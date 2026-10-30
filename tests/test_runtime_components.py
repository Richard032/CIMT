"""Unit tests with fake phones, API transport, and clocks. No real app is used."""

import io
import json
import pathlib
import subprocess
import sys
import tempfile
import time
import unittest
from types import SimpleNamespace

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "runtime"))

from action_prompt import parse_action
from activity import ActivityLog
from decision_recovery import DecisionRecovery
from scenario import ScenarioSession
from evidence import ScenarioEvidence
from actions import ActionExecutor
from agent import Agent
from app_lifecycle import AppLifecycle
from budget import Budget
from coverage_tracker import CoverageTracker
from device_commands import DeviceReadiness
from device_runner import result_exit_code
from errors import InfrastructureError, LimitReached, InvalidAgentResponse
from openai_transport import OpenAiTransport
from redaction import Redactor
from run_control import RunControl
from scenario import ScenarioRunner
from rpc_messages import RpcMessages
from screen_capture import ScreenCapture

MODEL = "gpt-5.4-mini-2026-03-17"
BUTTON = {"ref": "@e1", "identifier": "ButtonA", "type": "Button", "label": "Open"}
SIZE = {"type": "CimtScreenInfo", "screenWidth": 100, "screenHeight": 200}


def check(status="passed"):
    """Use explicit expected and observed behavior in each decided check."""
    return {
        "subject": "Button exploration",
        "source": "instructions",
        "status": status,
        "expected": "Buttons keep the app usable",
        "observed": "The app remains usable",
        "reason": "",
        "requirementId": "",
        "instructionQuote": "",
    }


def action(kind="done", **values):
    result = {
        "action": kind,
        "ref": "",
        "text": "",
        "x": -1,
        "y": -1,
        "direction": "",
        "credential": "",
        "field": "",
        "observation": "fixture",
        "remaining": [],
        "completion": "complete",
        "checks": [check()] if kind == "done" else [],
    }
    result.update(values)
    return result


class ScriptedTransport:
    """Return queued API responses and record requests without network access."""

    def __init__(self, responses):
        self.responses = iter(responses)
        self.bodies = []

    def request(self, path, body):
        self.bodies.append(body)
        value = next(self.responses)
        if isinstance(value, Exception):
            raise value
        return {
            "status": "completed",
            "usage": {"input_tokens": 10, "output_tokens": 10},
            "output": [{"type": "message", "content": [{
                "type": "output_text", "text": value if isinstance(value, str) else json.dumps(value),
            }]}],
        }


def api_agent(responses, budget=None):
    budget = budget or Budget(MODEL, 5, "USD")
    transport = ScriptedTransport(responses)
    agent = Agent({"ai-model": {"name": MODEL, "api-key": "synthetic"}},
                  budget, time.time() + 30, transport=transport)
    return agent, budget, transport


class FakeAgent:
    def __init__(self, actions):
        self.actions = iter(actions)
        self.calls = []

    def choose(self, *arguments):
        self.calls.append(arguments)
        return next(self.actions)


class FakeMobile:
    """Records operations and supplies a chosen foreground sequence."""

    def __init__(self, folder, elements=None, foreground=None):
        self.folder = pathlib.Path(folder)
        self.device = {"platform": "android", "id": "fixture"}
        self.elements = elements if elements is not None else [BUTTON, SIZE]
        self.foregrounds = iter(foreground or [])
        self.calls = []
        self.reset_error = None

    def connect(self):
        self.calls.append(("connect", {}))

    def close(self):
        self.calls.append(("close", {}))

    def readiness(self):
        pass

    def reset(self, artifact, app_id, target):
        self.calls.append(("reset", {"app": app_id, "target": target}))
        if self.reset_error:
            raise self.reset_error

    def snapshot(self):
        return self.elements, b"masked image fixture"

    def foreground(self):
        return next(self.foregrounds, "com.example.app")

    def running(self, app_id, executable):
        return False

    def crashes(self):
        return []

    def call(self, name, **arguments):
        self.calls.append((name, arguments))


