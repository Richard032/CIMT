"""Context selection tests use synthetic records and no API or device."""

import json
import pathlib
import sys
import unittest
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / 'runtime'))
from test_planning.context_memory import ContextMemory, COLLECTIONS
from test_planning.application_map import ApplicationMap
from test_planning.planner import TestPlanner
from test_planning.test_plan import TestPlan
from request_context import prepare_context
from redaction import Redactor
from errors import InvalidAgentResponse, NoProgressAction
from budget import Budget
from test_runtime_components import action, api_agent
from evidence import ScenarioEvidence
from errors import InfrastructureError
from action_prompt import ActionPromptBuilder
from test_test_planner import BUTTON, INSTRUCTIONS, check, decision


def selection(summary='', include_all=None, records=None):
    return dict(summary=summary, includeAll=include_all or [], records=records or [])


class ContextSelectionTests(unittest.TestCase):
    def setUp(self):
        self.memory = ContextMemory()
        self.records = {name: [] for name in COLLECTIONS}
        self.records['actions'] = [dict(action='tap', result='Outcome ' + str(number)) for number in range(60)]

    def test_bootstrap_supplies_all_history_without_a_fixed_window(self):
        self.assertEqual(self.memory.project(self.records)['actions'], self.records['actions'])

    def test_ai_can_keep_an_old_action_and_omit_everything_else(self):
        chosen = selection('Keep the first failure', records=[dict(collection='actions', id='0')])
        self.memory.validate(chosen, self.records)
        self.memory.accept(chosen)
        projected = self.memory.project(self.records)
        self.assertEqual(projected['actions'], [self.records['actions'][0]])
        self.assertEqual(len(self.records['actions']), 60)

    def test_latest_is_followed_only_when_selected_by_ai(self):
        self.memory.accept(selection(records=[dict(collection='actions', id='latest')]))
        self.records['actions'].append(dict(action='back', result='New outcome'))
        self.assertEqual(self.memory.project(self.records)['actions'], [self.records['actions'][-1]])

    def test_ai_can_retrieve_a_whole_collection_after_omitting_it(self):
        self.memory.accept(selection())
        self.assertEqual(self.memory.project(self.records)['actions'], [])
        self.memory.accept(selection(include_all=['actions']))
        self.assertEqual(len(self.memory.project(self.records)['actions']), 60)

    def test_unknown_addresses_are_rejected_instead_of_silently_omitted(self):
        with self.assertRaisesRegex(InvalidAgentResponse, 'Unknown context record'):
            self.memory.validate(selection(records=[dict(collection='actions', id='999')]), self.records)

    def test_bad_collection_shape_is_a_correctable_response_error(self):
        with self.assertRaises(InvalidAgentResponse):
            self.memory.validate(selection(records=[dict(collection='unknown', id='0')]), self.records)

    def test_ai_selection_does_not_keep_shared_mutable_records(self):
        chosen = selection('A useful summary', include_all=['actions'])
        self.memory.accept(chosen)
        chosen['summary'] = 'Changed outside the layer'
        self.assertEqual(self.memory.saved()['summary'], 'A useful summary')

    def test_ai_can_request_an_exact_range_to_discover_older_record_ids(self):
        chosen = selection(records=[dict(collection='actions', id='@3:7')])
        self.memory.validate(chosen, self.records)
        self.memory.accept(chosen)
        self.assertEqual(self.memory.project(self.records)['actions'], self.records['actions'][3:7])

    def test_out_of_range_requests_are_rejected_instead_of_truncated(self):
        with self.assertRaisesRegex(InvalidAgentResponse, 'outside its collection'):
            self.memory.validate(selection(records=[dict(collection='actions', id='@55:70')]), self.records)

    def test_ai_can_retain_its_selection_without_repeating_the_summary(self):
        chosen = selection('Remember the failed save', records=[dict(collection='actions', id='0')])
        self.memory.accept(chosen)
        self.memory.validate(None, self.records)
        self.memory.accept(None)
        self.assertEqual(self.memory.saved(), chosen)


