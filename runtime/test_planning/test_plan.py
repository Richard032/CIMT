"""Keep source-linked testing tasks separate from navigation coverage."""


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


    def update(self, updates, active):
        for row in updates:
            if row['id'] < 0:
                row = dict(row, id=max((task['id'] for task in self.tasks), default=-1) + 1)
            task = next((task for task in self.tasks if task['id'] == row['id']), None)
            if task is None:
                self.tasks.append(dict(row, result='not tested'))
            else:
                task.update(row)
        self.active = active
        for task in self.tasks:
            if task['status'] == 'active' and task['id'] != active:
                task['status'] = 'pending'
        task = next((task for task in self.tasks if task['id'] == active), None)
        if task and task['status'] not in ['tested', 'blocked']:
            task['status'] = 'active'

    def record_checks(self, checks):
        for check in checks:
            identifier = check.get('id')
            if identifier is not None:
                if identifier <= self.last_check_id:
                    continue
                self.last_check_id = identifier
            task = next((row for row in self.tasks if row['id'] == check['taskId']), None)
            if task is None or task['source'] != check['source'] or task['requirementId'] != check['requirementId']:
                # Keep the original finding, but do not attach it to another source.
                continue
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


    def remaining(self):
        return [task['subject'] + ': ' + (task['reason'] or task['status'])
                for task in self.tasks if task['status'] != 'tested']

    def saved(self):
        return dict(tasks=[dict(task) for task in self.tasks], activeTaskId=self.active,
                    nextTaskId=max((task['id'] for task in self.tasks), default=-1) + 1)