class ChangingScreenMobile(FakeMobile):
    """Expose a different button after the first decision is rejected."""

    def __init__(self, folder):
        super().__init__(folder)
        self.captures = 0

    def snapshot(self):
        self.captures += 1
        if self.captures > 1:
            return [dict(BUTTON, ref="@e2", identifier="ButtonB"), SIZE], b"fresh masked screen"
        return super().snapshot()


class DeadlineTransport(ScriptedTransport):
    """Expire the run while the first response is in flight."""

    def __init__(self, responses, control):
        super().__init__(responses)
        self.control = control

    def request(self, path, body):
        response = super().request(path, body)
        self.control.deadline = 0
        return response


class FailingRefreshMobile(FakeMobile):
    """Fail only the capture requested after an AI response."""

    def __init__(self, folder, transport):
        super().__init__(folder)
        self.transport = transport

    def snapshot(self):
        if self.transport.bodies:
            raise InfrastructureError("mask unavailable")
        return super().snapshot()


class ScenarioTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = pathlib.Path(self.temporary.name)
        self.redactor = Redactor({})
        self.control = RunControl(time.time() + 30)
        self.actions = ActionExecutor(
            {}, self.redactor, self.control.deadline, sleep=lambda _: None
        )
        self.runner = self.create_runner()
        self.build = {
            "target": "Release",
            "platform": "android",
            "app-id": "com.example.app",
            "artifact": "fixture.apk",
        }

    def create_runner(self, requirements=None, activity=None):
        return ScenarioRunner(
            {"instructions": "Explore buttons"},
            {},
            self.redactor,
            self.control,
            self.actions,
            self.root,
            sleep=lambda _: None,
            requirements=requirements,
            activity=activity,
        )

    def run_scenario(self, mobile, actions, runner=None):
        result = {"scenarios": []}
        agent = FakeAgent(actions)
        (runner or self.runner).run(mobile, self.build, result, agent, lambda: None)
        return result["scenarios"][0], agent

    def test_unchecked_catalogue_item_prevents_completion(self):
        definitions = [{"id": "REQ-0001", "text": "Save works", "startLine": 1, "endLine": 1}]
        result, agent = self.run_scenario(
            FakeMobile(self.root, elements=[]), [action()], self.create_runner(definitions)
        )
        self.assertEqual(result["completion"], "incomplete")
        self.assertEqual(result["requirements"][0]["status"], "not tested")
        self.assertEqual(agent.calls[0][-1][0]["id"], "REQ-0001")

    def test_mapped_requirement_and_objective_can_complete(self):
        definitions = [{"id": "REQ-0001", "text": "Save works", "startLine": 1, "endLine": 1}]
        mapped = dict(check(), source="requirements", requirementId="REQ-0001")
        result, _ = self.run_scenario(
            FakeMobile(self.root, elements=[]),
            [action(checks=[mapped, check()])],
            self.create_runner(definitions),
        )
        self.assertEqual(result["completion"], "complete")
        self.assertEqual(result["verdict"], "passed")
        self.assertTrue(result["requirements"][0]["screenshot"])

    def test_observed_button_must_be_activated_before_completion(self):
        result, _ = self.run_scenario(FakeMobile(self.root), [action()])
        self.assertEqual(result["completion"], "incomplete")
        self.assertEqual(result["coverage"]["outstandingObservedControls"], 1)

    def test_successful_activation_can_complete_the_objective(self):
        mobile = FakeMobile(self.root)
        result, _ = self.run_scenario(mobile, [action("tap", ref="@e1"), action()])
        self.assertEqual(result["completion"], "complete")
        self.assertEqual(result["verdict"], "passed")
        self.assertEqual(result["coverage"]["attemptedControls"], 1)
        self.assertEqual(mobile.calls[1][0], "mobile_click_on_screen_at_coordinates")

    def test_rejected_action_does_not_count_as_button_coverage(self):
        result, _ = self.run_scenario(
            FakeMobile(self.root), [action("tap", ref="@missing"), action()]
        )
        self.assertEqual(result["coverage"]["attemptedControls"], 0)
        self.assertEqual(result["completion"], "incomplete")
        self.assertIn("actionError", result["steps"][1])

    def test_three_matching_crashes_cancel_only_this_objective(self):
        sequence = ["com.example.app", "home"] * 3
        result, agent = self.run_scenario(
            FakeMobile(self.root, foreground=sequence), [action("tap", ref="@e1")] * 3
        )
        self.assertEqual(len(agent.calls), 3)
        self.assertEqual([row["matchingAttempt"] for row in result["crashes"]], [1, 2, 3])
        self.assertEqual(result["verdict"], "failed")
        self.assertEqual(result["completion"], "incomplete")

    def test_three_startup_terminations_do_not_call_the_agent(self):
        result, agent = self.run_scenario(FakeMobile(self.root, foreground=["home"] * 3), [])
        self.assertEqual(len(result["crashes"]), 3)
        self.assertFalse(agent.calls)

    def test_reset_failure_prevents_any_agent_action(self):
        mobile = FakeMobile(self.root)
        mobile.reset_error = InfrastructureError("reset failed")
        agent = FakeAgent([action()])
        with self.assertRaises(InfrastructureError):
            self.runner.run(mobile, self.build, {"scenarios": []}, agent, lambda: None)
        self.assertFalse(agent.calls)

    def test_functional_failure_without_crash_stays_failed(self):
        result, _ = self.run_scenario(
            FakeMobile(self.root, elements=[]), [action(checks=[check("failed")])]
        )
        self.assertEqual(result["verdict"], "failed")
        self.assertEqual(result["completion"], "complete")
        self.assertEqual(
            result_exit_code([{"error": None, "stoppingReason": None, "scenarios": [result]}]), 1
        )
        self.assertTrue((self.root / result["checks"][0]["screenshot"]).exists())

    def test_finishing_without_a_check_cannot_pass(self):
        result, _ = self.run_scenario(FakeMobile(self.root, elements=[]), [action(checks=[])])
        self.assertEqual(result["verdict"], "inconclusive")
        self.assertEqual(
            result_exit_code([{"error": None, "stoppingReason": None, "scenarios": [result]}]), 2
        )

    def test_permission_block_is_incomplete_without_an_application_failure(self):
        result, _ = self.run_scenario(FakeMobile(self.root, elements=[]), [action(
            completion="blocked", checks=[], remaining=["Permission decision needs test authorization"])])
        self.assertEqual(result["completion"], "incomplete")
        self.assertEqual(result["verdict"], "inconclusive")
        self.assertFalse(result["crashes"])

    def test_returned_failure_survives_a_limit_during_the_request(self):
        result = {"scenarios": []}
        agent = StopThenReportFailure(self.control)
        with self.assertRaises(LimitReached):
            self.runner.run(
                FakeMobile(self.root, elements=[]), self.build, result, agent, lambda: None
            )
        self.assertEqual(result["scenarios"][0]["verdict"], "failed")
        self.assertEqual(len(result["scenarios"][0]["checks"]), 1)

    def test_crash_and_action_survive_failed_post_action_capture(self):
        mobile = FailingPostActionCapture(self.root, foreground=["com.example.app", "home"])
        result = {"scenarios": []}
        with self.assertRaises(InfrastructureError):
            self.runner.run(
                mobile, self.build, result, FakeAgent([action("tap", ref="@e1")]), lambda: None
            )
        scenario = result["scenarios"][0]
        self.assertEqual(scenario["verdict"], "failed")
        self.assertEqual(len(scenario["crashes"]), 1)
        self.assertEqual(scenario["steps"][-1]["action"]["action"], "tap")
        self.assertIn("evidenceError", scenario["steps"][-1])

    def test_remaining_plan_survives_failed_relaunch(self):
        mobile = FailedRelaunch(self.root, foreground=["com.example.app", "home"])
        result = {"scenarios": []}
        with self.assertRaisesRegex(InfrastructureError, "launch timed out"):
            self.runner.run(mobile, self.build, result,
                FakeAgent([action("tap", ref="@e1", remaining=["Explore settings buttons"])]), lambda: None)
        self.assertIn("Explore settings buttons", result["scenarios"][0]["remaining"])
        self.assertEqual(result["scenarios"][0]["completion"], "incomplete")

    def test_reset_failure_reports_unfinished_objective(self):
        mobile = FakeMobile(self.root)
        mobile.reset_error = InfrastructureError("reset failed")
        result = {"scenarios": []}
        with self.assertRaises(InfrastructureError):
            self.runner.run(mobile, self.build, result, FakeAgent([]), lambda: None)
        self.assertIn("Testing objective has not finished; coverage is not confirmed",
            result["scenarios"][0]["remaining"])

    def test_remaining_plan_is_saved_before_a_returned_response_hits_the_limit(self):
        result = {"scenarios": []}
        agent = StopThenReportFailure(self.control)
        with self.assertRaises(LimitReached):
            self.runner.run(FakeMobile(self.root), self.build, result, agent, lambda: None)
        self.assertIn("Check other buttons", result["scenarios"][0]["remaining"])

    def test_failure_includes_unresolved_requirements_and_controls(self):
        definitions = [{"id": "REQ-0001", "text": "Save works", "startLine": 1, "endLine": 1}]
        result = {"scenarios": []}
        with self.assertRaises(InfrastructureError):
            self.create_runner(definitions).run(
                FailedRelaunch(self.root, foreground=["com.example.app", "home"]), self.build,
                result, FakeAgent([action("tap", ref="@missing")]), lambda: None)
        remaining = result["scenarios"][0]["remaining"]
        self.assertIn("1 requirements have no decided result", remaining)
        self.assertIn("1 observed control/state combinations were not activated", remaining)

    def test_accepted_action_is_not_reported_as_unactivated_after_capture_failure(self):
        result = {"scenarios": []}
        with self.assertRaises(InfrastructureError):
            self.runner.run(FailingPostActionCapture(self.root), self.build, result,
                FakeAgent([action("tap", ref="@e1")]), lambda: None)
        scenario = result["scenarios"][0]
        self.assertEqual(scenario["coverage"]["outstandingObservedControls"], 0)
        self.assertFalse(any("were not activated" in item for item in scenario["remaining"]))

    def test_completed_objective_clears_earlier_remaining_plan(self):
        result, _ = self.run_scenario(FakeMobile(self.root), [
            action("tap", ref="@e1", remaining=["Check the opened page"]), action()])
        self.assertEqual(result["remaining"], [])
        self.assertEqual(result["completion"], "complete")

    def test_latest_remaining_plan_replaces_older_plan(self):
        result, _ = self.run_scenario(FakeMobile(self.root), [
            action("tap", ref="@e1", remaining=["Old pending task"]),
            action(completion="blocked", remaining=["Current pending task"])])
        self.assertEqual(result["remaining"], ["Current pending task"])

    def test_remaining_plan_is_redacted_before_publishing(self):
        self.runner.redactor = Redactor({"credentials": {"login": {"password": "private-fixture"}}})
        result = {"scenarios": []}
        snapshots = []
        with self.assertRaises(InfrastructureError):
            self.runner.run(FailingPostActionCapture(self.root), self.build, result,
                FakeAgent([action("tap", ref="@e1", remaining=["Retry private-fixture"])]),
                lambda: snapshots.append(json.dumps(result)))
        self.assertIn("Retry <redacted>", result["scenarios"][0]["remaining"])
        self.assertFalse(any("private-fixture" in snapshot for snapshot in snapshots))


    def test_invalid_check_is_corrected_before_a_single_tap(self):
        bad = action("tap", ref="@e1", checks=[dict(check(), requirementId="REQ-0001")])
        agent, budget, transport = api_agent([bad, action("tap", ref="@e1"), action()])
        mobile = FakeMobile(self.root)
        result = {"scenarios": []}
        self.runner.run(mobile, self.build, result, agent, lambda: None)
        taps = [name for name, _ in mobile.calls if name == "mobile_click_on_screen_at_coordinates"]
        self.assertEqual(len(taps), 1)
        self.assertEqual(budget.requests, 3)
        self.assertEqual(result["scenarios"][0]["verdict"], "passed")
        feedback = json.loads(transport.bodies[1]["input"][1]["content"][0]["text"])
        self.assertIn("checks[0]", feedback["correctionFeedback"][0]["error"])
        rejected = result["scenarios"][0]["rejectedResponses"][0]
        self.assertEqual(rejected["status"], "unaccepted")
        self.assertTrue((self.root / rejected["screenshot"]).exists())

    def test_three_invalid_responses_stop_without_a_tap(self):
        bad = action("tap", ref="@e1", checks=[dict(check(), requirementId="REQ-0001")])
        agent, budget, _ = api_agent([bad, bad, bad])
        mobile = FakeMobile(self.root)
        result = {"scenarios": []}
        with self.assertRaisesRegex(InvalidAgentResponse, "exhausted after 3 attempts"):
            self.runner.run(mobile, self.build, result, agent, lambda: None)
        self.assertEqual(budget.requests, 3)
        self.assertFalse(any(name.startswith("mobile_click") for name, _ in mobile.calls))
        self.assertEqual(len(result["scenarios"][0]["rejectedResponses"]), 3)
        self.assertTrue(result["scenarios"][0]["remaining"])

    def test_unknown_catalogue_id_is_corrected_before_recording(self):
        bad = action(checks=[dict(check(), source="requirements", requirementId="UNKNOWN")])
        agent, _, _ = api_agent([bad, action()])
        result = {"scenarios": []}
        self.runner.run(FakeMobile(self.root, elements=[]), self.build, result, agent, lambda: None)
        scenario = result["scenarios"][0]
        self.assertEqual(len(scenario["checks"]), 1)
        self.assertIn("catalogue", scenario["rejectedResponses"][0]["error"])

    def test_invalid_override_quote_is_corrected_before_recording(self):
        definitions = [{"id": "REQ-0001", "text": "Save works", "startLine": 1, "endLine": 1}]
        mapped = dict(check(), source="requirements", requirementId="REQ-0001")
        bad = dict(mapped, status="overridden", instructionQuote="invented", reason="Conflict")
        agent, _, _ = api_agent([action(checks=[bad]), action(checks=[mapped, check()])])
        result = {"scenarios": []}
        self.create_runner(definitions).run(FakeMobile(self.root, elements=[]), self.build,
                                            result, agent, lambda: None)
        scenario = result["scenarios"][0]
        self.assertEqual(scenario["requirements"][0]["status"], "passed")
        self.assertEqual(len(scenario["checks"]), 2)
        self.assertIn("instructionQuote", scenario["rejectedResponses"][0]["error"])

    def test_rejected_failure_remains_in_diagnostics_after_correction(self):
        bad = action(checks=[check("failed"), dict(check(), requirementId="REQ-0001")])
        agent, _, _ = api_agent([bad, action()])
        result = {"scenarios": []}
        self.runner.run(FakeMobile(self.root, elements=[]), self.build, result, agent, lambda: None)
        scenario = result["scenarios"][0]
        self.assertEqual(scenario["rejectedResponses"][0]["response"]["checks"][0]["status"], "failed")
        self.assertEqual(len(scenario["checks"]), 1)

    def test_rejected_metadata_and_correction_feedback_are_redacted(self):
        self.redactor = Redactor({"credentials": {"test": {"password": "synthetic-secret"}}})
        runner = self.create_runner()
        bad = action(checks=[dict(check(), requirementId="synthetic-secret")])
        agent, _, transport = api_agent([bad, action()])
        result = {"scenarios": []}
        runner.run(FakeMobile(self.root, elements=[]), self.build, result, agent, lambda: None)
        self.assertNotIn("synthetic-secret", json.dumps(result))
        self.assertNotIn("synthetic-secret", json.dumps(transport.bodies))

    def test_malformed_json_can_be_corrected(self):
        agent, _, _ = api_agent(["{broken", action()])
        result = {"scenarios": []}
        self.runner.run(FakeMobile(self.root, elements=[]), self.build, result, agent, lambda: None)
        self.assertEqual(result["scenarios"][0]["rejectedResponses"][0]["response"], "{broken")

    def test_budget_limit_stops_correction_before_another_api_request(self):
        budget = Budget(MODEL, 5, "USD")
        budget.limit = budget.bound
        agent, _, transport = api_agent(["{broken", action()], budget)
        result = {"scenarios": []}
        with self.assertRaises(LimitReached):
            self.runner.run(FakeMobile(self.root, elements=[]), self.build, result, agent, lambda: None)
        self.assertEqual(len(transport.bodies), 1)
        self.assertTrue(result["scenarios"][0]["rejectedResponses"])

    def test_generic_infrastructure_error_is_not_retried(self):
        agent, _, transport = api_agent([InfrastructureError("transport failed"), action()])
        with self.assertRaisesRegex(InfrastructureError, "transport failed"):
            self.runner.run(FakeMobile(self.root), self.build, {"scenarios": []}, agent, lambda: None)
        self.assertEqual(len(transport.bodies), 1)

    def test_refusal_does_not_enter_correction(self):
        response = {"status": "completed", "output": [{"type": "message", "content": [
            {"type": "refusal", "refusal": "fixture"}]}]}
        with self.assertRaises(InfrastructureError) as raised:
            parse_action(response)
        self.assertNotIsInstance(raised.exception, InvalidAgentResponse)


    def test_correction_uses_a_fresh_screen_and_new_element_refs(self):
        bad = action("tap", ref="@e1", checks=[dict(check(), requirementId="REQ-0001")])
        agent, _, transport = api_agent([bad, action("tap", ref="@e2"), action()])
        mobile = ChangingScreenMobile(self.root)
        self.runner.run(mobile, self.build, {"scenarios": []}, agent, lambda: None)
        state = json.loads(transport.bodies[1]["input"][1]["content"][0]["text"])
        self.assertEqual(state["elements"][0]["ref"], "@e2")
        taps = [arguments for name, arguments in mobile.calls if name.startswith("mobile_click")]
        self.assertEqual(taps, [{"ref": "@e2"}])

    def test_expired_deadline_prevents_a_correction_request(self):
        transport = DeadlineTransport(["{broken", action()], self.control)
        agent = Agent({"ai-model": {"name": MODEL, "api-key": "synthetic"}},
                      Budget(MODEL, 5, "USD"), time.time() + 30, transport=transport)
        result = {"scenarios": []}
        with self.assertRaisesRegex(LimitReached, "Whole-run time limit"):
            self.runner.run(FakeMobile(self.root), self.build, result, agent, lambda: None)
        self.assertEqual(len(transport.bodies), 1)
        self.assertEqual(len(result["scenarios"][0]["rejectedResponses"]), 1)

    def test_accepted_failure_survives_later_response_corrections(self):
        bad = action(checks=[dict(check(), requirementId="REQ-0001")])
        agent, _, _ = api_agent([action("tap", ref="@e1", checks=[check("failed")]), bad, action()])
        result = {"scenarios": []}
        self.runner.run(FakeMobile(self.root), self.build, result, agent, lambda: None)
        self.assertEqual(result["scenarios"][0]["verdict"], "failed")

    def test_correction_capture_error_is_not_retried(self):
        transport = ScriptedTransport(["{broken", action()])
        agent = Agent({"ai-model": {"name": MODEL, "api-key": "synthetic"}},
                      Budget(MODEL, 5, "USD"), time.time() + 30, transport=transport)
        with self.assertRaisesRegex(InfrastructureError, "mask unavailable"):
            self.runner.run(FailingRefreshMobile(self.root, transport), self.build, {"scenarios": []}, agent, lambda: None)
        self.assertEqual(len(transport.bodies), 1)


    def test_activity_records_rejection_and_recovery_with_device_target(self):
        output = io.StringIO()
        activity = ActivityLog(self.root, self.redactor, output=output)
        agent, _, _ = api_agent(["{broken", action()])
        self.create_runner(activity=activity).run(FakeMobile(self.root, elements=[]), self.build,
                                                {"scenarios": []}, agent, lambda: None)
        rows = [json.loads(line) for line in activity.path.read_text().splitlines()]
        attempts = [row for row in rows if row["operation"] == "AI response correction"]
        self.assertEqual([row["status"] for row in attempts], ["rejected", "corrected"])
        self.assertTrue(all(row["target"] == "Release" and row["device"] == "fixture" for row in attempts))
        self.assertNotIn("{broken", output.getvalue())

    def test_rejected_diagnostic_survives_storage_failure_without_retry(self):
        session = ScenarioSession({"target": "Release", "steps": [], "requirements": []},
                                  "com.example.app", "com.example.app", [], b"masked")
        recovery = DecisionRecovery({"instructions": "Explore"}, {}, self.redactor, self.control)
        agent, _, transport = api_agent(["{broken", action()])
        # An existing file cannot also be the evidence folder.
        blocked_folder = self.root / "not-a-folder"
        blocked_folder.write_text("fixture")
        evidence = ScenarioEvidence(blocked_folder, self.root)
        with self.assertRaises(OSError):
            recovery.choose(FakeMobile(self.root), session, agent, evidence, lambda: None)
        self.assertEqual(len(transport.bodies), 1)
        self.assertEqual(session.result["rejectedResponses"][0]["response"], "{broken")
        self.assertIn("evidenceError", session.result["rejectedResponses"][0])

    def test_incomplete_provider_response_is_not_a_correction_error(self):
        with self.assertRaises(InfrastructureError) as raised:
            parse_action({"status": "incomplete", "output": []})
        self.assertNotIsInstance(raised.exception, InvalidAgentResponse)


