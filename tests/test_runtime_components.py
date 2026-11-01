"""Unit tests with fake phones, API transport, and clocks. No real app is used."""

import io
import json
import pathlib
import subprocess
import sys
import tempfile
import time
import unittest
from contextlib import redirect_stdout
from types import SimpleNamespace

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "runtime"))

from action_prompt import parse_action
from activity import ActivityLog
from ai_interaction import AiInteraction
from scenario import ScenarioSession
from evidence import ScenarioEvidence
from actions import ActionExecutor
from agent import Agent
from device_adapter.app_lifecycle import AppLifecycle
from budget import Budget
from coverage_tracker import CoverageTracker
from device_adapter.readiness import DeviceReadiness
from stopping_policy.policy import result_exit_code
from errors import AppLaunchError, DeviceActionError, InfrastructureError, LimitReached
from openai_transport import OpenAiTransport
from redaction import Redactor
from run_control import RunControl
from scenario import ScenarioRunner
from run_ui import Execution
from device_adapter.rpc_messages import RpcMessages
from device_adapter.screen_capture import ScreenCapture

MODEL = "gpt-5.4-mini-2026-03-17"
BUTTON = {"ref": "@e1", "identifier": "ButtonA", "type": "Button", "label": "Open"}
SIZE = {"type": "CimtScreenInfo", "screenWidth": 100, "screenHeight": 200}


def check(status="passed"):
    """Use explicit expected and observed behavior in each decided check."""
    return {
        "taskId": 0,
        "subject": "Testing objective",
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
        "repeatInstruction": "",
        "repeatReason": "",
        "remaining": [],
        "completion": "complete",
        "checks": [check()] if kind == "done" else [],
        "planUpdates": [], "planStepId": 0, "discoveredControls": [],
        "configuration": [], "pathDecisions": [],
        'context': dict(summary='', includeAll=['actions', 'tasks', 'paths', 'states', 'transitions', 'requirements', 'checks', 'configuration'], records=[]),
        'recovery': dict(id=-1, decision='none', reason=''),
    }
    result.update(values)
    if kind != 'done' and 'planUpdates' not in values:
        result['planUpdates'] = [dict(id=0, source='instructions', requirementId='', instructionQuote='Explore',
            subject='Testing objective', expected='Buttons keep the app usable', status='active', reason='', targetState='')]
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
        self.app_id = app_id

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


class RejectedTargetMobile(FakeMobile):
    """A missing adapter target is an interaction result, not a lost connection."""

    def call(self, name, **arguments):
        super().call(name, **arguments)
        if name == 'mobile_click_on_screen_at_coordinates' and arguments.get('ref') == '@earlier':
            raise DeviceActionError('Adapter could not resolve the requested target')


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


class StopAfterFocusMobile(FakeMobile):
    def __init__(self, folder, control):
        super().__init__(folder, elements=[dict(BUTTON, identifier='LoginUser'), SIZE])
        self.control = control

    def call(self, name, **arguments):
        super().call(name, **arguments)
        if name == 'mobile_click_on_screen_at_coordinates':
            self.control.interrupt()


