"""Queue state is separate from device execution and AI calls."""

from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'runtime'))
from command_queue import CommandQueue
from redaction import Redactor
import json


class CommandQueueTests(unittest.TestCase):
    def test_commands_are_taken_first_in_first_out(self):
        queue = CommandQueue()
        queue.add(dict(action='tap', ref='first', queuedCommands=[dict(action='back'), dict(action='done')]))
        actions = []
        while queue.pending:
            actions.append(queue.take()['action'])
            queue.finish('executed')
        self.assertEqual(actions, ['tap', 'back', 'done'])

    def test_receipt_does_not_mark_commands_executed(self):
        queue = CommandQueue()
        queue.add(dict(action='tap', queuedCommands=[dict(action='back')]))
        self.assertEqual([row['status'] for row in queue.records], ['queued', 'queued'])

    def test_stop_preserves_the_unexecuted_tail(self):
        queue = CommandQueue()
        queue.add(dict(action='tap', queuedCommands=[dict(action='back'), dict(action='done')]))
        queue.take()
        queue.finish('executed', step=1)
        queue.stop('User interrupted')
        self.assertEqual([row['status'] for row in queue.records], ['executed', 'not executed', 'not executed'])
        self.assertFalse(queue.pending)

    def test_an_in_flight_command_is_interrupted_when_scenario_stops(self):
        queue = CommandQueue()
        queue.add(dict(action='tap'))
        queue.take()
        queue.stop('Scenario stopped')
        self.assertEqual(queue.records[0]['status'], 'interrupted')

    def test_batches_keep_distinct_identity_and_source_order(self):
        queue = CommandQueue()
        queue.add(dict(action='wait'))
        queue.take()
        queue.finish('executed')
        queue.add(dict(action='tap'))
        second = queue.take()
        self.assertEqual((second['commandId'], second['batchId'], second['batchPosition']), (1, 1, 0))

    def test_queue_does_not_change_the_decoded_reply(self):
        reply = dict(action='wait', queuedCommands=[dict(action='done')])
        queue = CommandQueue()
        queue.add(reply)
        queue.take()
        self.assertEqual(reply, dict(action='wait', queuedCommands=[dict(action='done')]))

    def test_saved_rows_cannot_mutate_the_live_queue(self):
        queue = CommandQueue()
        queue.add(dict(action='wait'))
        saved = queue.saved()
        saved['commands'][0]['status'] = 'executed'
        self.assertEqual(queue.records[0]['status'], 'queued')


class QueuePrivacyTests(unittest.TestCase):
    def test_queue_redaction_keeps_control_metadata_and_hides_reply_secrets(self):
        redactor = Redactor({'credentials': {'test': {'password': 'synthetic-secret'}}})
        queue = CommandQueue()
        queue.add(dict(action='tap', ref='@e1', modelResponse='synthetic-secret'))
        queue.stop('synthetic-secret')
        saved = redactor.records.command_queue(queue.saved())
        row = saved['commands'][0]
        self.assertEqual(row['status'], 'not executed')
        self.assertEqual(row['response']['ref'], '@e1')
        self.assertEqual(row['id'], 0)
        self.assertNotIn('synthetic-secret', json.dumps(saved))