class StopThenReportFailure:
    """Simulate a limit reached while the model is returning a finding."""

    def __init__(self, control):
        self.control = control

    def choose(self, *arguments):
        self.control.stop()
        return action(checks=[check("failed")], remaining=["Check other buttons"])


class FailingPostActionCapture(FakeMobile):
    """Allow the initial image, then fail the image after an action."""

    def snapshot(self):
        if any(name.startswith("mobile_click") for name, _ in self.calls):
            raise InfrastructureError("capture failed")
        return super().snapshot()


class FailedRelaunch(FakeMobile):
    def call(self, name, **arguments):
        super().call(name, **arguments)
        if name == "mobile_launch_app":
            raise InfrastructureError("launch timed out")


class BoundaryTests(unittest.TestCase):
    def test_rpc_parser_keeps_partial_lines_until_complete(self):
        messages = RpcMessages()
        self.assertEqual(messages.feed(b'{"id":1,'), [])
        self.assertEqual(messages.feed(b'"result":{}}\n'), [{"id": 1, "result": {}}])

    def test_rpc_notifications_do_not_complete_a_request(self):
        matched, _ = RpcMessages.result({"method": "notice"}, 1)
        self.assertFalse(matched)

    def test_rpc_error_is_rejected_without_exposing_its_body(self):
        with self.assertRaises(InfrastructureError) as raised:
            RpcMessages.result({"id": 1, "error": {"secret": "private fixture"}}, 1)
        self.assertNotIn("private fixture", str(raised.exception))

    def test_moving_sensitive_field_stops_capture_before_masking(self):
        import base64

        redactor = Redactor({"masking": {"rules": [{"element-id": "Password"}]}})
        positions = iter([10, 30] * ScreenCapture.MAX_ATTEMPTS)
        masked = []

        def call(name, **arguments):
            if name == "mobile_take_screenshot":
                return {
                    "content": [{"type": "image", "data": base64.b64encode(b"fixture").decode()}]
                }
            elements = [
                {
                    "identifier": "Password",
                    "coordinates": {"x": next(positions), "y": 1, "width": 10, "height": 10},
                }
            ]
            return {"content": [{"type": "text", "text": json.dumps(elements)}]}

        screen = ScreenCapture(
            call,
            lambda _: {"data": {"device": {"screenSize": {"width": 100, "height": 100}}}},
            lambda: None,
            redactor,
            SimpleNamespace(capture=lambda *args: masked.append(args)),
            sleep=lambda _: None,
        )
        with self.assertRaises(InfrastructureError):
            screen.snapshot()
        self.assertFalse(masked)

    def test_failed_android_data_clear_prevents_launch(self):
        present = iter([{"data": []}, {"data": [{"packageName": "com.example.app"}]}])
        calls = []
        commands = SimpleNamespace(
            device={"platform": "android", "id": "fixture"},
            native=lambda _: next(present),
            run_command=lambda *args, **kwargs: subprocess.CompletedProcess(args, 1, "Failed", ""),
        )
        lifecycle = AppLifecycle(commands, lambda name, **kwargs: calls.append(name))
        with self.assertRaises(InfrastructureError):
            lifecycle.reset("fixture.apk", "com.example.app", "Release")
        self.assertEqual(calls, ["mobile_install_app"])

    def test_expired_transport_does_not_open_a_connection(self):
        calls = []
        opener = SimpleNamespace(open=lambda *args, **kwargs: calls.append(args))
        transport = OpenAiTransport("synthetic", 10, opener=opener, clock=lambda: 10)
        with self.assertRaises(LimitReached):
            transport.request("responses", {})
        self.assertFalse(calls)

    def test_failed_transport_retains_full_budget_reservation(self):
        def fail(*args):
            raise InfrastructureError("transport fixture")

        budget = Budget(MODEL, 1, "USD")
        agent = Agent(
            {"ai-model": {"name": MODEL, "api-key": "synthetic"}},
            budget,
            30,
            transport=SimpleNamespace(request=fail),
        )
        with self.assertRaises(InfrastructureError):
            agent.choose("test", "", "", [], b"image", [], [], {})
        self.assertEqual(budget.uncertain, budget.bound)

    def test_android_lock_stops_without_app_calls(self):
        calls = []

        def run(arguments, **kwargs):
            calls.append(arguments)
            return subprocess.CompletedProcess(arguments, 0, "  showing=true\n", "")

        commands = SimpleNamespace(
            device={"platform": "android", "id": "fixture"}, context={}, run_command=run
        )
        with self.assertRaises(LimitReached):
            DeviceReadiness(commands, pathlib.Path("/unused")).readiness()
        self.assertEqual(len(calls), 1)
        self.assertIn("dumpsys", calls[0])

    def test_system_app_reset_is_rejected_before_any_device_command(self):
        calls = []
        commands = SimpleNamespace(native=lambda args: calls.append(args))
        lifecycle = AppLifecycle(commands, lambda *args, **kwargs: calls.append(args))
        with self.assertRaises(InfrastructureError):
            lifecycle.reset("fixture.apk", "com.android.settings", "Release")
        self.assertFalse(calls)

    def test_coverage_keeps_unvisited_buttons_after_state_changes(self):
        coverage = CoverageTracker()
        coverage.observe([BUTTON])
        coverage.observe([dict(BUTTON, identifier="Other")])
        coverage.activated(dict(BUTTON, identifier="Other"))
        self.assertEqual(coverage.snapshot()["observedControls"], 2)
        self.assertEqual(coverage.snapshot()["outstandingObservedControls"], 1)

    def test_stop_signal_is_shared_without_using_real_time(self):
        control = RunControl(20, clock=lambda: 10)
        control.check()
        control.stop()
        with self.assertRaises(LimitReached):
            control.check()

    def test_error_precedence_is_higher_than_a_crash(self):
        results = [{"error": "fixture", "scenarios": [{"crashes": [{}]}]}]
        self.assertEqual(result_exit_code(results), 3)


if __name__ == "__main__":
    unittest.main(verbosity=2)
