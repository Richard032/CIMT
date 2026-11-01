"""AI replies are data. Only explicit readable commands cause device requests."""

import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'runtime'))
from command_reply import read_reply
from test_planning.context_memory import ContextMemory
from test_planning.loop_recovery import LoopRecovery


def reply(text):
    return dict(status='completed', output=[dict(type='message',
        content=[dict(type='output_text', text=text)])])


class CommandReplyTests(unittest.TestCase):
    def test_minimal_device_command_needs_no_plan_or_report_fields(self):
        result = read_reply(reply('{"action":"tap","ref":"@earlier"}'))
        self.assertEqual(result['action'], 'tap')
        self.assertEqual(result['ref'], '@earlier')
        self.assertEqual(result['planUpdates'], [])

    def test_prose_is_a_note_without_a_selected_replacement_command(self):
        result = read_reply(reply('I want to reconsider my plan.'))
        self.assertEqual(result['action'], 'note')
        self.assertIn('Unreadable reply text', result['resourceFeedback'])
        self.assertEqual(result['modelResponse'], 'I want to reconsider my plan.')

    def test_multiple_objects_are_decoded_in_received_order(self):
        text = '{"action":"tap","ref":"@one"}{"action":"restart"}'
        result = read_reply(reply(text))
        self.assertEqual(result['action'], 'tap')
        self.assertEqual([row['action'] for row in result['queuedCommands']], ['restart'])
        self.assertEqual(result['modelResponse'], text)

    def test_array_commands_keep_their_order(self):
        result = read_reply(reply('[{"action":"tap","ref":"@one"},{"action":"back"},{"action":"done"}]'))
        self.assertEqual([result['action']] + [row['action'] for row in result['queuedCommands']], ['tap', 'back', 'done'])

    def test_unreadable_suffix_does_not_discard_decoded_prefix(self):
        result = read_reply(reply('{"action":"tap","ref":"@one"} unreadable trailing text'))
        self.assertEqual(result['action'], 'tap')
        self.assertEqual(result['queuedCommands'][0]['action'], 'note')
        self.assertIn('Unreadable', result['queuedCommands'][0]['resourceFeedback'])

    def test_prose_containing_json_does_not_create_guessed_actions(self):
        result = read_reply(reply('Example only: {"action":"tap","ref":"@one"}'))
        self.assertEqual(result['action'], 'note')
        self.assertNotIn('queuedCommands', result)

    def test_unknown_fields_are_preserved_in_the_original_reply(self):
        text = json.dumps(dict(action='wait', myPlan=dict(next='Settings')))
        result = read_reply(reply(text))
        self.assertEqual(result['action'], 'wait')
        self.assertEqual(json.loads(result['modelResponse'])['myPlan']['next'], 'Settings')

    def test_sparse_metadata_cannot_block_an_explicit_command(self):
        result = read_reply(reply(json.dumps(dict(action='tap', ref='@one',
            planUpdates=[dict(subject='My plan')], pathDecisions=[dict(id='login-screen')]))))
        self.assertEqual(result['action'], 'tap')
        self.assertEqual(result['pathDecisions'][0]['id'], 'login-screen')

    def test_unavailable_context_addresses_are_resource_information(self):
        memory = ContextMemory()
        memory.accept(dict(summary='Keep my plan', includeAll=['unknown'],
            records=[dict(collection='actions', id='not-present')]))
        selected = memory.project(dict(actions=[]))
        self.assertEqual(selected['actions'], [])
        self.assertEqual(len(memory.unavailable), 2)
        self.assertEqual(memory.saved()['summary'], 'Keep my plan')

    def test_unstructured_recovery_is_preserved_without_a_format_gate(self):
        text = json.dumps(dict(action='wait', recovery=dict(id='AI-label', reason=dict(note='Think again'))))
        result = read_reply(reply(text))
        self.assertEqual(result['action'], 'wait')
        self.assertEqual(result['modelResponse'], text)

    def test_note_does_not_claim_that_ai_has_chosen_a_recovery_command(self):
        recovery = LoopRecovery()
        recovery.request('repetition', 'Repeated path', 3)
        recovery.acknowledge(read_reply(reply('I need to consider earlier evidence.')))
        self.assertEqual(recovery.pending['status'], 'waiting')

    def test_command_can_continue_recovery_without_structured_acknowledgement(self):
        recovery = LoopRecovery()
        recovery.request('repetition', 'Repeated path', 3)
        recovery.acknowledge(read_reply(reply('{"action":"tap","ref":"@another"}')))
        self.assertIsNone(recovery.pending)
        self.assertEqual(recovery.records[0]['decision'], 'AI action')
