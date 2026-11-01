"""Keep the ordered facts from each command batch without judging their meaning."""

from copy import deepcopy


class BatchFeedback:
    """Scenario-local records. Device I/O and AI calls belong to their callers."""

    def __init__(self):
        self.batches = []
        self.observations = {}
        self.warnings = {}
        self.latest = None
        self.current_warnings = []
        self.current = None

    def observe(self, observation, warnings, action_result=False):
        identifier = observation['id']
        self.observations.setdefault(identifier, deepcopy(observation))
        self.warnings.update({row['id']: deepcopy(row) for row in warnings})
        warning_ids = [row['id'] for row in warnings]
        if action_result and self.current is not None:
            self.current.update(observation=identifier, warnings=warning_ids,
                uiChange='changed' if identifier != self.latest else 'no observed change')
        elif self.latest is not None and identifier != self.latest and self.batches:
            self.batches[-1]['path'].append(dict(kind='observation', observation=identifier,
                timestamp=observation['timestamp'], warnings=warning_ids))
        self.latest = identifier
        self.current_warnings = warning_ids

    def start(self, identifier):
        self.batches.append(dict(id=identifier, initialObservation=self.latest,
            initialWarnings=list(self.current_warnings), path=[], delivery='pending'))

    def take(self, row):
        self.current = self._command(row)
        self.batches[-1]['path'].append(self.current)

    @staticmethod
    def _command(row):
        action = row['response']
        # Secret text is never copied into the compact feedback target.
        target = {key: action[key] for key in ('ref', 'x', 'y', 'direction', 'credential', 'field') if key in action}
        return dict(kind='command', commandId=row['id'], action=action['action'], target=target,
            status=row['status'], step=row.get('step'), observation=None,
            uiChange='observation unavailable', warnings=[], error='')

    def finish(self, row, error='', target_label=''):
        if self.current is not None:
            self.current.update(status=row['status'], step=row.get('step'), error=error, targetLabel=target_label)
            if row['status'] in ('handled', 'deferred'):
                self.current.update(observation=self.latest, uiChange='not applicable')
            self.current = None

    def sync(self, commands):
        """Keep cancelled/unstarted commands in order, without inventing observations."""
        by_id = {row['id']: row for row in commands}
        for batch in self.batches:
            recorded = set()
            for event in batch['path']:
                if event['kind'] != 'command':
                    continue
                row = by_id[event['commandId']]
                event.update(status=row['status'], step=row.get('step'))
                if row['status'] in ('cancelled', 'not executed', 'interrupted', 'deferred'):
                    event['error'] = row.get('reason', '')
                recorded.add(row['id'])
            for row in commands:
                if row['batchId'] == batch['id'] and row['id'] not in recorded and row['status'] not in ('queued', 'started'):
                    event = self._command(row)
                    event['error'] = row.get('reason', '')
                    batch['path'].append(event)

    def _resolved(self, batch):
        observations = {batch['initialObservation']} - {None}
        warnings = set(batch['initialWarnings'])
        for event in batch['path']:
            if event.get('observation') is not None:
                observations.add(event['observation'])
            warnings.update(event['warnings'])
        return dict(deepcopy(batch), observations=[deepcopy(row) for key, row in self.observations.items() if key in observations],
            warnings=[deepcopy(row) for key, row in self.warnings.items() if key in warnings])

    def collection(self):
        return [self._resolved(batch) for batch in self.batches]

    def pending(self):
        return [self._resolved(batch) for batch in self.batches if batch['delivery'] == 'pending']

    def delivered(self):
        for batch in self.batches:
            batch['delivery'] = 'supplied to AI'

    def close(self):
        for batch in self.batches:
            if batch['delivery'] == 'pending':
                batch['delivery'] = 'not supplied; scenario ended'

    def saved(self):
        return dict(batches=self.collection())
