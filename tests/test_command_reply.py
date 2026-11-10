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
        self.assertIn('Invalid JSON command reply', result['resourceFeedback'])
        self.assertIn('Expected one JSON command object', result['resourceFeedback'])
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

    def test_unreadable_suffix_prevents_partial_execution(self):
        text = '{"action":"tap","ref":"@one"} unreadable trailing text'
        result = read_reply(reply(text))
        self.assertEqual(result['action'], 'note')
        self.assertNotIn('queuedCommands', result)
        self.assertIn('No commands from this reply were executed', result['resourceFeedback'])
        self.assertEqual(result['modelResponse'], text)

    def test_comma_separated_commands_explain_the_missing_array(self):
        text = '{"action":"wait"},{"action":"wait"}'
        result = read_reply(reply(text))
        self.assertEqual(result['action'], 'note')
        self.assertNotIn('queuedCommands', result)
        self.assertIn('Unexpected comma between top-level commands', result['resourceFeedback'])
        self.assertIn('[{"action":"wait"},{"action":"wait"}]', result['resourceFeedback'])
        self.assertEqual(result['modelResponse'], text)

    def test_json_error_reports_its_position_in_the_original_reply(self):
        result = read_reply(reply('  \n{"action":"wait"}\n{broken'))
        self.assertIn('line 3, column 2', result['resourceFeedback'])
        self.assertIn('Expecting property name enclosed in double quotes', result['resourceFeedback'])

    def test_non_object_values_prevent_the_entire_reply_from_executing(self):
        for text in ['42', 'null', '"text"', '[{"action":"wait"},42]',
                     '{"action":"wait"} [false]', '[[{"action":"wait"}]]']:
            with self.subTest(text=text):
                result = read_reply(reply(text))
                self.assertEqual(result['action'], 'note')
                self.assertNotIn('queuedCommands', result)
                self.assertIn('every command must be a JSON object', result['resourceFeedback'])

    def test_empty_replies_explain_the_expected_command_formats(self):
        for text in ['', '  ', '[]']:
            with self.subTest(text=text):
                result = read_reply(reply(text))
                self.assertEqual(result['action'], 'note')
                self.assertIn('No command objects were supplied', result['resourceFeedback'])
                self.assertIn('Expected one JSON command object', result['resourceFeedback'])

    def test_error_feedback_does_not_repeat_untrusted_reply_values(self):
        result = read_reply(reply('{"action":"wait"} synthetic-secret'))
        self.assertNotIn('synthetic-secret', result['resourceFeedback'])

    def test_valid_note_before_commands_does_not_claim_the_whole_reply_was_skipped(self):
        result = read_reply(reply('[{}, {"action":"wait"}]'))
        self.assertEqual(result['action'], 'note')
        self.assertEqual(result['queuedCommands'][0]['action'], 'wait')
        self.assertNotIn('No commands from this reply', result['resourceFeedback'])

    def test_whitespace_between_commands_remains_supported(self):
        result = read_reply(reply(' \n{"action":"wait"} \n {"action":"back"} \n'))
        self.assertEqual([result['action']] + [row['action'] for row in result['queuedCommands']], ['wait', 'back'])

    def test_prose_containing_json_does_not_create_guessed_actions(self):
        result = read_reply(reply('Example only: {"action":"tap","ref":"@one"}'))
        self.assertEqual(result['action'], 'note')
        self.assertNotIn('queuedCommands', result)

    def test_swipe_distance_and_fractional_coordinates_survive_decoding(self):
        result = read_reply(reply('{"action":"swipe","x":12.5,"y":30.25,"direction":"up","distance":40.5}'))
        self.assertEqual((result['x'], result['y'], result['distance']), (12.5, 30.25, 40.5))

    def test_invalid_swipe_distance_is_retained_for_explicit_execution_failure(self):
        result = read_reply(reply('{"action":"swipe","ref":"@wheel","direction":"up","distance":"bad"}'))
        self.assertEqual(result['distance'], 'bad')

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
