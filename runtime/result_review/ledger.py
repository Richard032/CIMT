"""Build a compact ledger from recorded scenario evidence."""

from copy import deepcopy


class EvidenceLedger:
    """Summarize recorded steps and checks without deciding their meaning."""

    MAX_STEPS = 200
    MAX_CHECKS = 100
    MAX_SCREENS = 5
    MAX_ELEMENTS = 40

    def snapshot(self, result):
        steps = result.get('steps', [])
        checks = result.get('checks', [])
        events = {event.get('step'): event for batch in result.get('batchFeedback', {}).get('batches', [])
                  for event in batch.get('path', []) if event.get('kind') == 'command'}
        return {
            'progressNote': result.get('evidenceProgress', ''),
            'steps': [self._step(row, events.get(row.get('step'), {})) for row in steps[-self.MAX_STEPS:]],
            'omittedEarlierSteps': max(0, len(steps) - self.MAX_STEPS),
            'checks': [self._check(row) for row in checks[-self.MAX_CHECKS:]],
            'omittedEarlierChecks': max(0, len(checks) - self.MAX_CHECKS),
            'recentScreens': self._screens(result),
        }

    def _screens(self, result):
        batches = result.get('batchFeedback', {}).get('batches', [])
        references = {row['id']: row for batch in batches for row in batch.get('observations', [])}
        observations = {row['id']: row for row in result.get('exploration', {}).get('applicationMap', {}).get('observations', [])}
        events = [event for batch in batches for event in batch.get('path', [])
                  if event.get('kind') == 'command' and event.get('status') == 'executed'
                  and event.get('observedAt') and event.get('observation') in references]
        screens = []
        for event in events[-self.MAX_SCREENS:]:
            reference = references[event['observation']]
            observation = observations.get(reference.get('uiObservation'))
            if observation is None:
                continue
            elements = observation.get('elements', [])
            fields = ('identifier', 'type', 'label', 'text', 'visible', 'enabled')
            screens.append(dict(step=event.get('step'), observedAt=event.get('observedAt'),
                observation=event['observation'],
                elements=[{key: deepcopy(row[key]) for key in fields if key in row}
                          for row in elements[:self.MAX_ELEMENTS]],
                omittedElements=max(0, len(elements) - self.MAX_ELEMENTS)))
        return screens

    @staticmethod
    def _step(row, event):
        action = row.get('action', {})
        if isinstance(action, dict):
            action = {key: action[key] for key in ('action', 'commandId', 'field', 'ref') if key in action}
        fields = ('step', 'controlLabel', 'targetIdentifier', 'targetType', 'decisionObservedAt', 'completedAt', 'actionDispatched',
                  'observedOutcome', 'actionError', 'resultObservation', 'observation')
        entry = dict(action=deepcopy(action), **{key: deepcopy(row[key]) for key in fields if key in row})
        if event.get('observedAt'):
            entry['observedAt'] = event['observedAt']
        return entry

    @staticmethod
    def _check(row):
        fields = ('id', 'step', 'subject', 'status', 'expected', 'observed', 'reason', 'requirementId')
        return {key: deepcopy(row[key]) for key in fields if key in row}
