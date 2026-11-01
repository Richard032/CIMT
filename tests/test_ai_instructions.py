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

    def test_instruction_layer_does_not_import_reply_or_execution_services(self):
        forbidden = {'command_reply', 'actions', 'agent', 'openai_transport', 'scenario', 'mcp_client'}
        package = Path(__file__).resolve().parents[1] / 'runtime/ai_instructions'
        for path in package.glob('*.py'):
            for node in ast.walk(ast.parse(path.read_text())):
                if isinstance(node, ast.Import):
                    self.assertFalse({item.name.split('.')[0] for item in node.names} & forbidden)
                elif isinstance(node, ast.ImportFrom):
                    self.assertNotIn((node.module or '').split('.')[0], forbidden)
