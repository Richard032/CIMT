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
        self.session.context_only = True
        self.session.observed_at = '2026-11-09T22:55:00.000+00:00'

    def test_repeated_context_only_requests_reuse_timestamped_evidence(self):
        self.select_large_history()
        agent = FakeAgent([action('recall'), action('recall')])
        for _ in range(2):
            self.interaction.choose(self.mobile, self.session, agent, self.evidence, lambda: None)
        self.assertEqual(self.mobile.captures, 0)
        self.assertEqual(len(self.evidence.images), 0)
        for arguments in agent.calls:
            self.assertEqual(arguments[-1]['currentEvidence'], dict(
                observedAt='2026-11-09T22:55:00.000+00:00', reusedForContextSelection=True))

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
        self.session.context_only = False
        self.interaction.choose(self.mobile, self.session, FakeAgent([action()]), self.evidence, lambda: None)
        self.assertEqual(self.mobile.captures, 1)

    def test_unknown_capture_time_requires_a_fresh_observation(self):
        self.select_large_history()
        self.session.observed_at = None
        self.interaction.choose(self.mobile, self.session, FakeAgent([action()]), self.evidence, lambda: None)
        self.assertEqual(self.mobile.captures, 1)

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
