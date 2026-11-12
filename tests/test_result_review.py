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
        self.assertEqual(ledger['recordedEvidence']['steps'][0]['action'], dict(action='tap', commandId=7))
        self.assertEqual(ledger['recordedEvidence']['steps'][0]['targetIdentifier'], 'menu_login')
        self.assertEqual(ledger['recordedEvidence']['steps'][0]['targetType'], 'TextView')
        self.assertEqual(ledger['recordedEvidence']['steps'][0]['observedOutcome'], 'Login form appeared')
        self.assertEqual(ledger['aiInterpretations']['checks'], [])

    def test_retains_actor_progress_as_a_claim_with_recorded_evidence(self):
        ledger = EvidenceLedger().snapshot(dict(steps=[], checks=[], evidenceProgress='One completed; command 2.'))
        self.assertEqual(ledger['aiInterpretations']['progressNote'], 'One completed; command 2.')

    def test_separates_ai_explanations_and_checks_from_execution_records(self):
        result = dict(steps=[dict(step=2, action=dict(action='tap', commandId=3),
                                  observation='AI: startup form', observedOutcome='Observed UI changed')],
                      checks=[dict(id=1, status='passed', observed='AI: submission succeeded')],
                      evidenceProgress='AI: startup is complete')
        ledger = EvidenceLedger().snapshot(result)
        self.assertEqual(ledger['recordedEvidence']['steps'][0]['observedOutcome'], 'Observed UI changed')
        self.assertNotIn('observation', ledger['recordedEvidence']['steps'][0])
        self.assertEqual(ledger['aiInterpretations']['stepExplanations'], [dict(step=2, text='AI: startup form')])
        self.assertEqual(ledger['aiInterpretations']['checks'][0]['status'], 'passed')
        self.assertEqual(ledger['aiInterpretations']['progressNote'], 'AI: startup is complete')

    def test_discloses_earlier_omitted_steps(self):
        result = dict(steps=[dict(step=i, action='wait') for i in range(205)], checks=[])
        ledger = EvidenceLedger().snapshot(result)
        self.assertEqual(ledger['recordedEvidence']['omittedEarlierSteps'], 5)
        self.assertEqual(ledger['recordedEvidence']['steps'][0]['step'], 5)

    def test_observation_time_is_linked_to_the_recorded_step(self):
        result = dict(steps=[dict(step=2, action='wait')], checks=[],
            batchFeedback=dict(batches=[dict(path=[dict(kind='command', step=2, observedAt='2026-01-01T00:00:03Z')])]))
        ledger = EvidenceLedger().snapshot(result)
        self.assertEqual(ledger['recordedEvidence']['steps'][0]['observedAt'], '2026-01-01T00:00:03Z')

    def test_recent_screen_uses_recorded_masked_ui_and_observation_time(self):
        result = dict(steps=[], checks=[],
            batchFeedback=dict(batches=[dict(
                observations=[dict(id='screen-1', uiObservation='ui-1')],
                path=[dict(kind='command', status='executed', step=2, observation='screen-1', observedAt='2026-01-01T00:00:03Z')])]),
            exploration=dict(applicationMap=dict(observations=[dict(id='ui-1',
                elements=[dict(type='Text', label='Ready', value='ignored')])])) )
        screen = EvidenceLedger().snapshot(result)['recordedEvidence']['recentScreens'][0]
        self.assertEqual(screen['observedAt'], '2026-01-01T00:00:03Z')
        self.assertEqual(screen['elements'], [dict(type='Text', label='Ready')])

    def test_recent_screen_discloses_omitted_elements(self):
        result = dict(steps=[], checks=[],
            batchFeedback=dict(batches=[dict(observations=[dict(id='s', uiObservation='u')],
                path=[dict(kind='command', status='executed', step=1, observation='s', observedAt='2026-01-01T00:00:03Z')])]),
            exploration=dict(applicationMap=dict(observations=[dict(id='u',
                elements=[dict(label=str(i)) for i in range(43)])])))
        screen = EvidenceLedger().snapshot(result)['recordedEvidence']['recentScreens'][0]
        self.assertEqual(screen['omittedElements'], 3)
        self.assertEqual(len(screen['elements']), 40)

    def test_keeps_distinct_check_evidence(self):
        result = dict(steps=[], checks=[dict(id=3, status='failed', expected='Ready', observed='Still loading')])
        ledger = EvidenceLedger().snapshot(result)
        self.assertEqual(ledger['aiInterpretations']['checks'][0]['observed'], 'Still loading')
        self.assertEqual(ledger['aiInterpretations']['checks'][0]['status'], 'failed')


class CompletionCriticTests(unittest.TestCase):
    def test_passes_evidence_to_budgeted_request_and_parses_feedback(self):
        calls = []
        def request(body, kind):
            calls.append((body, kind))
            return dict(status='completed', output=[dict(type='message', content=[
                dict(type='output_text', text='{"decision":"revise","feedback":"More work remains"}')])])
        result = CompletionCritic('fixture', request, 100).review(dict(ledger={'recordedEvidence': {'steps': [1]}, 'aiInterpretations': {'progressNote': 'claim'}}))
        self.assertEqual(result['decision'], 'revise')
        self.assertEqual(calls[0][1], 'completion critic')
        self.assertIn('blocked completion can correctly have an inconclusive check', calls[0][0]['input'][0]['content'])
        self.assertIn('Compare interpretations with the recorded sequence', calls[0][0]['input'][0]['content'])
        self.assertEqual(json.loads(calls[0][0]['input'][1]['content'][0]['text'])['ledger']['recordedEvidence']['steps'], [1])

    def test_invalid_response_is_not_accepted_as_a_review(self):
        def request(body, kind):
            return dict(status='completed', output=[dict(type='message', content=[
                dict(type='output_text', text='{"decision":"agree"}')])])
        with self.assertRaises(InfrastructureError):
            CompletionCritic('fixture', request, 100).review({})
