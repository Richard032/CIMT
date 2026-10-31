"""Coordinate source-linked plans and observed application exploration."""

from .test_plan import TestPlan
from .exploration_memory import ExplorationMemory


class TestPlanner:
    """The execution layer supplies observations; this layer never operates the app."""

    def __init__(self, instructions='', requirements=None):
        self.instructions = instructions
        self.plan = TestPlan(instructions, requirements)
        self.memory = ExplorationMemory()

    def validate(self, action, elements):
        self.plan.validate(action['planUpdates'], action['planStepId'], self.memory.map.states,
                           finishing=action['action'] == 'done')
        task_ids = {task['id'] for task in self.plan.tasks} | {row['id'] for row in action['planUpdates']}
        self.memory.validate_updates(action, elements, task_ids)
        self.memory.validate(elements, action, self.instructions)

    def observe(self, elements):
        self.memory.observe(elements)

    def record(self, before, after, action, entry):
        self.memory.record(before, after, action, entry)
        entry.update(planStepId=action['planStepId'], sourceState=self.memory.map.state_id(before),
                     destinationState=self.memory.map.state_id(after))

    def record_checks(self, checks):
        self.plan.record_checks(checks)

    def accept(self, action, elements):
        # Validation happens before any candidate is allowed to change the plan or map.
        self.plan.update(action['planUpdates'], action['planStepId'])
        self.memory.update(action, elements)
        self.memory.plan = list(action['remaining'])

    def context(self, elements):
        task = self.plan.tasks[self.plan.active]
        context = self.memory.snapshot(elements, task['targetState'])
        plan = self.plan.saved()
        # Full tasks stay in the report. Keep the active task and pending work in AI input.
        plan['tasks'] = sorted(plan['tasks'], key=lambda row: (row['id'] != self.plan.active, row['status'] == 'tested'))[:40]
        plan['taskCount'] = len(self.plan.tasks)
        context['testPlan'] = plan
        return context

    def saved(self):
        return dict(testPlan=self.plan.saved(), exploration=self.memory.saved(),
                    planningRemaining=self.plan.remaining() + self.memory.remaining())
