"""Ordered feedback uses synthetic commands and already masked observations."""

import io
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'runtime'))
from activity import ActivityLog
from batch_feedback import BatchFeedback
from command_queue import CommandQueue
from device_adapter.warnings import android_anr
from evidence import ScenarioEvidence
from errors import InfrastructureError
from observation_recorder import ObservationRecorder
from redaction import Redactor
from test_planning.planner import TestPlanner


def observation(name):
    return dict(id=name, screen=name, uiObservation=name, timestamp='2026-01-01T00:00:00Z',
                screenshot=name + '.png', ui=name + '.json')


class BatchFeedbackTests(unittest.TestCase):
    def setUp(self):
        self.feedback = BatchFeedback()
        self.queue = CommandQueue()
        self.feedback.observe(observation('A'), [])

    def start(self, actions):
        self.queue.add(dict(actions[0], queuedCommands=actions[1:]))
        self.feedback.start(0)

    def perform(self, destination=None, error=''):
        self.queue.take()
        self.feedback.take(self.queue.current)
        if destination is not None:
            self.feedback.observe(observation(destination), [], action_result=True)
        row = self.queue.finish('failed' if error else 'executed', error, step=1)
        self.feedback.finish(row, error)

    def test_cycle_retains_each_intermediate_result_without_before_copies(self):
        self.start([dict(action='tap')] * 3)
        for destination in ('B', 'C', 'A'):
            self.perform(destination)
        batch = self.feedback.pending()[0]
        self.assertEqual(batch['initialObservation'], 'A')
        self.assertEqual([row['observation'] for row in batch['path']], ['B', 'C', 'A'])
        self.assertEqual(len(batch['observations']), 3)
        self.assertNotIn('before', json.dumps(batch))

    def test_unchanged_step_is_kept_with_its_observation_reference(self):
        self.start([dict(action='tap')])
        self.perform('A')
        path = self.feedback.pending()[0]['path']
        self.assertEqual(path[0]['uiChange'], 'no observed change')
        self.assertEqual(path[0]['observation'], 'A')

    def test_missing_observation_is_not_replaced_with_the_previous_state(self):
        self.start([dict(action='tap')])
        self.perform(error='Observation failed')
        path = self.feedback.pending()[0]['path']
        self.assertEqual(path[0]['uiChange'], 'observation unavailable')
        self.assertIsNone(path[0]['observation'])
        self.assertEqual(path[0]['error'], 'Observation failed')

    def test_independent_change_has_its_own_event_between_commands(self):
        self.start([dict(action='tap')] * 2)
        self.perform('B')
        self.feedback.observe(observation('C'), [])
        self.perform('D')
        self.assertEqual([row['kind'] for row in self.feedback.pending()[0]['path']],
            ['command', 'observation', 'command'])

    def test_failure_feedback_contains_all_cancelled_commands_in_order(self):
        self.start([dict(action='tap')] * 3)
        self.perform('A', error='Target unavailable')
        self.queue.cancel_pending('Target unavailable')
        self.feedback.sync(self.queue.records)
        path = self.feedback.pending()[0]['path']
        self.assertEqual([row['status'] for row in path], ['failed', 'cancelled', 'cancelled'])
        self.assertEqual([row['commandId'] for row in path], [0, 1, 2])
        self.assertIsNone(path[-1]['observation'])

    def test_supplied_feedback_is_not_repeated_as_new_but_remains_retrievable(self):
        self.start([dict(action='tap')])
        self.perform('B')
        self.feedback.delivered()
        self.assertEqual(self.feedback.pending(), [])
        self.assertEqual(len(self.feedback.collection()[0]['path']), 1)

    def test_stopping_keeps_undelivered_results_with_an_explicit_delivery_status(self):
        self.start([dict(action='tap')])
        self.perform('B')
        self.feedback.close()
        self.assertEqual(self.feedback.collection()[0]['delivery'], 'not supplied; scenario ended')
        self.assertEqual(len(self.feedback.collection()[0]['path']), 1)

    def test_feedback_target_excludes_typed_secret_text(self):
        self.start([dict(action='credential', ref='@password', text='never-copy-this', credential='account', field='password')])
        self.perform('B')
        self.assertNotIn('never-copy-this', json.dumps(self.feedback.pending()))

    def test_redaction_preserves_ids_and_scrubs_errors_at_every_path_step(self):
        self.start([dict(action='tap', ref='@e1')])
        self.perform('B', error='synthetic-password')
        redactor = Redactor(dict(credentials=dict(account=dict(password='synthetic-password'))))
        saved = redactor.records.batch_feedback(self.feedback.saved())
        path = saved['batches'][0]['path'][0]
        self.assertEqual(path['commandId'], 0)
        self.assertEqual(path['observation'], 'B')
        self.assertNotIn('synthetic-password', json.dumps(saved))


