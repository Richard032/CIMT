"""Planning tests use masked synthetic observations without devices or an AI service."""

import ast
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / 'runtime'))
from test_planning.planner import TestPlanner
from test_planning.application_map import ApplicationMap
from test_planning.screen_model import control_kind, progress_identity
from errors import NoProgressAction
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
                     discoveredControls=[], configuration=[], pathDecisions=[],
                     context=dict(summary='', includeAll=[], records=[]),
                     recovery=dict(id=-1, decision='none', reason='')), **updates)


def check(subject='Language selection', status='passed', **updates):
    return dict(dict(taskId=0 if subject == 'Testing objective' else 2, subject=subject, source='instructions', requirementId='', status=status,
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

    def test_placeholder_objective_does_not_block_the_ai_command(self):
        self.planner.accept(decision(planUpdates=[]), self.screen)
        self.assertEqual(self.planner.plan.active, 0)

    def test_instruction_interpretation_is_stored_without_host_quote_evaluation(self):
        self.planner.accept(decision(planUpdates=[task(2, instructionQuote='My interpretation')]), self.screen)
        self.assertEqual(self.planner.plan.tasks[-1]['instructionQuote'], 'My interpretation')

    def test_ai_requirement_reference_is_retained_without_catalogue_reassignment(self):
        self.planner.accept(decision(planUpdates=[task(7, source='requirements',
            requirementId='REQ-9999', instructionQuote='')]), self.screen)
        self.assertEqual(self.planner.plan.tasks[-1]['id'], 7)
        self.assertEqual(self.planner.plan.tasks[-1]['requirementId'], 'REQ-9999')

    def test_an_accepted_task_is_retained_when_the_next_response_has_no_updates(self):
        action = decision(planUpdates=[task(2)], planStepId=2)
        self.planner.accept(action, self.screen)
        self.planner.accept(decision(planStepId=2), self.screen)
        self.assertEqual(self.planner.context(self.screen)['testPlan']['activeTaskId'], 2)
        self.assertEqual(len(self.planner.saved()['testPlan']['tasks']), 3)

    def test_ai_can_revise_its_task_description(self):
        self.planner.accept(decision(planUpdates=[task(2)]), self.screen)
        self.planner.accept(decision(planUpdates=[task(2, subject='Revised goal')]), self.screen)
        self.assertEqual(self.planner.plan.tasks[-1]['subject'], 'Revised goal')

    def test_unbound_task_reference_does_not_block_the_ai_command(self):
        self.planner.accept(decision(planStepId=99), self.screen)
        self.assertEqual(self.planner.plan.active, 99)
        self.assertEqual(len(self.planner.plan.tasks), 2)

    def test_blocked_task_remains_visible_without_approving_the_ai_command(self):
        row = task(2, status='blocked', reason='Permission was not authorized')
        self.planner.accept(decision(planUpdates=[row], planStepId=2), self.screen)
        self.assertIn('Language selection: Permission was not authorized', self.planner.plan.remaining())

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
        self.planner.accept(action, self.screen)
        self.assertFalse(any('Settings:' in item for item in self.planner.saved()['planningRemaining']))

    def test_unclassified_paths_remain_explicit_pending_work(self):
        self.assertIn('Settings: unclassified', self.planner.saved()['planningRemaining'])

    def test_unknown_path_is_retained_as_a_requested_path(self):
        self.planner.accept(decision(pathDecisions=[dict(id='invented', scope='out of scope',
            reason='AI scope decision', planStepId=0)]), self.screen)
        path = self.planner.memory.paths['invented']
        self.assertTrue(path['requested'])
        self.assertEqual(path['attempts'], 0)

    def test_ai_can_identify_a_generic_web_control_using_a_current_ref(self):
        screen = [dict(ref='@e7', type='android.view.View', text='Choose Location')]
        action = decision(discoveredControls=[dict(ref='@e7', kind='tap')])
        self.planner.accept(action, screen)
        current = self.planner.context(screen)['currentControls'][0]
        self.assertEqual(current['label'], 'Choose Location')
        self.assertEqual(current['kind'], 'tap')

    def test_absent_discovered_ref_does_not_become_an_observed_control(self):
        self.planner.accept(decision(discoveredControls=[dict(ref='@old', kind='tap')]), self.screen)
        self.assertNotIn('@old', [row['ref'] for row in self.planner.memory.current_controls(self.screen)])

    def test_configuration_value_is_ai_owned_context(self):
        self.planner.accept(decision(configuration=[dict(ref='@e1', name='Language', value='German')]),
            [dict(BUTTON, value='English')])
        self.assertEqual(self.planner.memory.map.configuration['Language']['value'], 'German')

    def test_unavailable_configuration_ref_does_not_create_an_observed_control(self):
        self.planner.accept(decision(configuration=[dict(ref='@missing', name='Enabled', value='false')]), self.screen)
        self.assertEqual(self.planner.memory.map.configuration, {})

    def test_current_boolean_configuration_is_supported(self):
        screen = [dict(BUTTON, checked=False)]
        self.planner.accept(decision(configuration=[dict(ref='@e1', name='Enabled', value='false')]), screen)
        self.assertEqual(self.planner.memory.map.configuration['Enabled']['value'], 'false')

    def test_observed_configuration_remains_context_on_the_next_screen(self):
        screen = [dict(BUTTON, value='German')]
        action = decision(configuration=[dict(ref='@e1', name='Language', value='German')],
            context=dict(summary='', includeAll=['configuration'], records=[]))
        self.planner.accept(action, screen)
        other = [dict(BUTTON, identifier='home')]
        self.planner.observe(other)
        context = self.planner.context(other)['applicationMap']['configuration'][0]
        self.assertEqual(context['value'], 'German')
        self.assertTrue(context['observedAt'])

    def test_configuration_names_remain_ai_owned(self):
        screen = [dict(BUTTON, value='English')]
        self.planner.accept(decision(configuration=[dict(ref='@e1', name='Language', value='English')]), screen)
        self.planner.accept(decision(configuration=[dict(ref='@e1', name='Other language', value='English')]), screen)
        self.assertIn('Other language', self.planner.memory.map.configuration)

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
            self.planner.memory.check_repetition(before, decision())

    def test_ai_can_select_all_tasks_without_a_host_history_window(self):
        for number in range(2, 47):
            self.planner.accept(decision(planUpdates=[task(number)], planStepId=number,
                context=dict(summary='', includeAll=['tasks'], records=[])), self.screen)
        context = self.planner.context(self.screen)['testPlan']
        self.assertEqual(len(context['tasks']), 47)
        self.assertEqual(context['activeTaskId'], 46)
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

    def test_missing_task_ids_receive_distinct_local_record_ids(self):
        planner = TestPlanner(INSTRUCTIONS)
        planner.accept(decision(planUpdates=[task(-1), task(-1)]), [BUTTON])
        self.assertEqual([row['id'] for row in planner.plan.tasks], [0, 1, 2])

    def test_seven_ai_task_updates_are_stored_without_a_format_limit(self):
        planner = TestPlanner(INSTRUCTIONS)
        planner.accept(decision(planUpdates=[task(number) for number in range(1, 8)]), [BUTTON])
        self.assertEqual(len(planner.plan.tasks), 8)

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
