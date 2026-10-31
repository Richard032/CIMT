"""Keep recovery requests and AI decisions separate from format retries."""


class LoopRecovery:
    def __init__(self):
        self.records = []
        self.pending = None

    def request(self, kind, reason, step):
        self.pending = dict(id=len(self.records), kind=kind, reason=reason,
            step=step, status='waiting', decision='', explanation='')
        self.records.append(self.pending)


    def acknowledge(self, action):
        if self.pending is None or action['action'] in ['recall', 'note']:
            return
        decision = action['recovery']
        if decision['id'] != self.pending['id'] or decision['decision'] == 'none':
            self.pending.update(status='continued', decision='AI action',
                explanation='AI supplied its next command without a structured acknowledgement.')
            self.pending = None
            return
        self.pending.update(status='blocked' if decision['decision'] == 'blocked' else 'continued',
            decision=decision['decision'], explanation=decision['reason'])
        self.pending = None
