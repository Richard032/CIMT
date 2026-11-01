"""Keep AI commands in received order and record their execution state."""

from collections import deque
from copy import deepcopy


class CommandQueue:
    """Scenario-local FIFO data. It never calls AI, devices or stopping policy."""

    def __init__(self):
        self.records = []
        self.pending = deque()
        self.current = None
        self.next_batch = 0

    def add(self, reply):
        first = dict(reply)
        commands = [first] + first.pop('queuedCommands', [])
        for position, action in enumerate(commands):
            row = dict(id=len(self.records), batchId=self.next_batch, position=position,
                       status='queued', response=deepcopy(action))
            self.records.append(row)
            self.pending.append(row)
        self.next_batch += 1

    def take(self):
        self.current = self.pending.popleft()
        self.current['status'] = 'started'
        return dict(self.current['response'], commandId=self.current['id'],
                    batchId=self.current['batchId'], batchPosition=self.current['position'])

    def finish(self, status, reason='', step=None):
        if self.current is not None:
            row = self.current
            self.current.update(status=status, reason=reason)
            if step is not None:
                self.current['step'] = step
            self.current = None
            return row

    def cancel_pending(self, reason):
        """Cancel the whole pending batch after a command cannot run."""
        count = len(self.pending)
        while self.pending:
            self.pending.popleft().update(status='cancelled', reason=reason)
        return count

    def stop(self, reason):
        """Keep unperformed commands visible; do not silently execute them later."""
        self.finish('interrupted', reason)
        while self.pending:
            self.pending.popleft().update(status='not executed', reason=reason)

    def saved(self):
        return dict(commands=deepcopy(self.records))