class ContextCapacityTests(unittest.TestCase):
    def state(self):
        return dict(instructions='Explore settings', elements=[BUTTON], coverage={},
            recentActions=[dict(action='tap', observation='x' * 3000)], requirementResults=[],
            explorationMemory=dict(summary='Keep failed saves', selection=selection(include_all=['actions']),
                                   catalogue=dict(actions=1), recoveryRequest=dict(id=0)))

    def test_oversized_selection_requests_ai_reduction_without_selecting_records(self):
        state = self.state()
        reduced = prepare_context(state, allowance=1000)
        self.assertIn('contextSelectionRequired', reduced)
        self.assertEqual(reduced['recentActions'], [])
        self.assertEqual(reduced['explorationMemory']['summary'], 'Keep failed saves')
        self.assertEqual(reduced['explorationMemory']['selection'], state['explorationMemory']['selection'])
        self.assertEqual(len(state['recentActions']), 1)
        self.assertEqual(reduced['elements'], state['elements'])

    def test_fitting_selection_reaches_the_model_unchanged(self):
        state = self.state()
        self.assertEqual(prepare_context(state, allowance=10000), state)

    def test_oversized_context_cannot_dispatch_a_model_action(self):
        agent, _, _ = api_agent([action('tap', ref='@e1')])
        history = [dict(action='tap', observation='x' * 70000)]
        with self.assertRaisesRegex(InvalidAgentResponse, 'Context reduction is pending'):
            agent.choose('Explore', '', '', [BUTTON], b'masked', history, [], {})

    def test_ai_can_explain_a_blocker_instead_of_spending_on_more_reduction_requests(self):
        finish = action(completion='blocked', checks=[], remaining=['Cannot select enough source context'])
        agent, _, _ = api_agent([finish])
        result = agent.choose('Explore', '', '', [BUTTON], b'masked',
            [dict(action='tap', observation='x' * 70000)], [], {})
        self.assertEqual(result['action'], 'done')
        self.assertEqual(result['completion'], 'blocked')


class RequestUsageTests(unittest.TestCase):
    def test_missing_cache_details_are_not_reported_as_zero_cache_usage(self):
        budget = Budget('gpt-5.4-mini-2026-03-17', 5, 'USD')
        budget.reserve()
        budget.finish(dict(input_tokens=100, output_tokens=10))
        self.assertIsNone(budget.snapshot()['cachedInputTokens'])

    def test_cache_usage_is_recorded_without_relaxing_the_spending_bound(self):
        budget = Budget('gpt-5.4-mini-2026-03-17', 5, 'USD')
        budget.reserve()
        budget.finish(dict(input_tokens=100, output_tokens=10, input_tokens_details=dict(cached_tokens=80)), kind='recovery')
        self.assertEqual(budget.snapshot()['cachedInputTokens'], 80)
        self.assertEqual(budget.snapshot()['requestUsage'][0]['kind'], 'recovery')
        self.assertEqual(budget.snapshot()['accountedUpperCost'], '0.00012')


class HistoricalImageTests(unittest.TestCase):
    def test_selected_image_must_still_match_the_saved_masked_bytes(self):
        with tempfile.TemporaryDirectory() as folder:
            evidence = ScenarioEvidence(folder, folder)
            path = evidence.save_image('first.png', b'masked first frame')
            selected = dict(evidence.images[path])
            self.assertEqual(evidence.load_images([selected])[0]['image'], b'masked first frame')
            pathlib.Path(folder, path).write_bytes(b'changed outside the evidence service')
            with self.assertRaisesRegex(InfrastructureError, 'changed after capture'):
                evidence.load_images([selected])

    def test_unknown_image_paths_are_not_loaded(self):
        with tempfile.TemporaryDirectory() as folder:
            evidence = ScenarioEvidence(folder, folder)
            with self.assertRaisesRegex(InfrastructureError, 'not registered'):
                evidence.load_images([dict(id=0, path='../private.png', sha256='invented')])

    def test_reusing_an_image_name_preserves_the_previous_evidence(self):
        with tempfile.TemporaryDirectory() as folder:
            evidence = ScenarioEvidence(folder, folder)
            first = evidence.save_image('first.png', b'masked first frame')
            second = evidence.save_image('first.png', b'masked second frame')
            self.assertNotEqual(first, second)
            self.assertEqual(pathlib.Path(folder, first).read_bytes(), b'masked first frame')
            self.assertEqual(len({row['id'] for row in evidence.images.values()}), 2)

    def test_duplicate_historical_pixels_are_referenced_without_another_image_payload(self):
        body = ActionPromptBuilder('fixture').build('Explore', '', '', [], b'masked current', [], [], {},
            exploration_memory=dict(historicalImages=[dict(id=0, image=b'masked current')]))
        content = body['input'][1]['content']
        self.assertEqual(sum(item['type'] == 'input_image' for item in content), 1)
        self.assertTrue(any('identical' in item.get('text', '') for item in content))


