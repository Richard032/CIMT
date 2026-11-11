"""Build a compact ledger from recorded scenario evidence."""

from copy import deepcopy


class EvidenceLedger:
    """Summarize recorded steps and checks without deciding their meaning."""

    MAX_STEPS = 200
    MAX_CHECKS = 100

    def snapshot(self, result):
        steps = result.get('steps', [])
        checks = result.get('checks', [])
        return {
            'steps': [self._step(row) for row in steps[-self.MAX_STEPS:]],
            'omittedEarlierSteps': max(0, len(steps) - self.MAX_STEPS),
            'checks': [self._check(row) for row in checks[-self.MAX_CHECKS:]],
            'omittedEarlierChecks': max(0, len(checks) - self.MAX_CHECKS),
        }

    @staticmethod
    def _step(row):
        action = row.get('action', {})
        if isinstance(action, dict):
            action = {key: action[key] for key in ('action', 'commandId', 'field', 'ref') if key in action}
        fields = ('step', 'controlLabel', 'completedAt', 'actionDispatched',
                  'observedOutcome', 'actionError', 'resultObservation', 'observation')
        return dict(action=deepcopy(action), **{key: deepcopy(row[key]) for key in fields if key in row})

    @staticmethod
    def _check(row):
        fields = ('id', 'step', 'subject', 'status', 'expected', 'observed', 'reason', 'requirementId')
        return {key: deepcopy(row[key]) for key in fields if key in row}
