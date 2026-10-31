"""Coordinate source-linked plans and observed application exploration."""

from .test_plan import TestPlan
from .exploration_memory import ExplorationMemory
from .context_memory import ContextMemory


class TestPlanner:
    """The execution layer supplies observations; this layer never operates the app."""

    def __init__(self, instructions='', requirements=None):
        self.instructions = instructions
        self.plan = TestPlan(instructions, requirements)
        self.memory = ExplorationMemory()
        self.context_memory = ContextMemory()
        self.available = None


    def observe(self, elements):
        self.memory.observe(elements)

    def record(self, before, after, action, entry):
        self.memory.record(before, after, action, entry)
        entry.update(planStepId=action['planStepId'], sourceState=self.memory.map.state_id(before),
                     destinationState=self.memory.map.state_id(after))

    def record_checks(self, checks):
        self.plan.record_checks(checks)

    def accept(self, action, elements):
        # These are AI-owned records. Their content does not approve device commands.
        self.plan.update(action['planUpdates'], action['planStepId'])
        self.memory.update(action, elements)
        self.memory.plan = list(action['remaining'])
        self.context_memory.accept(action['context'])

    def collections(self, history=None, requirements=None, checks=None, decisions=None, coverage=None, screenshots=None):
        return dict(actions=history or [], decisions=decisions or [], tasks=self.plan.saved()['tasks'], paths=list(self.memory.paths.values()),
            observations=list(self.memory.map.observations.values()),
            screenshots=screenshots or [],
            states=list(self.memory.map.states.values()), transitions=self.memory.map.transitions,
            requirements=requirements or [], checks=checks or [],
            configuration=[dict(row, id=row['control'], name=name) for name, row in self.memory.map.configuration.items()],
            coverage=[coverage] if coverage is not None else [], routes=[])

    def context(self, elements, history=None, requirements=None, checks=None, decisions=None, coverage=None, screenshots=None):
        context = dict(currentScreen=self.memory.map.state_id(elements),
            currentControls=self.memory.current_controls(elements), knownPaths=len(self.memory.paths))
        plan = self.plan.saved()
        self.available = self.collections(history, requirements, checks, decisions, coverage, screenshots)
        self.available['routes'] = [dict(id=row['id'], destination=row['targetState'],
            edges=self.memory.map.route(self.memory.map.state_id(elements), row['targetState']))
            for row in self.plan.tasks if row['targetState']]
        selected = self.context_memory.project(self.available)
        plan['tasks'] = selected['tasks']
        plan['taskCount'] = len(self.plan.tasks)
        context['testPlan'] = plan
        # These are exact AI selections, not a host-ranked frontier or history window.
        context['paths'] = selected['paths']
        context['applicationMap'] = dict(states=selected['states'], transitions=selected['transitions'],
            configuration=selected['configuration'], knownStates=len(self.memory.map.states))
        context['selectedActions'] = selected['actions']
        context['selectedRequirements'] = selected['requirements']
        context['selectedChecks'] = selected['checks']
        context['selectedDecisions'] = selected['decisions']
        context['selectedCoverage'] = selected['coverage']
        context['routes'] = selected['routes']
        context['selectedObservations'] = selected['observations']
        context['selectedScreenshots'] = selected['screenshots']
        context['summary'] = (self.context_memory.selection or {}).get('summary', '')
        context['selection'] = self.context_memory.saved()
        context['catalogue'] = {name: len(rows) for name, rows in self.available.items()}
        context['resourceFeedback'] = list(self.context_memory.unavailable)
        return context

    def saved(self):
        return dict(testPlan=self.plan.saved(), exploration=self.memory.saved(),
                    planningRemaining=self.plan.remaining() + self.memory.remaining(),
                    contextSelection=self.context_memory.saved())
