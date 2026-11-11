"""Tests for scenario evidence and completion review."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'runtime'))
from result_review.ledger import EvidenceLedger
from result_review.critic import CompletionCritic
from errors import InfrastructureError
import json


class EvidenceLedgerTests(unittest.TestCase):
    def test_records_action_and_outcome_without_inventing_success(self):
        result = dict(steps=[dict(step=1, action=dict(action='tap', commandId=7, text='private'),
            controlLabel='Login', targetIdentifier='menu_login', targetType='TextView',
            actionDispatched=True, observedOutcome='Login form appeared')], checks=[])
        ledger = EvidenceLedger().snapshot(result)
        self.assertEqual(ledger['steps'][0]['action'], dict(action='tap', commandId=7))
        self.assertEqual(ledger['steps'][0]['targetIdentifier'], 'menu_login')
        self.assertEqual(ledger['steps'][0]['targetType'], 'TextView')
        self.assertEqual(ledger['steps'][0]['observedOutcome'], 'Login form appeared')
        self.assertEqual(ledger['checks'], [])

    def test_discloses_earlier_omitted_steps(self):
        result = dict(steps=[dict(step=i, action='wait') for i in range(205)], checks=[])
        ledger = EvidenceLedger().snapshot(result)
        self.assertEqual(ledger['omittedEarlierSteps'], 5)
        self.assertEqual(ledger['steps'][0]['step'], 5)

    def test_observation_time_is_linked_to_the_recorded_step(self):
        result = dict(steps=[dict(step=2, action='wait')], checks=[],
            batchFeedback=dict(batches=[dict(path=[dict(kind='command', step=2, observedAt='2026-01-01T00:00:03Z')])]))
        ledger = EvidenceLedger().snapshot(result)
        self.assertEqual(ledger['steps'][0]['observedAt'], '2026-01-01T00:00:03Z')

    def test_keeps_distinct_check_evidence(self):
        result = dict(steps=[], checks=[dict(id=3, status='failed', expected='Ready', observed='Still loading')])
        ledger = EvidenceLedger().snapshot(result)
        self.assertEqual(ledger['checks'][0]['observed'], 'Still loading')
        self.assertEqual(ledger['checks'][0]['status'], 'failed')


class CompletionCriticTests(unittest.TestCase):
    def test_passes_evidence_to_budgeted_request_and_parses_feedback(self):
        calls = []
        def request(body, kind):
            calls.append((body, kind))
            return dict(status='completed', output=[dict(type='message', content=[
                dict(type='output_text', text='{"decision":"revise","feedback":"More work remains"}')])])
        result = CompletionCritic('fixture', request, 100).review(dict(ledger={'steps': [1]}))
        self.assertEqual(result['decision'], 'revise')
        self.assertEqual(calls[0][1], 'completion critic')
        self.assertEqual(json.loads(calls[0][0]['input'][1]['content'][0]['text'])['ledger']['steps'], [1])

    def test_invalid_response_is_not_accepted_as_a_review(self):
        def request(body, kind):
            return dict(status='completed', output=[dict(type='message', content=[
                dict(type='output_text', text='{"decision":"agree"}')])])
        with self.assertRaises(InfrastructureError):
            CompletionCritic('fixture', request, 100).review({})
