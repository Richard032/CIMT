"""Unit tests with fake phones, API transport, and clocks. No real app is used."""

import io
import json
import pathlib
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from types import SimpleNamespace

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "runtime"))

from actions import ActionExecutor
from agent import Agent
from app_lifecycle import AppLifecycle
from budget import Budget
from coverage_tracker import CoverageTracker
from device_commands import DeviceReadiness
from device_runner import result_exit_code
from errors import InfrastructureError, LimitReached
from openai_transport import OpenAiTransport
from redaction import Redactor
from run_control import RunControl
from run_ui import Execution
from scenario import ScenarioRunner
from rpc_messages import RpcMessages
from screen_capture import ScreenCapture

MODEL = "gpt-5.4-mini-2026-03-17"
BUTTON = {"ref": "@e1", "identifier": "ButtonA", "type": "Button", "label": "Open"}
SIZE = {"type": "CimtScreenInfo", "screenWidth": 100, "screenHeight": 200}


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
    }
    result.update(values)
    return result


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
        self.runner = ScenarioRunner(
            {"instructions": "Explore buttons"},
            {},
            self.redactor,
            self.control,
            self.actions,
            self.root,
            sleep=lambda _: None,
        )
        self.build = {
            "target": "Release",
            "platform": "android",
            "app-id": "com.example.app",
            "artifact": "fixture.apk",
        }

    def run_scenario(self, mobile, actions):
        result = {"scenarios": []}
        agent = FakeAgent(actions)
        self.runner.run(mobile, self.build, result, agent, lambda: None)
        return result["scenarios"][0], agent

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
        positions = iter([10, 30])
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


class SchedulingTests(unittest.TestCase):
    def test_all_startup_devices_run_with_at_most_two_active(self):
        with tempfile.TemporaryDirectory() as temporary:
            barrier = threading.Barrier(2)
            lock = threading.Lock()
            counts = {"active": 0, "maximum": 0, "connected": 0}

            def factory(device, folder):
                mobile = FakeMobile(folder, elements=[])

                def connect():
                    with lock:
                        counts["active"] += 1
                        counts["connected"] += 1
                        number = counts["connected"]
                        counts["maximum"] = max(counts["maximum"], counts["active"])
                    if number <= 2:
                        barrier.wait(timeout=5)

                def close():
                    with lock:
                        counts["active"] -= 1

                mobile.connect = connect
                mobile.close = close
                return mobile

            context = {
                "config": {
                    "ai-model": {"name": MODEL, "api-key": "synthetic"},
                    "ai-budget": {"amount": 1, "currency": "USD"},
                },
                "report": temporary,
                "deadline": time.time() + 30,
                "inputs": {"instructions": "fixture"},
                "devices": [{"platform": "android", "id": str(index)} for index in range(3)],
                "builds": [
                    {
                        "platform": "android",
                        "target": "Release",
                        "app-id": "com.example.app",
                        "artifact": "fixture.apk",
                    }
                ],
            }
            execution = Execution(
                context, mobile_factory=factory, agent_factory=lambda: FakeAgent([action()])
            )
            self.assertEqual(execution.run(), 0)
            self.assertEqual(counts["connected"], 3)
            self.assertEqual(counts["maximum"], 2)
            self.assertEqual(len(execution.journal.results), 3)


if __name__ == "__main__":
    unittest.main(verbosity=2)
