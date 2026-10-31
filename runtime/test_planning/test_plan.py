"""Keep source-linked testing tasks separate from navigation coverage."""

from errors import InvalidAgentResponse

OBJECTIVE_EXPECTATION = 'Execute the supplied testing instructions'


class TestPlan:
    def __init__(self, instructions='', requirements=None):
        self.instructions = instructions
        self.tasks = [dict(id=0, source='instructions', requirementId='', instructionQuote=instructions,
            subject='Testing objective', expected=OBJECTIVE_EXPECTATION,
            status='active', reason='', targetState='', result='not tested')]
        for row in requirements or []:
            self.tasks.append(dict(id=len(self.tasks), source='requirements', requirementId=row['id'],
                instructionQuote='', subject=row.get('text', row['id']), expected=row.get('text', row['id']),
                status='pending', reason='', targetState='', result='not tested'))
        self.active = 0

    def validate(self, updates, active, states, finishing=False):
        candidate = {row['id']: dict(row) for row in self.tasks}
        seen = set()
        for row in updates:
            if row['id'] in seen:
                raise InvalidAgentResponse('Plan updates contain duplicate task IDs')
            seen.add(row['id'])
            if row['id'] not in candidate and row['id'] != len(candidate):
                raise InvalidAgentResponse('New plan tasks must use nextTaskId in sequence')
            if row['targetState'] and row['targetState'] not in states:
                raise InvalidAgentResponse('Plan targetState must be an observed state ID')
            if not row['subject'].strip() or not row['expected'].strip():
                raise InvalidAgentResponse('Plan tasks need a subject and expected behavior')
            if row['status'] == 'blocked' and not row['reason'].strip():
                raise InvalidAgentResponse('A blocked plan task needs a reason')
            if row['source'] == 'instructions':
                if row['requirementId'] or not row['instructionQuote'].strip() or row['instructionQuote'] not in self.instructions:
                    raise InvalidAgentResponse('Instruction plan tasks need an exact instruction quote and no requirement ID')
            elif row['requirementId'] not in {task['requirementId'] for task in self.tasks if task['source'] == 'requirements'} or row['instructionQuote']:
                raise InvalidAgentResponse('Requirement plan tasks need a known requirement ID and no instruction quote')
            if row['id'] not in candidate and row['source'] == 'requirements':
                raise InvalidAgentResponse('Update the existing catalogue task instead of duplicating it')
            if row['id'] in candidate:
                old = candidate[row['id']]
                # The first decision refines the placeholder into a concrete objective.
                refining = row['id'] == 0 and old['expected'] == OBJECTIVE_EXPECTATION
                fixed = ['source', 'requirementId', 'subject'] if refining else [
                    'source', 'requirementId', 'instructionQuote', 'subject', 'expected']
                if any(row[key] != old[key] for key in fixed):
                    raise InvalidAgentResponse('An existing plan task cannot change its source or meaning')
            candidate[row['id']] = dict(row)
        if active not in candidate or candidate[active]['status'] == 'blocked' and not finishing:
            raise InvalidAgentResponse('planStepId must select an available plan task')
        if not finishing and candidate[active]['expected'] == OBJECTIVE_EXPECTATION:
            raise InvalidAgentResponse('Refine the objective into concrete expected behavior or select a source-linked subtask before acting')

    def update(self, updates, active):
        for row in updates:
            if row['id'] == len(self.tasks):
                self.tasks.append(dict(row, result='not tested'))
            else:
                self.tasks[row['id']].update(row)
        self.active = active
        for task in self.tasks:
            if task['status'] == 'active' and task['id'] != active:
                task['status'] = 'pending'
        if self.tasks[active]['status'] not in ['tested', 'blocked']:
            self.tasks[active]['status'] = 'active'

    def record_checks(self, checks):
        for task in self.tasks:
            matching = [check for check in checks if check['source'] == task['source'] and (
                check['requirementId'] == task['requirementId'] if task['source'] == 'requirements'
                else check['subject'] == task['subject'])]
            for check in matching:
                # A later pass cannot erase a failure. Existing override validation still applies.
                if task['result'] == 'overridden' or task['result'] == 'failed' and check['status'] != 'overridden':
                    continue
                task['result'] = check['status']
                task['status'] = 'tested' if check['status'] in ['passed', 'failed', 'overridden'] else 'pending'
                task['reason'] = check['reason']

    def remaining(self):
        return [task['subject'] + ': ' + (task['reason'] or task['status'])
                for task in self.tasks if task['status'] != 'tested']

    def saved(self):
        return dict(tasks=[dict(task) for task in self.tasks], activeTaskId=self.active, nextTaskId=len(self.tasks))
