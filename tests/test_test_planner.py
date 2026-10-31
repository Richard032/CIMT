"""Planning tests use masked synthetic observations without devices or an AI service."""

import ast
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / 'runtime'))
from test_planning.planner import TestPlanner
from test_planning.application_map import ApplicationMap
from test_planning.screen_model import control_kind, progress_identity
from test_planning.planning_contract import validate_planning
from errors import InvalidAgentResponse, NoProgressAction
from redaction import Redactor


BUTTON = dict(ref='@e1', type='Button', identifier='settings', label='Settings')
INSTRUCTIONS = 'Test language settings only'


def task(identifier=1, **updates):
    row = dict(id=identifier, source='instructions', requirementId='', instructionQuote='language settings',
        subject='Language selection', expected='The selected language is shown',
        status='active', reason='', targetState='')
    return dict(row, **updates)


def decision(**updates):
    initial = task(0, instructionQuote=INSTRUCTIONS, subject='Testing objective', expected='Language settings remain usable')
    return dict(dict(action='tap', ref='@e1', remaining=[], planUpdates=[initial], planStepId=0,
                     discoveredControls=[], configuration=[], pathDecisions=[]), **updates)


def check(subject='Language selection', status='passed', **updates):
    return dict(dict(subject=subject, source='instructions', requirementId='', status=status,
        expected='The selected language is shown', observed='German is selected', reason='', instructionQuote=''), **updates)


