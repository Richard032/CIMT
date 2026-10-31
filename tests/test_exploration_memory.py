"""Scenario memory tests use only masked synthetic UI data."""

import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / 'runtime'))
from exploration_memory import ExplorationMemory, view_identity
from errors import NoProgressAction


BUTTON = {'ref': '@e1', 'type': 'Button', 'identifier': 'Settings', 'label': 'Settings'}
TAP = {'action': 'tap', 'ref': '@e1'}


class ExplorationMemoryTests(unittest.TestCase):
    def setUp(self):
        self.memory = ExplorationMemory()
        self.screen = [BUTTON]

    def record(self, count=1):
        for _ in range(count):
            self.memory.record(self.screen, self.screen, TAP, {})

    def test_ref_label_and_order_changes_do_not_forget_identified_controls(self):
        self.record()
        refreshed = [dict(BUTTON, ref='@e99', label='Einstellungen')]
        self.assertEqual(view_identity(self.screen), view_identity(refreshed))
        self.assertEqual(self.memory.snapshot(refreshed)['currentControls'][0]['attempts'], 1)
        self.assertEqual(self.memory.snapshot(refreshed)['currentControls'][0]['ref'], '@e99')

    def test_another_view_keeps_separate_control_memory(self):
        self.record()
        other = self.screen + [dict(BUTTON, identifier='Save', ref='@e2')]
        self.assertEqual(self.memory.snapshot(other)['currentControls'][0]['attempts'], 0)

    def test_outcome_describes_observed_unchanged_ui(self):
        entry = {}
        self.memory.record(self.screen, self.screen, TAP, entry)
        self.assertEqual(entry['observedOutcome'], 'No observed UI change after the action')
        self.assertEqual(entry['controlLabel'], 'Settings')

    def test_new_state_records_a_changed_outcome(self):
        entry = {}
        self.memory.record(self.screen, [dict(BUTTON, identifier='Save')], TAP, entry)
        self.assertEqual(entry['observedOutcome'], 'Observed UI changed')

    def test_three_unchanged_attempts_reject_another_tap(self):
        self.record(3)
        with self.assertRaises(NoProgressAction):
            self.memory.validate(self.screen, TAP, '')

    def test_explicit_repeat_instruction_and_reason_allow_repeat(self):
        self.record(3)
        self.memory.validate(self.screen, dict(TAP, repeatInstruction='Tap Settings five times',
            repeatReason='Fourth tap of the requested five'), 'Tap Settings five times')

    def test_invented_repeat_quote_cannot_disable_guard(self):
        self.record(3)
        with self.assertRaises(NoProgressAction):
            self.memory.validate(self.screen, dict(TAP, repeatInstruction='Tap five times',
                repeatReason='Reproduce'), 'Explore buttons')

    def test_quote_without_reason_cannot_disable_guard(self):
        self.record(3)
        with self.assertRaises(NoProgressAction):
            self.memory.validate(self.screen, dict(TAP, repeatInstruction='Repeat', repeatReason=''), 'Repeat')

    def test_more_than_24_other_paths_do_not_erase_first_control(self):
        self.record()
        for number in range(30):
            other = [dict(BUTTON, identifier='Button' + str(number))]
            self.memory.record(other, other, TAP, {})
        self.assertEqual(self.memory.snapshot(self.screen)['currentControls'][0]['attempts'], 1)
        self.assertEqual(len(self.memory.saved()['paths']), 31)

    def test_repeated_navigation_cycle_is_detected_without_new_paths(self):
        other = [dict(BUTTON, identifier='Back')]
        for _ in range(6):
            self.memory.record(self.screen, other, TAP, {})
            self.memory.record(other, self.screen, TAP, {})
        with self.assertRaises(NoProgressAction):
            self.memory.validate(self.screen, TAP, '')

    def test_crash_retry_does_not_count_as_unchanged_ui(self):
        self.memory.record(self.screen, self.screen, TAP, {'crash': 'suspected crash'})
        self.assertEqual(self.memory.snapshot(self.screen)['currentControls'][0]['unchangedAttempts'], 0)

    def test_failed_capture_does_not_claim_an_observed_unchanged_result(self):
        entry = {'evidenceError': 'Mask unavailable'}
        self.memory.record(self.screen, self.screen, TAP, entry)
        self.assertEqual(entry['observedOutcome'], 'Mask unavailable')
        self.assertEqual(self.memory.snapshot(self.screen)['currentControls'][0]['unchangedAttempts'], 0)

    def test_interrupted_observation_reports_the_stop_instead_of_unchanged_ui(self):
        entry = {'stoppingReason': 'User interrupted execution; partial observations were retained'}
        self.memory.record(self.screen, self.screen, TAP, entry)
        self.assertEqual(entry['observedOutcome'], entry['stoppingReason'])
        self.assertEqual(self.memory.saved()['transitions'][-1]['outcome'], entry['stoppingReason'])
        self.assertEqual(self.memory.snapshot(self.screen)['currentControls'][0]['unchangedAttempts'], 0)

    def test_interruption_does_not_replace_a_recorded_crash_outcome(self):
        entry = {'crash': 'confirmed crash report', 'stoppingReason': 'User interrupted execution'}
        self.memory.record(self.screen, self.screen, TAP, entry)
        self.assertEqual(entry['observedOutcome'], 'confirmed crash report')


    def test_untried_path_is_retained_after_leaving_its_view(self):
        self.memory.observe(self.screen + [dict(BUTTON, identifier='Other', ref='@e2')])
        self.memory.observe([dict(BUTTON, identifier='Back')])
        pending = self.memory.snapshot([dict(BUTTON, identifier='Back')])['pendingPaths']
        self.assertTrue(any(row['label'] == 'Settings' and row['attempts'] == 0 for row in pending))

    def test_element_order_does_not_create_a_new_view(self):
        other = dict(BUTTON, identifier='Other', ref='@e2')
        self.assertEqual(view_identity([BUTTON, other]), view_identity([other, BUTTON]))


    def test_discovering_a_new_path_reopens_a_previously_repeated_return_route(self):
        other = [dict(BUTTON, identifier='Back')]
        for _ in range(6):
            self.memory.record(self.screen, other, TAP, {})
            self.memory.record(other, self.screen, TAP, {})
        self.memory.observe([dict(BUTTON, identifier='New route')])
        self.memory.validate(self.screen, TAP, '')


if __name__ == '__main__':
    unittest.main()
