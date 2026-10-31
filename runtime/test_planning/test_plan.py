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
        self.last_check_id = -1

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
        for check in checks:
            identifier = check.get('id')
            if identifier is not None:
                if identifier <= self.last_check_id:
                    continue
                self.last_check_id = identifier
            task = next((row for row in self.tasks if row['id'] == check['taskId']), None)
            if task is None:
                raise InvalidAgentResponse('Check taskId is not in the testing plan')
            # Keep failures even when a later check passes. Work status is independent.
            if task['result'] == 'overridden' or task['result'] == 'failed' and check['status'] != 'overridden':
                continue
            task['result'] = check['status']
            if check['status'] in ['passed', 'failed', 'overridden']:
                task['status'] = 'tested'
            elif task['status'] != 'blocked':
                task['status'] = 'pending'
            if task['status'] != 'blocked':
                task['reason'] = check['reason']

    def validate_checks(self, checks, updates):
        tasks = {row['id']: row for row in self.tasks}
        tasks.update({row['id']: row for row in updates})
        for check in checks:
            task = tasks.get(check['taskId'])
            if not task or check['source'] != task['source'] or check['requirementId'] != task['requirementId']:
                raise InvalidAgentResponse('Check taskId must match its plan source and requirement ID')

    def remaining(self):
        return [task['subject'] + ': ' + (task['reason'] or task['status'])
                for task in self.tasks if task['status'] != 'tested']

    def saved(self):
        return dict(tasks=[dict(task) for task in self.tasks], activeTaskId=self.active, nextTaskId=len(self.tasks))
