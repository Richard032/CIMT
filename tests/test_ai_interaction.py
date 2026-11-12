"""Context-only exchanges use synthetic observations and a scripted API transport."""

import io
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'runtime'))
from activity import ActivityLog
from ai_interaction import AiInteraction
from errors import InfrastructureError, LimitReached
from evidence import ScenarioEvidence
from redaction import Redactor
from run_control import RunControl
from scenario import ScenarioSession
from test_context_memory import selection
from test_runtime_components import FakeAgent, FakeMobile, BUTTON, action, api_agent


class CountingMobile(FakeMobile):
    def __init__(self, folder):
        super().__init__(folder)
        self.captures = 0

    def snapshot(self):
        self.captures += 1
        return [dict(BUTTON, label='Fresh screen')], b'fresh masked image'


class AiInteractionTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.redactor = Redactor({})
        self.control = RunControl(float('inf'))
        self.activity = ActivityLog(self.root, self.redactor, io.StringIO())
        self.interaction = AiInteraction(dict(instructions='Explore'), {}, self.redactor,
                                         self.control, self.activity)
        self.session = ScenarioSession(dict(target='Debug', steps=[], requirements=[]),
            'com.example.app', 'fixture', [BUTTON], b'old masked image')
        self.evidence = ScenarioEvidence(self.root, self.root)
        self.mobile = CountingMobile(self.root)

    def select_large_history(self):
        self.session.planner.observe([dict(type='Text', text='x' * 70000)])
        self.session.planner.context_memory.accept(selection(include_all=['observations']))
        self.session.observed_at = '2026-11-09T22:55:00.000+00:00'

    def test_context_requests_refresh_evidence_in_conversation(self):
        self.select_large_history()
        agent = FakeAgent([action('recall'), action('recall')])
        for _ in range(2):
            self.interaction.choose(self.mobile, self.session, agent, self.evidence, lambda: None)
        self.assertEqual(self.mobile.captures, 2)
        self.assertEqual(len(self.evidence.images), 1)
        for arguments in agent.calls:
            self.assertFalse(arguments[-1]['currentEvidence']['reusedForContextSelection'])
            self.assertNotEqual(arguments[-1]['currentEvidence']['observedAt'],
                                '2026-11-09T22:55:00.000+00:00')

    def test_reduced_selection_refreshes_changed_screen_before_normal_decision(self):
        self.select_large_history()
        self.session.planner.context_memory.accept(selection())
        agent = FakeAgent([action()])
        self.interaction.choose(self.mobile, self.session, agent, self.evidence, lambda: None)
        self.assertEqual(self.mobile.captures, 1)
        self.assertEqual(agent.calls[0][3][0]['label'], 'Fresh screen')
        self.assertEqual(agent.calls[0][4], b'fresh masked image')
        self.assertFalse(agent.calls[0][-1]['currentEvidence']['reusedForContextSelection'])
        self.assertNotEqual(self.session.observed_at, '2026-11-09T22:55:00.000+00:00')

    def test_device_action_invalidates_reuse_even_when_history_remains_large(self):
        self.select_large_history()
        self.interaction.choose(self.mobile, self.session, FakeAgent([action()]), self.evidence, lambda: None)
        self.assertEqual(self.mobile.captures, 1)

    def test_unknown_capture_time_requires_a_fresh_observation(self):
        self.select_large_history()
        self.session.observed_at = None
        self.interaction.choose(self.mobile, self.session, FakeAgent([action()]), self.evidence, lambda: None)
        self.assertEqual(self.mobile.captures, 1)

    def test_later_request_has_current_context_without_conversation_history(self):
        self.session.history.append(dict(action='tap', observation='First step'))
        agent, _, transport = api_agent([action('tap', ref='@e1'), action()])
        self.interaction.choose(self.mobile, self.session, agent, self.evidence, lambda: None)
        self.session.history.append(dict(action='wait', observation='Second step'))
        self.interaction.choose(self.mobile, self.session, agent, self.evidence, lambda: None)

        messages = transport.bodies[1]['input']
        self.assertEqual([message['role'] for message in messages], ['system', 'user'])
        current = json.loads(messages[1]['content'][0]['text'])
        self.assertEqual(current['instructions'], 'Explore')
        self.assertIn('commandResources', current)
        self.assertEqual([row['observation'] for row in current['recentActions']],
                         ['First step', 'Second step'])
        self.assertEqual(current['elements'][0]['label'], 'Fresh screen')
        self.assertEqual(messages[1]['content'][1]['type'], 'input_image')

    def test_each_decision_records_redacted_request_and_screenshot_reference(self):
        secret = 'fixture-private-password'
        redactor = Redactor({'credentials': {'login': {'password': secret}}})
        interaction = AiInteraction(dict(instructions='Use ' + secret), {}, redactor,
                                    self.control, self.activity)
        agent, _, transport = api_agent([action('tap', ref='@e1'), action()])
        interaction.choose(self.mobile, self.session, agent, self.evidence, lambda: None)
        self.session.history.append(dict(action='tap', observation='First step'))
        interaction.choose(self.mobile, self.session, agent, self.evidence, lambda: None)

        records = self.session.result['aiRequests']
        self.assertEqual(len(records), 2)
        self.assertTrue(all(row['status'] == 'completed' for row in records))
        self.assertTrue(all(row['inputTokens'] == 10 for row in records))
        self.assertGreater(records[1]['sectionBytes']['recentActions'], 0)
        path = self.root / records[1]['requestPath']
        text = path.read_text()
        self.assertNotIn(secret, text)
        self.assertNotIn('data:image/png;base64,', text)
        payload = json.loads(text)
        user = payload['input'][-1]['content']
        self.assertEqual(user[0]['text']['instructions'], 'Use <redacted>')
        self.assertEqual(user[0]['text']['recentActions'][0]['observation'], 'First step')
        self.assertEqual(user[1]['imageEvidence'], records[1]['images'][0])
        self.assertEqual((self.root / records[1]['images'][0]).read_bytes(), b'fresh masked image')
        self.assertEqual(transport.bodies[1]['input'][-1]['content'][1]['type'], 'input_image')

    def test_failed_provider_request_is_still_recorded(self):
        agent, _, _ = api_agent([])
        def failed(path, body):
            raise InfrastructureError('Synthetic failure')
        agent.transport.request = failed
        with self.assertRaises(InfrastructureError):
            self.interaction.choose(self.mobile, self.session, agent, self.evidence, lambda: None)
        record = self.session.result['aiRequests'][0]
        self.assertEqual(record['status'], 'failed')
        self.assertTrue((self.root / record['requestPath']).is_file())

    def test_invalid_usage_still_records_the_provider_request_outcome(self):
        agent, budget, _ = api_agent([])
        agent.transport.request = lambda path, body: dict(status='completed',
            usage=dict(input_tokens=10, output_tokens=999999))
        with self.assertRaises(InfrastructureError):
            self.interaction.choose(self.mobile, self.session, agent, self.evidence, lambda: None)
        self.assertEqual(self.session.result['aiRequests'][0]['status'], 'completed')
        self.assertEqual(budget.uncertain, budget.bound)

    def test_sdk_refusal_stops_without_exposing_provider_text_or_retrying(self):
        agent, budget, transport = api_agent([])
        response = dict(status="completed", usage=dict(input_tokens=10, output_tokens=3),
                        output=[dict(type="message", content=[
                            dict(type="refusal", refusal="private provider refusal")])])
        transport.request = lambda path, body: response

        with self.assertRaisesRegex(InfrastructureError, "^OpenAI refused the request; no action executed$"):
            self.interaction.choose(self.mobile, self.session, agent, self.evidence, lambda: None)

        self.assertEqual(budget.snapshot()["requests"], 1)
        self.assertEqual(len(self.session.result["aiRequests"]), 1)

    def test_output_limit_retry_has_its_own_request_record(self):
        agent, _, _ = api_agent([])
        responses = iter([
            dict(status='incomplete', incomplete_details=dict(reason='max_output_tokens'),
                 usage=dict(input_tokens=10, output_tokens=2048)),
            dict(status='completed', usage=dict(input_tokens=11, output_tokens=12),
                 output=[dict(type='message', content=[dict(type='output_text', text='{"action":"wait"}')])]),
        ])
        agent.transport.request = lambda path, body: next(responses)
        self.interaction.choose(self.mobile, self.session, agent, self.evidence, lambda: None)
        rows = self.session.result['aiRequests']
        self.assertEqual([row['kind'] for row in rows], ['decision', 'decision retry'])
        self.assertEqual([row['status'] for row in rows], ['incomplete', 'completed'])
        retry = json.loads((self.root / rows[1]['requestPath']).read_text())
        self.assertIn('none of its commands ran', retry['input'][-1]['content'][-1]['text'])

    def test_provider_time_is_separate_from_context_and_capture_operations(self):
        agent, _, _ = api_agent([action()])
        ticks = iter([10, 13.25])
        agent.clock = lambda: next(ticks)
        self.interaction.choose(self.mobile, self.session, agent, self.evidence, lambda: None)
        records = [json.loads(line) for line in self.activity.path.read_text().splitlines()]
        provider = [row for row in records if row['operation'] == 'AI provider response']
        self.assertEqual(len(provider), 1)
        self.assertEqual(provider[0]['durationSeconds'], 3.25)
        self.assertEqual(provider[0]['message'], 'decision')
        self.assertEqual(provider[0]['device'], self.mobile.device['id'])
        completed = {row['operation'] for row in records if row['status'] == 'completed'}
        self.assertTrue({'Prepare AI context', 'Refresh AI screen evidence', 'AI action decision'} <= completed)

    def test_transport_failure_records_time_and_preserves_uncertain_budget(self):
        agent, budget, _ = api_agent([])
        def failed(path, body):
            raise InfrastructureError('Synthetic transport failure')
        agent.transport.request = failed
        ticks = iter([10, 12])
        agent.clock = lambda: next(ticks)
        with self.assertRaises(InfrastructureError):
            self.interaction.choose(self.mobile, self.session, agent, self.evidence, lambda: None)
        self.assertEqual(agent.last_request_timing, dict(kind='decision', status='failed', seconds=2))
        self.assertGreater(budget.uncertain, 0)
        records = [json.loads(line) for line in self.activity.path.read_text().splitlines()]
        self.assertEqual([row['status'] for row in records if row['operation'] == 'AI provider response'], ['failed'])

    def test_unfunded_request_does_not_reuse_previous_provider_timing(self):
        agent, budget, _ = api_agent([action()])
        self.interaction.choose(self.mobile, self.session, agent, self.evidence, lambda: None)
        budget.limit = 0
        with self.assertRaises(LimitReached):
            self.interaction.choose(self.mobile, self.session, agent, self.evidence, lambda: None)
        records = [json.loads(line) for line in self.activity.path.read_text().splitlines()]
        self.assertEqual(sum(row['operation'] == 'AI provider response' for row in records), 1)
        self.assertIsNone(agent.last_request_timing)