class PlanningRegressionTests(unittest.TestCase):
    def test_redacted_check_subject_does_not_break_task_identity(self):
        plan = TestPlan(INSTRUCTIONS)
        safe = Redactor({'credentials': {'test': {'password': 'e'}}}).records.check(check(subject='Testing objective'))
        plan.record_checks([dict(safe, id=0)])
        self.assertEqual(plan.tasks[0]['status'], 'tested')
        self.assertEqual(plan.tasks[0]['result'], 'passed')

    def test_historical_inconclusive_check_cannot_erase_a_new_blocker(self):
        plan = TestPlan(INSTRUCTIONS)
        old = dict(check(subject='Testing objective', status='inconclusive', reason='Not observed'), id=0)
        plan.record_checks([old])
        plan.update([dict(plan.tasks[0], status='blocked', reason='Equipment unavailable')], 0)
        plan.record_checks([old])
        self.assertEqual(plan.tasks[0]['status'], 'blocked')
        self.assertEqual(plan.tasks[0]['reason'], 'Equipment unavailable')

    def test_check_must_match_its_task_source(self):
        planner = TestPlanner(INSTRUCTIONS)
        with self.assertRaisesRegex(InvalidAgentResponse, 'taskId'):
            planner.validate(decision(checks=[check(taskId=99)]), [BUTTON])

    def test_changing_passive_text_does_not_create_duplicate_button_paths(self):
        planner = TestPlanner(INSTRUCTIONS)
        for number in range(40):
            planner.observe([BUTTON, dict(type='Text', identifier='status', text='Updated ' + str(number))])
        self.assertEqual(len(planner.memory.paths), 1)
        self.assertEqual(len(planner.memory.map.states), 1)
        self.assertEqual(len(next(iter(planner.memory.map.states.values()))['observations']), 40)

    def test_passive_changes_still_supply_repetition_facts_for_ai_recovery(self):
        planner = TestPlanner(INSTRUCTIONS)
        for number in range(5):
            before = [BUTTON, dict(type='Text', identifier='status', text=str(number))]
            after = [BUTTON, dict(type='Text', identifier='status', text=str(number + 1))]
            planner.record(before, after, decision(), {})
        with self.assertRaises(NoProgressAction):
            planner.validate(decision(), after)

    def test_configuration_learning_preserves_the_observed_navigation_route(self):
        mapping = ApplicationMap()
        home = [dict(BUTTON, identifier='home')]
        settings = [dict(BUTTON, value='German')]
        mapping.record(home, settings, 'language', 'tap', 'Observed UI changed', True)
        source = mapping.state_id(home)
        mapping.configure([dict(ref='@e1', name='Language', value='German')], settings)
        route = mapping.route(source, mapping.state_id(settings))
        self.assertEqual(len(route), 1)
        self.assertEqual(route[0]['destination'], mapping.state_id(settings))

    def test_observing_a_new_configuration_value_does_not_merge_the_old_variant(self):
        mapping = ApplicationMap()
        english = [dict(BUTTON, label='English')]
        german = [dict(BUTTON, label='German')]
        mapping.configure([dict(ref='@e1', name='Language', value='English')], english)
        first = mapping.state_id(english)
        mapping.record(english, german, 'language', 'tap', 'Observed UI changed', True)
        mapping.configure([dict(ref='@e1', name='Language', value='German')], german)
        second = mapping.state_id(german)
        self.assertNotEqual(mapping.resolve(first), second)
        self.assertEqual(len(mapping.route(first, second)), 1)

    def test_context_redaction_keeps_record_addresses_but_removes_private_summary(self):
        planner = TestPlanner(INSTRUCTIONS)
        planner.observe([BUTTON])
        planner.context_memory.accept(selection('private-value', records=[dict(collection='tasks', id='0')]))
        context = planner.context([BUTTON])
        safe = Redactor({'credentials': {'test': {'password': 'private-value'}}}).records.request_context(context)
        self.assertNotIn('private-value', json.dumps(safe))
        self.assertEqual(safe['selection']['records'][0]['id'], '0')

    def test_omitted_ui_text_remains_retrievable_by_an_ai_selected_observation_address(self):
        planner = TestPlanner(INSTRUCTIONS)
        planner.observe([BUTTON, dict(type='Text', identifier='status', text='Earlier outcome')])
        planner.context_memory.accept(selection())
        planner.observe([BUTTON, dict(type='Text', identifier='status', text='Current outcome')])
        self.assertEqual(planner.context([BUTTON])['selectedObservations'], [])
        planner.context_memory.accept(selection(records=[dict(collection='observations', id='@0')]))
        old = planner.context([BUTTON])['selectedObservations'][0]
        self.assertEqual(old['elements'][1]['text'], 'Earlier outcome')
