"""Conversation tests use synthetic messages and no provider calls."""

import json
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / 'runtime'))
from chat.conversation import Conversation


class ConversationTests(unittest.TestCase):
    def setUp(self):
        self.chat = Conversation()
        self.stable = ('instructions',)
        self.paths = (('memory', 'records'),)

    def send(self, state):
        prepared = self.chat.prepare(state, self.stable, self.paths)
        message = dict(role='user', content=[
            dict(type='input_text', text=json.dumps(prepared)),
            dict(type='input_image', image_url='data:image/png;base64,fixture'),
        ])
        self.chat.record(message, 'response')
        return prepared

    def test_repeated_copies_are_omitted_and_chat_order_is_retained(self):
        state = dict(instructions='Run test', memory=dict(records=[dict(id=1, value='A')]))
        first = self.send(state)
        second = self.send(state)

        self.assertEqual(first, state)
        self.assertNotIn('instructions', second)
        self.assertEqual(second['memory']['records'], [])
        self.assertEqual([row['role'] for row in self.chat.messages],
                         ['user', 'assistant', 'user', 'assistant'])
        self.assertEqual(self.chat.messages[0]['content'][1]['text'],
                         '[Screenshot omitted from conversation history.]')
        self.assertEqual(state['memory']['records'], [dict(id=1, value='A')])

    def test_new_changed_and_reverted_records_are_sent(self):
        def state(value):
            return dict(instructions='Run test', memory=dict(records=[dict(id=1, value=value)]))

        self.send(state('A'))
        self.assertEqual(self.send(state('B'))['memory']['records'], [dict(id=1, value='B')])
        self.assertEqual(self.send(state('A'))['memory']['records'], [dict(id=1, value='A')])

    def test_new_or_changed_stable_information_is_sent(self):
        self.send(dict(instructions='First', memory=dict(records=[])))
        self.assertEqual(self.send(dict(instructions='Changed', memory=dict(records=[])))['instructions'],
                         'Changed')

    def test_record_returns_after_absence_and_explicit_recall(self):
        item = dict(id=1)
        self.send(dict(instructions='Run', memory=dict(records=[item])))
        self.send(dict(instructions='Run', memory=dict(records=[])))
        self.assertEqual(self.send(dict(instructions='Run', memory=dict(records=[item])))['memory']['records'], [item])
        self.chat.request_records()
        self.assertEqual(self.send(dict(instructions='Run', memory=dict(records=[item])))['memory']['records'], [item])
        self.assertEqual(self.send(dict(instructions='Run', memory=dict(records=[item])))['memory']['records'], [])

    def test_failed_exchange_does_not_mark_data_as_sent(self):
        state = dict(instructions='Run', memory=dict(records=[dict(id=1)]))
        self.chat.prepare(state, self.stable, self.paths)
        retried = self.chat.prepare(state, self.stable, self.paths)

        self.assertEqual(retried, state)

    def test_repeated_large_records_are_not_copied_into_each_turn(self):
        records = [dict(id=index, text='evidence-' + str(index) + 'x' * 300)
                   for index in range(100)]
        state = dict(instructions='unique-instructions:' + 'Task ' * 1000, memory=dict(records=records))

        self.send(state)
        for _ in range(19):
            self.send(state)

        stored = json.dumps(self.chat.messages)
        self.assertEqual(stored.count('evidence-99'), 1)
        self.assertEqual(stored.count('unique-instructions:'), 1)
        self.assertLess(len(stored), 80000)

    def test_history_is_complete_while_only_current_image_is_sent(self):
        self.send(dict(instructions='Run', memory=dict(records=[])))
        current = dict(role='user', content=[
            dict(type='input_text', text='next'),
            dict(type='input_image', image_url='data:image/png;base64,current'),
        ])
        messages = self.chat.build_messages(dict(role='system', content='system'), current)

        self.assertEqual([row['role'] for row in messages],
                         ['system', 'user', 'assistant', 'user'])
        self.assertEqual(messages[2]['content'], 'response')
        images = [part for row in messages if isinstance(row['content'], list)
                  for part in row['content'] if part['type'] == 'input_image']
        self.assertEqual(images, [current['content'][1]])


if __name__ == '__main__':
    unittest.main()