class ConfiguredModelTests(unittest.TestCase):
    def test_access_check_uses_the_selected_model_without_inference(self):
        for model in [MODEL, "gpt-5.6-luna"]:
            with self.subTest(model=model):
                calls = []
                budget = Budget(model, 1, "USD")
                agent = Agent({"ai-model": {"name": model, "api-key": "synthetic"}},
                              budget, time.time() + 30,
                              transport=SimpleNamespace(request=lambda path: calls.append(path)))
                agent.check_access()
                self.assertEqual(calls, ["models/" + model])
                self.assertEqual(budget.requests, 0)

    def test_access_failure_does_not_switch_models(self):
        calls = []

        def denied(path):
            calls.append(path)
            raise InfrastructureError("OpenAI API request failed with HTTP 403")

        agent = Agent({"ai-model": {"name": "gpt-5.6-luna", "api-key": "synthetic"}},
                      Budget("gpt-5.6-luna", 1, "USD"), time.time() + 30,
                      transport=SimpleNamespace(request=denied))
        with self.assertRaises(InfrastructureError):
            agent.check_access()
        self.assertEqual(calls, ["models/gpt-5.6-luna"])

    def test_inference_uses_luna_with_the_priced_cache_lifetime(self):
        transport = ScriptedTransport([action()])
        agent = Agent({"ai-model": {"name": "gpt-5.6-luna", "api-key": "synthetic"}},
                      Budget("gpt-5.6-luna", 1, "USD"), time.time() + 30,
                      transport=transport)
        agent.choose("Explore", "", "", [], b"masked", [], [], {})
        body = transport.bodies[0]
        self.assertEqual(body["model"], "gpt-5.6-luna")
        self.assertEqual(body["prompt_cache_options"], {"ttl": "30m", 'mode': 'explicit'})
        self.assertEqual(body['input'][0]['content'][0]['prompt_cache_breakpoint'], {'mode': 'explicit'})
        self.assertEqual(body["service_tier"], "default")
        self.assertEqual(body["reasoning"], {"effort": "low"})
        self.assertEqual(body["max_output_tokens"], 2048)

    def test_mini_inference_keeps_its_existing_cache_behavior(self):
        agent, _, transport = api_agent([action()])
        agent.choose("Explore", "", "", [], b"masked", [], [], {})
        self.assertEqual(transport.bodies[0]["model"], MODEL)
        self.assertNotIn("prompt_cache_options", transport.bodies[0])

    def test_preflight_reports_and_journals_the_configured_model(self):
        with tempfile.TemporaryDirectory() as folder:
            config = {"ai-model": {"name": "gpt-5.6-luna", "api-key": "synthetic"},
                      "ai-budget": {"amount": 1, "currency": "USD"}}
            calls = []
            agent = Agent(config, Budget("gpt-5.6-luna", 1, "USD"), time.time() + 30,
                          transport=SimpleNamespace(request=lambda path: calls.append(path)))
            execution = Execution({"config": config, "report": folder, "deadline": time.time() + 30},
                                  agent_factory=lambda: agent)
            output = io.StringIO()
            with redirect_stdout(output):
                self.assertEqual(execution.run(preflight=True), 0)
            ledger = json.loads(pathlib.Path(folder, "ai-budget.json").read_text())
            self.assertEqual(ledger["model"], "gpt-5.6-luna")
            self.assertEqual(ledger["requests"], 0)
            self.assertIn("passed for gpt-5.6-luna", output.getvalue())
            self.assertEqual(calls, ["models/gpt-5.6-luna"])
            self.assertFalse(pathlib.Path(folder, "devices").exists())


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

    def test_one_ai_reply_executes_multiple_commands_in_received_order(self):
        batch = ''.join(json.dumps(value) for value in [action('tap', ref='@one'), action('back'), action()])
        agent, _, transport = api_agent([batch])
        mobile = FakeMobile(self.root, elements=[])
        result = {'scenarios': []}
        self.runner.run(mobile, self.build, result, agent, lambda: None)
        self.assertEqual([name for name, _ in mobile.calls],
            ['reset', 'mobile_click_on_screen_at_coordinates', 'mobile_press_button'])
        self.assertEqual(len(transport.bodies), 1)
        self.assertEqual([row['status'] for row in result['scenarios'][0]['commandQueue']['commands']],
            ['executed', 'executed', 'handled'])

    def test_done_keeps_later_commands_visible_without_executing_them(self):
        agent, _, transport = api_agent([json.dumps([action(), action('tap', ref='@later')])])
        mobile = FakeMobile(self.root, elements=[])
        result = {'scenarios': []}
        self.runner.run(mobile, self.build, result, agent, lambda: None)
        self.assertEqual([name for name, _ in mobile.calls], ['reset'])
        rows = result['scenarios'][0]['commandQueue']['commands']
        self.assertEqual([row['status'] for row in rows], ['handled', 'not executed'])
        self.assertEqual(len(transport.bodies), 1)

    def test_queued_context_selection_is_applied_before_the_next_ai_request(self):
        select = action('recall', context=dict(summary='Keep the actual outcome', includeAll=[], records=[]))
        agent, _, transport = api_agent([json.dumps([action('tap', ref='@one'), select]), action()])
        self.runner.run(FakeMobile(self.root, elements=[]), self.build, {'scenarios': []}, agent, lambda: None)
        state = json.loads(transport.bodies[1]['input'][1]['content'][0]['text'])
        self.assertEqual(state['explorationMemory']['summary'], 'Keep the actual outcome')
        self.assertNotIn('contextSelectionRequired', state)

    def test_failed_command_cancels_the_tail_and_reports_the_actual_issue_once(self):
        batch = json.dumps([action('tap', ref='@earlier'), action('tap', ref='@later')])
        agent, _, transport = api_agent([batch, action()])
        mobile = RejectedTargetMobile(self.root, elements=[])
        result = {'scenarios': []}
        self.runner.run(mobile, self.build, result, agent, lambda: None)
        taps = [args['ref'] for name, args in mobile.calls if name == 'mobile_click_on_screen_at_coordinates']
        self.assertEqual(taps, ['@earlier'])
        rows = result['scenarios'][0]['commandQueue']['commands']
        self.assertEqual([row['status'] for row in rows], ['failed', 'cancelled', 'handled'])
        self.assertEqual(len(transport.bodies), 2)
        state = json.loads(transport.bodies[1]['input'][1]['content'][0]['text'])
        self.assertIn('Batch 0, command 0 (tap, position 0)', state['resourceFeedback'])
        self.assertIn('Adapter could not resolve the requested target', state['resourceFeedback'])
        self.assertIn('Cancelled 1 remaining command(s)', state['resourceFeedback'])
        self.assertEqual(state['explorationMemory']['catalogue']['commands'], 2)

    def test_failure_on_the_last_command_still_returns_issue_feedback(self):
        agent, _, transport = api_agent([action('swipe', direction='invalid'), action()])
        mobile = FakeMobile(self.root, elements=[])
        self.runner.run(mobile, self.build, {'scenarios': []}, agent, lambda: None)
        self.assertEqual(len(transport.bodies), 2)
        state = json.loads(transport.bodies[1]['input'][1]['content'][0]['text'])
        self.assertIn('Invalid swipe direction', state['resourceFeedback'])
        self.assertIn('Cancelled 0 remaining command(s)', state['resourceFeedback'])

    def test_successful_batch_uses_only_the_next_normal_decision_request(self):
        batch = json.dumps([action('tap', ref='@one'), action('back')])
        agent, _, transport = api_agent([batch, action()])
        mobile = FakeMobile(self.root, elements=[])
        self.runner.run(mobile, self.build, {'scenarios': []}, agent, lambda: None)
        self.assertEqual(len(transport.bodies), 2)
        state = json.loads(transport.bodies[1]['input'][1]['content'][0]['text'])
        self.assertFalse(state.get('resourceFeedback'))
        self.assertEqual(len(state['recentActions']), 2)

    def test_mechanical_command_failure_cancels_every_later_command(self):
        batch = json.dumps([action('swipe', direction='invalid'),
            action('tap', ref='@later'), action()])
        agent, _, transport = api_agent([batch, action()])
        mobile = FakeMobile(self.root, elements=[])
        result = {'scenarios': []}
        published_states = []
        def publish():
            rows = result['scenarios'][0].get('commandQueue', {}).get('commands', [])
            published_states.append([row['status'] for row in rows])
        self.runner.run(mobile, self.build, result, agent, publish)
        self.assertEqual([name for name, _ in mobile.calls], ['reset'])
        self.assertIn(['started', 'cancelled', 'cancelled'], published_states)
        self.assertEqual([row['status'] for row in result['scenarios'][0]['commandQueue']['commands']],
            ['failed', 'cancelled', 'cancelled', 'handled'])
        state = json.loads(transport.bodies[1]['input'][1]['content'][0]['text'])
        self.assertIn('Invalid swipe direction', state['resourceFeedback'])
        self.assertIn('Cancelled 2 remaining command(s)', state['resourceFeedback'])

    def test_cancellation_after_first_command_preserves_the_unperformed_tail(self):
        control = self.control
        class StopAfterTap(FakeMobile):
            def call(self, name, **arguments):
                super().call(name, **arguments)
                if name == 'mobile_click_on_screen_at_coordinates':
                    control.interrupt()
        agent, _, transport = api_agent([json.dumps([action('tap', ref='@one'), action('tap', ref='@two')])])
        mobile = StopAfterTap(self.root, elements=[])
        result = {'scenarios': []}
        with self.assertRaises(LimitReached):
            self.runner.run(mobile, self.build, result, agent, lambda: None)
        taps = [args['ref'] for name, args in mobile.calls if name == 'mobile_click_on_screen_at_coordinates']
        self.assertEqual(taps, ['@one'])
        self.assertEqual(result['scenarios'][0]['commandQueue']['commands'][1]['status'], 'not executed')
        self.assertEqual(len(transport.bodies), 1)

    def test_deadline_after_first_command_prevents_the_next_queued_action(self):
        control = self.control
        class ExpireAfterTap(FakeMobile):
            def call(self, name, **arguments):
                super().call(name, **arguments)
                if name == 'mobile_click_on_screen_at_coordinates':
                    control.deadline = 0
        agent, _, transport = api_agent([json.dumps([action('tap', ref='@one'), action('tap', ref='@two')])])
        mobile = ExpireAfterTap(self.root, elements=[])
        result = {'scenarios': []}
        with self.assertRaises(LimitReached):
            self.runner.run(mobile, self.build, result, agent, lambda: None)
        self.assertEqual([args['ref'] for name, args in mobile.calls if name.startswith('mobile_click')], ['@one'])
        self.assertEqual(result['scenarios'][0]['commandQueue']['commands'][1]['status'], 'not executed')
        self.assertEqual(len(transport.bodies), 1)

    def test_fatal_adapter_error_preserves_pending_commands_without_another_request(self):
        class LostConnection(FakeMobile):
            def call(self, name, **arguments):
                super().call(name, **arguments)
                if name == 'mobile_click_on_screen_at_coordinates':
                    raise InfrastructureError('Connection lost')
        agent, _, transport = api_agent([json.dumps([action('tap', ref='@one'), action('tap', ref='@two')])])
        mobile = LostConnection(self.root, elements=[])
        result = {'scenarios': []}
        with self.assertRaisesRegex(InfrastructureError, 'Connection lost'):
            self.runner.run(mobile, self.build, result, agent, lambda: None)
        self.assertEqual([row['status'] for row in result['scenarios'][0]['commandQueue']['commands']],
            ['failed', 'cancelled'])
        self.assertEqual(len(transport.bodies), 1)

    def test_repetition_recovery_defers_a_batch_tail_without_a_fixed_action_stop(self):
        batch = json.dumps([action('tap', ref='@one') for _ in range(5)])
        agent, _, transport = api_agent([batch, action()])
        mobile = FakeMobile(self.root, elements=[])
        result = {'scenarios': []}
        self.runner.run(mobile, self.build, result, agent, lambda: None)
        self.assertEqual(len([name for name, _ in mobile.calls if name.startswith('mobile_click')]), 3)
        self.assertEqual(len(transport.bodies), 2)
        state = json.loads(transport.bodies[1]['input'][1]['content'][0]['text'])
        self.assertIn('recoveryRequest', state['explorationMemory'])
        self.assertEqual([row['status'] for row in result['scenarios'][0]['commandQueue']['commands']][-3:],
            ['not executed', 'not executed', 'handled'])

    def test_unchecked_catalogue_item_prevents_completion(self):
        definitions = [{"id": "REQ-0001", "text": "Save works", "startLine": 1, "endLine": 1}]
        result, agent = self.run_scenario(
            FakeMobile(self.root, elements=[]), [action(completion='blocked')], self.create_runner(definitions)
        )
        self.assertEqual(result["completion"], "incomplete")
        self.assertEqual(result["requirements"][0]["status"], "not tested")
        self.assertEqual(agent.calls[0][8][0]["id"], "REQ-0001")

    def test_each_worker_receives_only_its_own_execution_scope(self):
        _, agent = self.run_scenario(FakeMobile(self.root, elements=[]), [action()])
        setup = agent.calls[0][2]
        self.assertIn('"platform": "android"', setup)
        self.assertIn('"deviceId": "fixture"', setup)
        self.assertIn('"target": "Release"', setup)
        self.assertIn("Other devices and targets are scheduled independently", setup)

    def test_mapped_requirement_and_objective_can_complete(self):
        definitions = [{"id": "REQ-0001", "text": "Save works", "startLine": 1, "endLine": 1}]
        mapped = dict(check(), taskId=1, source="requirements", requirementId="REQ-0001")
        result, _ = self.run_scenario(
            FakeMobile(self.root, elements=[]),
            [action(checks=[mapped, check()])],
            self.create_runner(definitions),
        )
        self.assertEqual(result["completion"], "complete")
        self.assertEqual(result["verdict"], "passed")
        self.assertTrue(result["requirements"][0]["screenshot"])

    def test_observed_button_must_be_activated_before_completion(self):
        result, _ = self.run_scenario(FakeMobile(self.root), [action(completion='blocked')])
        self.assertEqual(result["completion"], "incomplete")
        self.assertEqual(result["coverage"]["outstandingObservedControls"], 1)

    def test_successful_activation_can_complete_the_objective(self):
        mobile = FakeMobile(self.root)
        result, _ = self.run_scenario(mobile, [action("tap", ref="@e1"), action()])
        self.assertEqual(result["completion"], "complete")
        self.assertEqual(result["verdict"], "passed")
        self.assertEqual(result["coverage"]["attemptedControls"], 1)
        self.assertEqual(mobile.calls[1][0], "mobile_click_on_screen_at_coordinates")

    def test_restart_preserves_data_and_uses_only_the_tested_app_identity(self):
        mobile = FakeMobile(self.root, elements=[])
        result, _ = self.run_scenario(mobile, [action('restart'), action()])
        self.assertEqual([name for name, _ in mobile.calls], ['reset', 'mobile_terminate_app', 'mobile_launch_app'])
        self.assertEqual(mobile.calls[1][1]['packageName'], self.build['app-id'])
        self.assertEqual(mobile.calls[2][1]['packageName'], self.build['app-id'])
        self.assertEqual(result['verdict'], 'passed')

    def test_cancellation_between_restart_calls_prevents_relaunch(self):
        mobile = FakeMobile(self.root)
        mobile.app_id = self.build['app-id']
        def stop_after_termination(name, **arguments):
            mobile.calls.append((name, arguments))
            self.control.interrupt()
        mobile.call = stop_after_termination
        executor = ActionExecutor({}, self.redactor, self.control.deadline, check=self.control.check)
        with self.assertRaisesRegex(LimitReached, 'User interrupted'):
            executor.execute(mobile, action('restart'), mobile.elements)
        self.assertEqual([name for name, _ in mobile.calls], ['mobile_terminate_app'])

    def test_scoped_completion_does_not_require_unrelated_observed_controls(self):
        def choose(*arguments):
            path = arguments[-1]['currentControls'][0]['id']
            return action(pathDecisions=[dict(id=path, scope='out of scope',
                reason='This control is unrelated to the configured testing objective', planStepId=0)])
        mobile = FakeMobile(self.root)
        result = {'scenarios': []}
        self.runner.run(mobile, self.build, result, SimpleNamespace(choose=choose), lambda: None)
        scenario = result['scenarios'][0]
        self.assertEqual(scenario['completion'], 'complete')
        self.assertEqual(scenario['coverage']['outstandingObservedControls'], 1)
        self.assertEqual(scenario['exploration']['paths'][0]['scope'], 'out of scope')
        self.assertFalse(any(name.startswith('mobile_click') for name, _ in mobile.calls))

    def test_instruction_subtask_keeps_completion_incomplete_until_it_has_a_check(self):
        task = dict(id=1, source='instructions', requirementId='', instructionQuote='Explore',
            subject='Test selector alternatives', expected='Each requested choice remains usable',
            status='pending', reason='', targetState='')
        result, _ = self.run_scenario(FakeMobile(self.root, elements=[]), [action(planUpdates=[task], completion='blocked')])
        self.assertEqual(result['completion'], 'incomplete')
        self.assertIn('Test selector alternatives: pending', result['remaining'])

    def test_plan_wording_is_ai_owned_and_does_not_gate_a_tap(self):
        task = dict(id=5, source='instructions', requirementId='', instructionQuote='AI paraphrase',
            subject='Explore settings', expected='Check the menu', status='active', reason='', targetState='')
        mobile = FakeMobile(self.root, elements=[])
        result, _ = self.run_scenario(mobile, [action('tap', ref='@e1', planUpdates=[task]), action(completion='blocked')])
        self.assertTrue(any(name.startswith('mobile_click') for name, _ in mobile.calls))
        self.assertTrue(any(row['id'] == 5 for row in result['testPlan']['tasks']))
        self.assertNotIn('rejectedResponses', result)

    def test_unobserved_ref_is_dispatched_without_claiming_observed_coverage(self):
        mobile = FakeMobile(self.root)
        result, _ = self.run_scenario(
            mobile, [action("tap", ref="@missing"), action(completion='blocked')]
        )
        self.assertEqual(result["coverage"]["attemptedControls"], 0)
        self.assertEqual(result["completion"], "incomplete")
        self.assertNotIn("actionError", result["steps"][1])
        self.assertIn(('mobile_click_on_screen_at_coordinates', {'ref': '@missing'}), mobile.calls)

    def test_disabled_observation_does_not_override_the_ai_selected_tap(self):
        mobile = FakeMobile(self.root, elements=[dict(BUTTON, enabled=False), SIZE])
        self.run_scenario(mobile, [action('tap', ref='@e1'), action(completion='blocked')])
        self.assertIn(('mobile_click_on_screen_at_coordinates', {'ref': '@e1'}), mobile.calls)

    def test_adapter_target_failure_returns_to_ai_without_a_host_selected_action(self):
        mobile = RejectedTargetMobile(self.root)
        result, agent = self.run_scenario(mobile,
            [action('tap', ref='@earlier'), action('tap', ref='@e1'), action()])
        self.assertEqual(len(agent.calls), 3)
        self.assertIn('Adapter could not resolve', result['steps'][1]['actionError'])
        self.assertEqual([args['ref'] for name, args in mobile.calls
            if name == 'mobile_click_on_screen_at_coordinates'], ['@earlier', '@e1'])
        self.assertNotIn('rejectedResponses', result)
        self.assertFalse(self.control.stopped.is_set())

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
        result, _ = self.run_scenario(FakeMobile(self.root, elements=[]), [action(checks=[], completion='blocked')])
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
        self.assertIn("Open: unclassified", remaining)

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


    def test_reporting_metadata_does_not_discard_an_ai_selected_tap(self):
        response = action('tap', ref='@e1', checks=[dict(check(), requirementId='REQ-0001')])
        agent, _, transport = api_agent([response, action()])
        mobile = FakeMobile(self.root)
        result = {'scenarios': []}
        self.runner.run(mobile, self.build, result, agent, lambda: None)
        self.assertEqual(len([name for name, _ in mobile.calls if name.startswith('mobile_click')]), 1)
        self.assertEqual(len(transport.bodies), 2)
        self.assertNotIn('rejectedResponses', result['scenarios'][0])

    def test_more_than_three_notes_do_not_trigger_a_format_stop(self):
        agent, budget, _ = api_agent(['AI working note'] * 4 + [action('tap', ref='@e1'), action()])
        mobile = FakeMobile(self.root)
        result = {'scenarios': []}
        self.runner.run(mobile, self.build, result, agent, lambda: None)
        self.assertEqual(budget.requests, 6)
        self.assertEqual(len([name for name, _ in mobile.calls if name.startswith('mobile_click')]), 1)
        self.assertEqual(result['scenarios'][0]['decisions'][0]['response']['modelResponse'], 'AI working note')

    def test_unknown_catalogue_reference_remains_an_unbound_ai_check(self):
        response = action(checks=[dict(check(), source='requirements', requirementId='UNKNOWN')])
        agent, _, _ = api_agent([response])
        result = {'scenarios': []}
        self.runner.run(FakeMobile(self.root, elements=[]), self.build, result, agent, lambda: None)
        scenario = result['scenarios'][0]
        self.assertEqual(scenario['checks'][0]['requirementId'], 'UNKNOWN')
        self.assertNotIn('rejectedResponses', scenario)

    def test_override_interpretation_is_recorded_without_a_quotation_gate(self):
        definitions = [dict(id='REQ-0001', text='Save works', startLine=1, endLine=1)]
        declared = dict(check(), taskId=1, source='requirements', requirementId='REQ-0001',
            status='overridden', instructionQuote='AI interpretation', reason='Conflict described by AI')
        agent, _, _ = api_agent([action(checks=[declared])])
        result = {'scenarios': []}
        self.create_runner(definitions).run(FakeMobile(self.root, elements=[]), self.build, result, agent, lambda: None)
        self.assertEqual(result['scenarios'][0]['requirements'][0]['status'], 'overridden')
        self.assertNotIn('rejectedResponses', result['scenarios'][0])

    def test_ai_failure_is_not_discarded_with_other_reporting_metadata(self):
        response = action(checks=[check('failed'), dict(check(), requirementId='REQ-0001')])
        agent, _, _ = api_agent([response])
        result = {'scenarios': []}
        self.runner.run(FakeMobile(self.root, elements=[]), self.build, result, agent, lambda: None)
        self.assertEqual(result['scenarios'][0]['verdict'], 'failed')
        self.assertEqual(len(result['scenarios'][0]['checks']), 2)

    def test_rejected_metadata_and_correction_feedback_are_redacted(self):
        self.redactor = Redactor({"credentials": {"test": {"password": "synthetic-secret"}}})
        runner = self.create_runner()
        bad = action(checks=[dict(check(), requirementId="synthetic-secret")])
        agent, _, transport = api_agent([bad, action()])
        result = {"scenarios": []}
        runner.run(FakeMobile(self.root, elements=[]), self.build, result, agent, lambda: None)
        self.assertNotIn("synthetic-secret", json.dumps(result))
        self.assertNotIn("synthetic-secret", json.dumps(transport.bodies))

    def test_unreadable_command_is_retained_as_a_note_for_the_ai(self):
        agent, _, transport = api_agent(['{broken', action()])
        result = {'scenarios': []}
        self.runner.run(FakeMobile(self.root, elements=[]), self.build, result, agent, lambda: None)
        response = result['scenarios'][0]['decisions'][0]['response']
        self.assertEqual(response['modelResponse'], '{broken')
        state = json.loads(transport.bodies[1]['input'][1]['content'][0]['text'])
        self.assertIn('Unreadable reply text', state['resourceFeedback'])

    def test_notes_still_respect_the_shared_request_budget(self):
        budget = Budget(MODEL, 5, 'USD')
        budget.limit = budget.bound
        agent, _, transport = api_agent(['{broken', action()], budget)
        result = {'scenarios': []}
        with self.assertRaises(LimitReached):
            self.runner.run(FakeMobile(self.root, elements=[]), self.build, result, agent, lambda: None)
        self.assertEqual(len(transport.bodies), 1)
        self.assertEqual(result['scenarios'][0]['decisions'][0]['response']['modelResponse'], '{broken')

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


    def test_each_dispatched_action_returns_fresh_evidence_to_the_ai(self):
        first = action('tap', ref='@e1', checks=[dict(check(), requirementId='REQ-0001')])
        agent, _, transport = api_agent([first, action('tap', ref='@e2'), action(completion='blocked')])
        mobile = ChangingScreenMobile(self.root)
        self.runner.run(mobile, self.build, {'scenarios': []}, agent, lambda: None)
        state = json.loads(transport.bodies[1]['input'][1]['content'][0]['text'])
        self.assertEqual(state['elements'][0]['ref'], '@e2')
        self.assertEqual([args['ref'] for name, args in mobile.calls if name.startswith('mobile_click')], ['@e1', '@e2'])

    def test_expired_deadline_prevents_another_turn_after_a_note(self):
        transport = DeadlineTransport(['{broken', action()], self.control)
        agent = Agent({'ai-model': {'name': MODEL, 'api-key': 'synthetic'}},
            Budget(MODEL, 5, 'USD'), time.time() + 30, transport=transport)
        result = {'scenarios': []}
        with self.assertRaisesRegex(LimitReached, 'Whole-run time limit'):
            self.runner.run(FakeMobile(self.root), self.build, result, agent, lambda: None)
        self.assertEqual(len(transport.bodies), 1)
        self.assertNotIn('rejectedResponses', result['scenarios'][0])

    def test_accepted_failure_survives_later_response_corrections(self):
        bad = action(checks=[dict(check(), requirementId="REQ-0001")])
        agent, _, _ = api_agent([action("tap", ref="@e1", checks=[check("failed")]), bad, action()])
        result = {"scenarios": []}
        self.runner.run(FakeMobile(self.root), self.build, result, agent, lambda: None)
        self.assertEqual(result["scenarios"][0]["verdict"], "failed")

    def test_ui_read_failure_stops_before_sending_another_instruction(self):
        transport = ScriptedTransport(['{broken', action()])
        agent = Agent({'ai-model': {'name': MODEL, 'api-key': 'synthetic'}},
            Budget(MODEL, 5, 'USD'), time.time() + 30, transport=transport)
        with self.assertRaises(InfrastructureError):
            self.runner.run(FailingRefreshMobile(self.root, transport), self.build, {'scenarios': []}, agent, lambda: None)
        self.assertEqual(len(transport.bodies), 1)

    def test_next_instruction_refreshes_controls_even_after_a_note_without_an_action(self):
        agent, _, transport = api_agent(['AI note', action()])
        class ChangedScreenMobile(FakeMobile):
            def snapshot(self):
                label = 'New screen' if transport.bodies else 'Initial screen'
                _, image = super().snapshot()
                return [dict(BUTTON, label=label)], image
        self.runner.run(ChangedScreenMobile(self.root), self.build, {'scenarios': []}, agent, lambda: None)
        next_input = json.loads(transport.bodies[1]['input'][1]['content'][0]['text'])
        self.assertEqual(next_input['humanInterface'][0]['label'], 'New screen')


    def test_activity_has_no_response_format_rejection_phase(self):
        output = io.StringIO()
        activity = ActivityLog(self.root, self.redactor, output=output)
        agent, _, _ = api_agent(['{broken', action()])
        self.create_runner(activity=activity).run(FakeMobile(self.root, elements=[]), self.build,
            {'scenarios': []}, agent, lambda: None)
        rows = [json.loads(line) for line in activity.path.read_text().splitlines()]
        self.assertFalse(any(row['operation'] == 'AI response correction' for row in rows))
        self.assertNotIn('{broken', output.getvalue())

    def test_note_does_not_create_a_rejected_response_screenshot(self):
        session = ScenarioSession({'target': 'Release', 'steps': [], 'requirements': []},
            'com.example.app', 'fixture', [BUTTON], b'masked')
        recovery = AiInteraction(dict(instructions='Explore'), {}, self.redactor, self.control)
        agent, _, transport = api_agent(['{broken'])
        evidence = ScenarioEvidence(self.root, self.root)
        response = recovery.choose(FakeMobile(self.root), session, agent, evidence, lambda: None)
        self.assertEqual(response['action'], 'note')
        self.assertNotIn('rejectedResponses', session.result)
        self.assertEqual(len(transport.bodies), 1)

    def test_incomplete_provider_response_is_not_a_correction_error(self):
        with self.assertRaises(InfrastructureError) as raised:
            parse_action({"status": "incomplete", "output": []})


    def test_repetition_information_does_not_veto_the_fourth_ai_selected_tap(self):
        tap = action('tap', ref='@e1')
        agent, _, _ = api_agent([tap, tap, tap, tap, action(recovery=dict(id=0, decision='replan', reason='Finish the observed objective'))])
        mobile = FakeMobile(self.root)
        result = {'scenarios': []}
        self.runner.run(mobile, self.build, result, agent, lambda: None)
        taps = [name for name, _ in mobile.calls if name.startswith('mobile_click')]
        self.assertEqual(len(taps), 4)
        scenario = result['scenarios'][0]
        self.assertEqual(scenario['recoveries'][0]['status'], 'continued')
        self.assertEqual(scenario['exploration']['paths'][0]['attempts'], 4)

    def test_ai_can_report_recovery_blocked_without_stopping_other_scenarios(self):
        tap = action('tap', ref='@e1')
        agent, _, _ = api_agent([tap] * 3 + [action(completion='blocked',
            remaining=['No productive path remains'], recovery=dict(id=0, decision='blocked', reason='All alternatives need unavailable equipment'))])
        mobile = FakeMobile(self.root)
        result = {'scenarios': []}
        self.runner.run(mobile, self.build, result, agent, lambda: None)
        scenario = result['scenarios'][0]
        self.assertEqual(scenario['completion'], 'incomplete')
        self.assertIn('No productive path remains', scenario['remaining'])
        self.assertEqual(scenario['recoveries'][0]['status'], 'blocked')
        self.assertFalse(self.control.stopped.is_set())
        self.assertEqual(len([name for name, _ in mobile.calls if name.startswith('mobile_click')]), 3)

    def test_model_receives_memory_with_observed_previous_outcome(self):
        agent, _, transport = api_agent([action('tap', ref='@e1'), action()])
        self.runner.run(FakeMobile(self.root), self.build, {'scenarios': []}, agent, lambda: None)
        state = json.loads(transport.bodies[1]['input'][1]['content'][0]['text'])
        self.assertEqual(state['explorationMemory']['currentControls'][0]['attempts'], 1)
        self.assertEqual(state['recentActions'][0]['result'], 'No observed UI change after the action')
        self.assertEqual(state['recentActions'][0]['controlLabel'], 'Open')

    def test_recall_updates_ai_context_without_touching_the_device(self):
        recall = action('recall', context=dict(summary='Remember the first observation', includeAll=['tasks'], records=[]))
        result, agent = self.run_scenario(FakeMobile(self.root, elements=[]), [recall, action()])
        self.assertEqual(len(agent.calls), 2)
        self.assertEqual(agent.calls[1][-1]['summary'], 'Remember the first observation')
        self.assertEqual(agent.calls[1][-1]['selectedActions'], [])
        self.assertEqual(len(result['decisions']), 2)
        self.assertEqual(len(result['steps']), 2)  # Reset evidence and the final check only.

    def test_ai_finish_is_not_rejected_by_a_host_plan_evaluation(self):
        result, agent = self.run_scenario(FakeMobile(self.root), [action()])
        self.assertEqual(len(agent.calls), 1)
        self.assertEqual(result['completion'], 'incomplete')
        self.assertTrue(result['remaining'])
        self.assertEqual(result['recoveries'], [])

    def test_ai_can_detect_a_loop_before_the_repetition_counter_does(self):
        request = action('recover', recovery=dict(id=-1, decision='replan', reason='I revisited the same menu'))
        finish = action(recovery=dict(id=0, decision='replan', reason='Fresh evidence shows the objective is complete'))
        mobile = FakeMobile(self.root, elements=[])
        result, agent = self.run_scenario(mobile, [request, finish])
        self.assertEqual([name for name, _ in mobile.calls], ['reset'])
        self.assertEqual(agent.calls[1][-1]['recoveryRequest']['kind'], 'AI detected loop')
        self.assertEqual(result['recoveries'][0]['status'], 'continued')

    def test_every_new_loop_requests_recovery_without_a_three_recovery_stop(self):
        tap = action('tap', ref='@e1')
        responses = [tap] * 6 + [action()]
        agent, budget, _ = api_agent(responses)
        mobile = FakeMobile(self.root)
        result = {'scenarios': []}
        self.runner.run(mobile, self.build, result, agent, lambda: None)
        scenario = result['scenarios'][0]
        self.assertEqual(len(scenario['recoveries']), 4)
        self.assertTrue(all(row['status'] == 'continued' for row in scenario['recoveries']))
        self.assertEqual(len([name for name, _ in mobile.calls if name.startswith('mobile_click')]), 6)
        self.assertEqual(scenario['completion'], 'complete')
        self.assertTrue(any(row['kind'] == 'recovery' for row in budget.usage_records))

    def test_ai_can_retrieve_history_during_recovery_before_selecting_an_action(self):
        tap = action('tap', ref='@e1')
        recall = action('recall', context=dict(summary='Inspect earlier outcomes', includeAll=['actions'], records=[]))
        finish = action(recovery=dict(id=0, decision='replan', reason='The retained evidence covers this objective'))
        agent, _, transport = api_agent([tap] * 3 + [recall, finish])
        mobile = FakeMobile(self.root)
        result = {'scenarios': []}
        self.runner.run(mobile, self.build, result, agent, lambda: None)
        state = json.loads(transport.bodies[-1]['input'][1]['content'][0]['text'])
        self.assertEqual(len(state['recentActions']), 3)
        self.assertEqual(state['explorationMemory']['recoveryRequest']['id'], 0)
        self.assertEqual(len([name for name, _ in mobile.calls if name.startswith('mobile_click')]), 3)

    def test_cancellation_during_recovery_keeps_partial_evidence_and_prevents_actions(self):
        tap = action('tap', ref='@e1')
        scripted = iter([tap] * 4)
        def choose(*arguments):
            if 'recoveryRequest' in arguments[-1]:
                self.control.interrupt()
                raise LimitReached('User interrupted execution')
            return next(scripted)
        mobile = FakeMobile(self.root)
        result = {'scenarios': []}
        with self.assertRaisesRegex(LimitReached, 'User interrupted'):
            self.runner.run(mobile, self.build, result, SimpleNamespace(choose=choose), lambda: None)
        scenario = result['scenarios'][0]
        self.assertEqual(scenario['recoveries'][0]['status'], 'waiting')
        self.assertTrue(scenario['remaining'])
        self.assertEqual(len([name for name, _ in mobile.calls if name.startswith('mobile_click')]), 3)

    def test_only_ai_selected_historical_screenshots_are_added_to_the_next_request(self):
        class FramesMobile(FakeMobile):
            def snapshot(self):
                tapped = any(name.startswith('mobile_click') for name, _ in self.calls)
                return self.elements, b'masked second frame' if tapped else b'masked first frame'
        chosen = dict(summary='Compare the old screen', includeAll=[], records=[dict(collection='screenshots', id='0')])
        agent, _, transport = api_agent([action('tap', ref='@e1', context=chosen), action()])
        self.runner.run(FramesMobile(self.root), self.build, {'scenarios': []}, agent, lambda: None)
        first = transport.bodies[0]['input'][1]['content']
        second = transport.bodies[1]['input'][1]['content']
        self.assertEqual(sum(item['type'] == 'input_image' for item in first), 1)
        self.assertEqual(sum(item['type'] == 'input_image' for item in second), 2)
        self.assertTrue(any('Selected historical screenshot 0' in item.get('text', '') for item in second))

    def test_failure_check_survives_while_the_ai_selected_action_is_executed(self):
        tap = action('tap', ref='@e1')
        observed_failure = action('tap', ref='@e1', checks=[check('failed')])
        blocked = action(completion='blocked', checks=[], remaining=['No further productive path'],
            recovery=dict(id=1, decision='blocked', reason='The observed failure prevents further progress'))
        result, _ = self.run_scenario(FakeMobile(self.root), [tap] * 3 + [observed_failure, blocked])
        self.assertEqual(result['verdict'], 'failed')
        self.assertEqual(len(result['checks']), 1)
        self.assertEqual(result['checks'][0]['status'], 'failed')
        self.assertEqual(result['recoveries'][1]['status'], 'blocked')

    def test_recovery_metadata_does_not_trigger_format_exhaustion(self):
        tap = action('tap', ref='@e1')
        response = action('tap', ref='@e1', recovery=dict(id=999, decision='replan', reason='AI note'))
        agent, _, _ = api_agent([tap] * 3 + [response, action(completion='blocked')])
        mobile = FakeMobile(self.root)
        result = {'scenarios': []}
        self.runner.run(mobile, self.build, result, agent, lambda: None)
        self.assertNotIn('rejectedResponses', result['scenarios'][0])
        self.assertEqual(len([name for name, _ in mobile.calls if name.startswith('mobile_click')]), 4)

    def test_user_stop_prevents_an_action_after_ai_returns(self):
        self.control.interrupt()
        mobile = FakeMobile(self.root)
        executor = ActionExecutor({}, self.redactor, self.control.deadline, check=self.control.check)
        with self.assertRaisesRegex(LimitReached, 'User interrupted'):
            executor.execute(mobile, action('tap', ref='@e1'), mobile.elements)
        self.assertFalse(mobile.calls)


    def test_interrupted_credential_focus_is_retained_without_typing_the_secret(self):
        config = {'credentials': {'test': {'username': 'synthetic-user', 'password': 'synthetic-password'}}}
        redactor = Redactor(config)
        executor = ActionExecutor(config, redactor, self.control.deadline, check=self.control.check)
        runner = ScenarioRunner({'instructions': 'Explore'}, config, redactor, self.control, executor,
                                self.root, sleep=lambda _: None)
        mobile = StopAfterFocusMobile(self.root, self.control)
        result = {'scenarios': []}
        agent = FakeAgent([action('credential', ref='@e1', credential='test', field='username')])
        with self.assertRaisesRegex(LimitReached, 'User interrupted'):
            runner.run(mobile, self.build, result, agent, lambda: None)
        self.assertTrue(any(name.startswith('mobile_click') for name, _ in mobile.calls))
        self.assertFalse(any(name == 'mobile_type_keys' for name, _ in mobile.calls))
        self.assertIn('User interrupted', result['scenarios'][0]['steps'][-1]['stoppingReason'])
        self.assertIn('User interrupted', result['scenarios'][0]['steps'][-1]['observedOutcome'])
        self.assertNotIn('actionError', result['scenarios'][0]['steps'][-1])
        self.assertNotIn('synthetic-user', json.dumps(result))


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

    def test_rejected_app_launch_is_a_device_error_and_is_redacted(self):
        redactor = Redactor({'ai-model': {'api-key': 'synthetic-secret'}})
        result = dict(isError=True, content=[dict(text='Launch failed synthetic-secret')])
        with self.assertRaises(AppLaunchError) as raised:
            RpcMessages.tool_result(result, 'mobile_launch_app', redactor.text)
        self.assertIn('Launch failed', str(raised.exception))
        self.assertNotIn('synthetic-secret', str(raised.exception))

    def test_other_tool_errors_keep_the_shared_infrastructure_policy(self):
        result = dict(isError=True, content=[dict(text='Connection unavailable')])
        with self.assertRaises(InfrastructureError) as raised:
            RpcMessages.tool_result(result, 'mobile_list_elements_on_screen', lambda text: text)
        self.assertNotIsInstance(raised.exception, AppLaunchError)

    def test_answered_interaction_error_is_returned_as_device_action_feedback(self):
        for name in ['mobile_click_on_screen_at_coordinates', 'mobile_type_keys',
                     'mobile_swipe_on_screen', 'mobile_press_button']:
            with self.subTest(tool=name):
                with self.assertRaises(DeviceActionError):
                    RpcMessages.tool_result(dict(isError=True, content=[dict(text='Target unavailable')]),
                        name, lambda text: text)

    def test_unobserved_credential_target_never_receives_secret_text(self):
        mobile = FakeMobile(pathlib.Path('/unused'), elements=[SIZE])
        config = dict(credentials={'test': dict(username='synthetic-user', password='synthetic-secret')})
        executor = ActionExecutor(config, Redactor(config), time.time() + 30)
        with self.assertRaises(ValueError):
            executor.execute(mobile, action('credential', ref='@earlier', credential='test', field='password'), [SIZE])
        self.assertFalse(mobile.calls)

    def test_successful_launch_keeps_the_adapter_result(self):
        result = dict(content=[dict(text='Started')])
        self.assertIs(RpcMessages.tool_result(result, 'mobile_launch_app', lambda text: text), result)

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