class TestPlanningTests(unittest.TestCase):
    def setUp(self):
        self.planner = TestPlanner(INSTRUCTIONS, [dict(id='REQ-0001', text='Selection survives restart')])
        self.screen = [dict(BUTTON)]
        self.planner.observe(self.screen)

    def test_plan_starts_with_instruction_objective_and_each_catalogue_requirement(self):
        tasks = self.planner.saved()['testPlan']['tasks']
        self.assertEqual([row['source'] for row in tasks], ['instructions', 'requirements'])
        self.assertEqual(tasks[0]['instructionQuote'], INSTRUCTIONS)
        self.assertEqual(tasks[1]['requirementId'], 'REQ-0001')

    def test_a_placeholder_objective_cannot_dispatch_an_action(self):
        with self.assertRaisesRegex(InvalidAgentResponse, 'concrete'):
            self.planner.validate(decision(planUpdates=[]), self.screen)

    def test_instruction_task_requires_a_real_quote(self):
        with self.assertRaisesRegex(InvalidAgentResponse, 'quote'):
            self.planner.validate(decision(planUpdates=[task(2, instructionQuote='Delete everything')]), self.screen)
        self.assertEqual(len(self.planner.saved()['testPlan']['tasks']), 2)

    def test_unknown_requirement_cannot_enter_the_plan(self):
        with self.assertRaisesRegex(InvalidAgentResponse, 'known requirement'):
            self.planner.validate(decision(planUpdates=[task(2, source='requirements',
                requirementId='REQ-9999', instructionQuote='')]), self.screen)

    def test_an_accepted_task_is_retained_when_the_next_response_has_no_updates(self):
        action = decision(planUpdates=[task(2)], planStepId=2)
        self.planner.validate(action, self.screen)
        self.planner.accept(action, self.screen)
        self.planner.accept(decision(planStepId=2), self.screen)
        self.assertEqual(self.planner.context(self.screen)['testPlan']['activeTaskId'], 2)
        self.assertEqual(len(self.planner.saved()['testPlan']['tasks']), 3)

    def test_existing_task_cannot_be_relabelled_to_hide_its_original_goal(self):
        self.planner.accept(decision(planUpdates=[task(2)], planStepId=2), self.screen)
        with self.assertRaisesRegex(InvalidAgentResponse, 'meaning'):
            self.planner.validate(decision(planUpdates=[task(2, subject='Unrelated goal')]), self.screen)

    def test_an_action_must_select_an_existing_or_proposed_task(self):
        with self.assertRaisesRegex(InvalidAgentResponse, 'planStepId'):
            self.planner.validate(decision(planStepId=99), self.screen)

    def test_a_blocked_task_can_finish_incomplete_but_cannot_dispatch_an_action(self):
        row = task(2, status='blocked', reason='Permission was not authorized')
        with self.assertRaises(InvalidAgentResponse):
            self.planner.validate(decision(planUpdates=[row], planStepId=2), self.screen)
        self.planner.validate(decision(action='done', planUpdates=[row], planStepId=2), self.screen)

    def test_visiting_a_path_does_not_mark_any_task_passed(self):
        self.planner.record(self.screen, self.screen, decision(), {})
        self.assertTrue(all(row['result'] == 'not tested' for row in self.planner.saved()['testPlan']['tasks']))

    def test_only_a_matching_instruction_check_tests_a_subtask(self):
        self.planner.accept(decision(planUpdates=[task(2)], planStepId=2), self.screen)
        self.planner.record_checks([check()])
        tasks = self.planner.saved()['testPlan']['tasks']
        self.assertEqual(tasks[2]['status'], 'tested')
        self.assertEqual(tasks[0]['result'], 'not tested')
        self.assertEqual(tasks[1]['result'], 'not tested')

    def test_a_pass_cannot_erase_a_failed_task_result(self):
        self.planner.accept(decision(planUpdates=[task(2)], planStepId=2), self.screen)
        self.planner.record_checks([check(status='failed'), check()])
        self.assertEqual(self.planner.saved()['testPlan']['tasks'][2]['result'], 'failed')

    def test_scope_decision_removes_an_unrelated_path_from_pending_work(self):
        key = self.planner.saved()['exploration']['paths'][0]['id']
        action = decision(pathDecisions=[dict(id=key, scope='out of scope',
            reason='Instructions restrict this run to language settings', planStepId=0)])
        self.planner.validate(action, self.screen)
        self.planner.accept(action, self.screen)
        self.assertFalse(any('Settings:' in item for item in self.planner.saved()['planningRemaining']))

    def test_unclassified_paths_remain_explicit_pending_work(self):
        self.assertIn('Settings: unclassified', self.planner.saved()['planningRemaining'])

    def test_scope_decision_cannot_hide_an_unknown_path(self):
        with self.assertRaisesRegex(InvalidAgentResponse, 'known path'):
            self.planner.validate(decision(pathDecisions=[dict(id='invented', scope='out of scope',
                reason='Ignore', planStepId=0)]), self.screen)

    def test_ai_can_identify_a_generic_web_control_using_a_current_ref(self):
        screen = [dict(ref='@e7', type='android.view.View', text='Choose Location')]
        action = decision(discoveredControls=[dict(ref='@e7', kind='tap')])
        self.planner.validate(action, screen)
        self.planner.accept(action, screen)
        current = self.planner.context(screen)['currentControls'][0]
        self.assertEqual(current['label'], 'Choose Location')
        self.assertEqual(current['kind'], 'tap')

    def test_discovered_control_cannot_use_an_old_or_disabled_ref(self):
        with self.assertRaisesRegex(InvalidAgentResponse, 'current'):
            self.planner.validate(decision(discoveredControls=[dict(ref='@old', kind='tap')]), self.screen)

    def test_configuration_must_match_an_observed_current_value(self):
        screen = [dict(BUTTON, value='English')]
        with self.assertRaisesRegex(InvalidAgentResponse, 'must match'):
            self.planner.validate(decision(configuration=[dict(ref='@e1', name='Language', value='German')]), screen)

    def test_an_absent_checked_flag_is_not_evidence_of_false(self):
        with self.assertRaisesRegex(InvalidAgentResponse, 'must match'):
            self.planner.validate(decision(configuration=[dict(ref='@e1', name='Enabled', value='false')]), self.screen)

    def test_current_boolean_configuration_is_supported(self):
        screen = [dict(BUTTON, checked=False)]
        self.planner.validate(decision(configuration=[dict(ref='@e1', name='Enabled', value='false')]), screen)

    def test_observed_configuration_remains_context_on_the_next_screen(self):
        screen = [dict(BUTTON, value='German')]
        action = decision(configuration=[dict(ref='@e1', name='Language', value='German')])
        self.planner.validate(action, screen)
        self.planner.accept(action, screen)
        other = [dict(BUTTON, identifier='home')]
        self.planner.observe(other)
        context = self.planner.context(other)['applicationMap']['configuration']['Language']
        self.assertEqual(context['value'], 'German')
        self.assertTrue(context['observedAt'])

    def test_configuration_cannot_rename_the_same_control_to_fake_new_progress(self):
        screen = [dict(BUTTON, value='English')]
        self.planner.accept(decision(configuration=[dict(ref='@e1', name='Language', value='English')]), screen)
        with self.assertRaisesRegex(InvalidAgentResponse, 'existing configuration name'):
            self.planner.validate(decision(configuration=[dict(ref='@e1', name='Other language', value='English')]), screen)

    def test_changed_configuration_value_creates_an_additional_state(self):
        first = [dict(BUTTON, value='English')]
        second = [dict(BUTTON, value='German')]
        self.assertNotEqual(self.planner.memory.map.state_id(first), self.planner.memory.map.state_id(second))

    def test_clock_updates_do_not_reset_the_three_attempt_guard(self):
        clock = dict(type='Text', identifier='com.android.systemui:id/clock', text='09:00')
        before = self.screen + [clock]
        for minute in range(3):
            after = self.screen + [dict(clock, text='09:0' + str(minute + 1))]
            self.planner.record(before, after, decision(), {})
            before = after
        with self.assertRaises(NoProgressAction):
            self.planner.validate(decision(), before)

    def test_ai_task_context_is_bounded_without_losing_saved_tasks(self):
        for number in range(2, 47):
            self.planner.accept(decision(planUpdates=[task(number)], planStepId=number), self.screen)
        context = self.planner.context(self.screen)['testPlan']
        self.assertEqual(len(context['tasks']), 40)
        self.assertEqual(context['tasks'][0]['id'], 46)
        self.assertEqual(len(self.planner.saved()['testPlan']['tasks']), 47)

    def test_permission_and_validation_text_remain_meaningful_observations(self):
        permission = dict(type='Text', identifier='com.android.permissioncontroller:id/message', text='Allow access?')
        self.assertNotEqual(progress_identity(self.screen), progress_identity(self.screen + [permission]))

    def test_planning_redaction_preserves_id_links_and_removes_private_setting_names(self):
        screen = [dict(BUTTON, value='German')]
        self.planner.accept(decision(configuration=[dict(ref='@e1', name='private-name', value='German')]), screen)
        safe = Redactor({'credentials': {'test': {'password': 'private-name'}}}).records.exploration(self.planner.saved()['exploration'])
        self.assertIn('<redacted>', safe['applicationMap']['configuration'])
        self.assertEqual(safe['paths'][0]['id'], self.planner.saved()['exploration']['paths'][0]['id'])