class AnrWarningTests(unittest.TestCase):
    def test_system_wait_identifier_reports_anr_without_language_matching(self):
        self.assertTrue(android_anr(dict(platform='android'),
            [dict(identifier='android:id/aerr_wait', text='Warten')]))

    def test_app_owned_warning_text_does_not_manufacture_a_system_anr(self):
        self.assertFalse(android_anr(dict(platform='android'),
            [dict(identifier='example:id/help', text="Application isn't responding")]))

    def test_crash_close_button_alone_is_not_an_anr(self):
        self.assertFalse(android_anr(dict(platform='android'), [dict(identifier='android:id/aerr_close')]))

    def test_other_platforms_do_not_produce_android_warnings(self):
        self.assertFalse(android_anr(dict(platform='ios'), [dict(identifier='android:id/aerr_wait')]))

    def test_intermediate_observation_ids_resolve_to_full_masked_ui_records(self):
        recorder = ObservationRecorder(dict(platform='android', id='fixture'), 'Debug')
        session = SimpleNamespace(result={}, elements=[dict(identifier='screen-B')], image=b'masked',
            planner=TestPlanner(), feedback=BatchFeedback())
        recorder.record(session, {}, 2, action_result=True)
        observed = next(iter(session.feedback.observations.values()))
        self.assertIn(observed['uiObservation'], session.planner.memory.map.observations)

    def test_warning_has_timestamp_device_step_and_one_log_event_per_episode(self):
        with tempfile.TemporaryDirectory() as folder:
            output = io.StringIO()
            activity = ActivityLog(folder, Redactor({}), output=output)
            recorder = ObservationRecorder(dict(platform='android', id='fixture'), 'Debug', activity)
            session = SimpleNamespace(result={}, elements=[dict(identifier='android:id/aerr_wait')],
                image=b'masked', planner=TestPlanner(), feedback=BatchFeedback())
            recorder.record(session, {}, 2)
            recorder.record(session, {}, 3)
            warning = session.result['warnings'][0]
            self.assertEqual(warning['step'], 2)
            self.assertEqual(warning['device'], 'fixture')
            self.assertTrue(warning['timestamp'].endswith('+00:00'))
            self.assertEqual(len(Path(folder, 'activity.jsonl').read_text().splitlines()), 1)
            self.assertIn('warning', output.getvalue())
            session.elements = []
            recorder.record(session, {}, 4)
            session.elements = [dict(identifier='android:id/aerr_wait')]
            recorder.record(session, {}, 5)
            self.assertEqual(len(session.result['warnings']), 2)
            self.assertNotIn('verdict', session.result)
            self.assertNotIn('crashes', session.result)


class EvidenceReuseTests(unittest.TestCase):
    def test_identical_evidence_reuses_files_without_dropping_steps(self):
        with tempfile.TemporaryDirectory() as folder:
            evidence = ScenarioEvidence(folder, folder)
            first = evidence.save_step(1, [], b'masked')
            second = evidence.save_step(2, [], b'masked')
            self.assertEqual(first, second)
            self.assertEqual(len(list(Path(folder).glob('*.png'))), 1)
            self.assertEqual(len(list(Path(folder).glob('*.json'))), 1)

    def test_changed_ui_with_unchanged_pixels_does_not_overwrite_earlier_ui(self):
        with tempfile.TemporaryDirectory() as folder:
            evidence = ScenarioEvidence(folder, folder)
            first = evidence.save_step('observation-1', [dict(text='A')], b'masked')
            second = evidence.save_step('observation-1', [dict(text='B')], b'masked')
            self.assertNotEqual(first['ui'], second['ui'])
            self.assertEqual(json.loads(Path(folder, first['ui']).read_text()), [dict(text='A')])

    def test_reuse_rejects_a_modified_registered_image(self):
        with tempfile.TemporaryDirectory() as folder:
            evidence = ScenarioEvidence(folder, folder)
            first = evidence.save_step(1, [], b'masked')
            Path(folder, first['screenshot']).write_bytes(b'altered')
            with self.assertRaises(InfrastructureError):
                evidence.save_step(2, [], b'masked')
