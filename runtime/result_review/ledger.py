"""Build a compact ledger from recorded scenario evidence."""

from copy import deepcopy


class EvidenceLedger:
    """Summarize recorded steps and checks without deciding their meaning."""

    MAX_STEPS = 200
    MAX_CHECKS = 100

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
        }

    @staticmethod
    def _step(row, event):
        action = row.get('action', {})
        if isinstance(action, dict):
            action = {key: action[key] for key in ('action', 'commandId', 'field', 'ref') if key in action}
        fields = ('step', 'controlLabel', 'targetIdentifier', 'targetType', 'completedAt', 'actionDispatched',
                  'observedOutcome', 'actionError', 'resultObservation', 'observation')
        entry = dict(action=deepcopy(action), **{key: deepcopy(row[key]) for key in fields if key in row})
        if event.get('observedAt'):
            entry['observedAt'] = event['observedAt']
        return entry

    @staticmethod
    def _check(row):
        fields = ('id', 'step', 'subject', 'status', 'expected', 'observed', 'reason', 'requirementId')
        return {key: deepcopy(row[key]) for key in fields if key in row}