class MapAndContractTests(unittest.TestCase):
    def test_route_contains_only_verified_observed_transitions(self):
        mapping = ApplicationMap()
        start, end = [BUTTON], [dict(BUTTON, identifier='home')]
        mapping.record(start, end, 'settings', 'tap', 'Observed UI changed', True)
        route = mapping.route(mapping.state_id(start), mapping.state_id(end))
        self.assertEqual(len(route), 1)
        self.assertEqual(route[0]['action'], 'tap')

    def test_a_failed_or_interrupted_transition_is_not_a_return_route(self):
        mapping = ApplicationMap()
        start, end = [BUTTON], [dict(BUTTON, identifier='home')]
        mapping.record(start, end, 'settings', 'tap', 'User interrupted', False)
        self.assertEqual(mapping.route(mapping.state_id(start), mapping.state_id(end)), [])

    def test_input_classification_does_not_treat_android_static_text_as_editable(self):
        self.assertEqual(control_kind(dict(type='android.widget.TextView')), '')
        self.assertEqual(control_kind(dict(type='android.widget.EditText')), 'text')

    def test_plan_contract_rejects_a_boolean_task_id(self):
        with self.assertRaises(InvalidAgentResponse):
            validate_planning(decision(planUpdates=[task(True)]))

    def test_plan_contract_limits_one_response_to_six_task_updates(self):
        with self.assertRaisesRegex(InvalidAgentResponse, 'Too many'):
            validate_planning(decision(planUpdates=[task(number) for number in range(7)]))

    def test_planning_layer_has_no_device_api_or_storage_dependencies(self):
        forbidden = {'mobile', 'agent', 'openai_transport', 'evidence', 'scenario', 'os', 'subprocess', 'pathlib'}
        package = pathlib.Path(__file__).resolve().parents[1] / 'runtime/test_planning'
        for path in package.glob('*.py'):
            for node in ast.walk(ast.parse(path.read_text())):
                if isinstance(node, ast.Import):
                    self.assertFalse({item.name.split('.')[0] for item in node.names} & forbidden)
                elif isinstance(node, ast.ImportFrom):
                    self.assertNotIn((node.module or '').split('.')[0], forbidden)


if __name__ == '__main__':
    unittest.main()
