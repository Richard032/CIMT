"""Instruction preparation uses synthetic UI information, not real devices or AI."""

import ast
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'runtime'))
from ai_instructions.instructions import ActionPromptBuilder


def state(elements):
    body = ActionPromptBuilder('fixture').build('Explore the supplied goal', 'App stays running',
        'Use the test setup', elements, b'already-masked', [], ['test-account'], {})
    return json.loads(body['input'][1]['content'][0]['text'])


class InstructionTests(unittest.TestCase):
    def test_controls_keep_enabled_state_for_the_ai_to_interpret(self):
        disabled = dict(ref='@disabled', type='Button', label='Save', enabled=False)
        inputs = state([disabled])
        self.assertEqual(inputs['humanInterface'], [dict(disabled, inputKind='tap')])
        self.assertEqual(inputs['elements'], [disabled])

    def test_static_text_is_evidence_without_becoming_a_control(self):
        text = dict(ref='@caption', type='Text', text='Current selection')
        inputs = state([text])
        self.assertEqual(inputs['elements'], [text])
        self.assertEqual(inputs['humanInterface'], [])

    def test_generic_control_uses_adapter_clickable_metadata(self):
        control = dict(ref='@web-control', type='android.view.View', clickable=True)
        self.assertEqual(state([control])['humanInterface'][0]['inputKind'], 'tap')

    def test_sources_setup_and_credential_aliases_remain_available(self):
        inputs = state([])
        self.assertEqual(inputs['instructions'], 'Explore the supplied goal')
        self.assertEqual(inputs['requirements'], 'App stays running')
        self.assertEqual(inputs['setup'], 'Use the test setup')
        self.assertEqual(inputs['credentialAliases'], ['test-account'])

    def test_credential_resources_show_alias_field_and_target_together(self):
        resources = state([])['commandResources']
        example = resources['credentialExample']
        self.assertEqual(example['action'], 'credential')
        self.assertTrue(example['credential'])
        self.assertEqual(example['field'], 'username')
        self.assertTrue(example['ref'])
        self.assertIn('Credential entry', resources['arguments']['ref']['description'])

    def test_prompt_explains_credential_replacement_and_hidden_value_confirmation(self):
        body = ActionPromptBuilder('fixture').build('Explore', '', '', [], b'masked', [], [], {})
        prompt = body['input'][0]['content']
        self.assertIn('repeating it replaces the value again instead of appending', prompt)
        self.assertIn('not that authentication succeeded', prompt)
        self.assertIn('do not re-enter credentials solely because their values are hidden', prompt)
        self.assertIn('text types into the focused field and may append', prompt)

    def test_normal_action_example_includes_an_explicit_ai_context_selection(self):
        example = state([])['commandResources']['contextExample']
        self.assertEqual(example['action'], 'tap')
        self.assertTrue(example['ref'])
        self.assertEqual(example['context']['includeAll'], [])
        self.assertEqual(example['context']['records'], [])
        self.assertTrue(example['context']['summary'])
        body = ActionPromptBuilder('fixture').build('Explore', '', '', [], b'masked', [], [], {})
        self.assertIn('Alongside your first normal action', body['input'][0]['content'])
        self.assertIn('null keeps bootstrap history', body['input'][0]['content'])

    def test_prompt_explains_whole_collection_and_unchanged_selection(self):
        body = ActionPromptBuilder('fixture').build('Explore', '', '', [], b'masked', [], [], {})
        prompt = body['input'][0]['content']
        self.assertIn('ENTIRE named collections', prompt)
        self.assertIn('keeps the existing selection', prompt)
        self.assertIn('explicit target', prompt)

    def test_prompt_explains_whole_reply_syntax_feedback(self):
        body = ActionPromptBuilder('fixture').build('Explore', '', '', [], b'masked', [], [], {})
        prompt = body['input'][0]['content']
        self.assertIn('Prefer an array for multiple commands', prompt)
        self.assertIn('Commas between commands require enclosing array brackets', prompt)
        self.assertIn('CIMT executes none of that reply', prompt)
        self.assertIn('reason and expected format', prompt)

    def test_swipe_resources_expose_target_and_distance_together(self):
        resources = state([])['commandResources']
        self.assertEqual(resources['swipeExample'], dict(action='swipe', ref='<current target ref>',
                                                       direction='up', distance=35, durationMs=1000))
        self.assertEqual(resources['arguments']['distance']['minimum'], 1)
        self.assertIn('null', resources['arguments']['distance']['type'])

    def test_prompt_exposes_slow_drag_timing_without_a_host_selected_default(self):
        resources = state([])['commandResources']
        self.assertEqual(resources['swipeExample']['durationMs'], 1000)
        self.assertIn('null', resources['arguments']['durationMs']['type'])
        self.assertIn('explicit target and distance', resources['arguments']['durationMs']['description'])
        body = ActionPromptBuilder('fixture').build('Explore', '', '', [], b'masked', [], [], {})
        self.assertIn('short swipe at default timing can still fling', body['input'][0]['content'])
        self.assertIn('inspect the actual result and adjust', body['input'][0]['content'])

    def test_swipe_resources_explain_finger_direction_and_distance_units(self):
        arguments = state([])['commandResources']['arguments']
        for meaning in ['up decreases y', 'down increases y', 'left decreases x', 'right increases x']:
            self.assertIn(meaning, arguments['direction']['description'])
        self.assertIn('not a number of picker rows', arguments['distance']['description'])

    def test_picker_guidance_survives_context_deferral_and_recovery(self):
        wheel = dict(ref='@wheel', type='PickerWheel', value='Tier C')
        body = ActionPromptBuilder('fixture').build('Select the requested tier', '', '', [wheel],
            b'masked', [dict(observation='x' * 70000)], [], {},
            exploration_memory=dict(recoveryRequest=dict(id=1, kind='repetition')))
        inputs = json.loads(body['input'][1]['content'][0]['text'])
        self.assertIn('contextSelectionRequired', inputs)
        self.assertEqual(inputs['elements'], [wheel])
        self.assertEqual(inputs['explorationMemory']['recoveryRequest']['id'], 1)
        prompt = body['input'][0]['content']
        self.assertIn('move the finger down to bring an item above the selection band', prompt)
        self.assertIn('up for an item below', prompt)
        self.assertIn('Use one gesture, then inspect the resulting wheel value and image', prompt)
        self.assertIn('If you overshoot, reduce distance and reverse direction as needed', prompt)
        self.assertIn('verify the displayed field value after the picker closes', prompt)
        self.assertNotIn('OEM', prompt)

    def test_shared_guide_stays_available_when_optional_history_is_deferred(self):
        knowledge = dict(enabled=True, appId='org.example.app', platform='ios', status='loaded', guide='Use Settings')
        body = ActionPromptBuilder('fixture').build('Current issue scope', '', '', [], b'masked',
            [dict(observation='x' * 70000)], [], {}, exploration_memory=dict(applicationKnowledge=knowledge))
        inputs = json.loads(body['input'][1]['content'][0]['text'])
        self.assertIn('contextSelectionRequired', inputs)
        self.assertEqual(inputs['applicationKnowledge'], knowledge)
        self.assertEqual(inputs['instructions'], 'Current issue scope')
        prompt = body['input'][0]['content']
        self.assertIn('Current testing instructions', prompt)
        self.assertIn('learnedAppKnowledge', prompt)
        self.assertIn('Git PR', prompt)

    def test_instruction_layer_does_not_import_reply_or_execution_services(self):
        forbidden = {'command_reply', 'actions', 'agent', 'openai_transport', 'scenario', 'mcp_client', 'device_adapter'}
        package = Path(__file__).resolve().parents[1] / 'runtime/ai_instructions'
        for path in package.glob('*.py'):
            for node in ast.walk(ast.parse(path.read_text())):
                if isinstance(node, ast.Import):
                    self.assertFalse({item.name.split('.')[0] for item in node.names} & forbidden)
                elif isinstance(node, ast.ImportFrom):
                    self.assertNotIn((node.module or '').split('.')[0], forbidden)
