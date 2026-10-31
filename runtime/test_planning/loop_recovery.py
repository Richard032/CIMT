"""Keep recovery requests and AI decisions separate from format retries."""

from errors import InvalidAgentResponse


class LoopRecovery:
    def __init__(self):
        self.records = []
        self.pending = None

    def request(self, kind, reason, step):
        self.pending = dict(id=len(self.records), kind=kind, reason=reason,
            step=step, status='waiting', decision='', explanation='')
        self.records.append(self.pending)

    def validate(self, action):
        decision = action['recovery']
        if self.pending is None:
            if action['action'] == 'recover' and decision['id'] == -1 and decision['decision'] == 'replan':
                return
            if decision['decision'] != 'none' or decision['id'] != -1:
                raise InvalidAgentResponse('No recovery is pending; use recovery id -1 and decision none')
            return
        if action['action'] == 'recall':
            return
        if action['action'] == 'recover':
            raise InvalidAgentResponse('Recovery is already pending; use recall, a revised action, or finish blocked')
        if decision['id'] != self.pending['id'] or decision['decision'] == 'none':
            raise InvalidAgentResponse('A pending recovery needs its request id and an AI decision')
        if decision['decision'] == 'blocked' and not (
                action['action'] == 'done' and action['completion'] == 'blocked'):
            raise InvalidAgentResponse('A blocked recovery must finish blocked with remaining work')

    def acknowledge(self, action):
        if self.pending is None or action['action'] == 'recall':
            return
        decision = action['recovery']
        self.pending.update(status='blocked' if decision['decision'] == 'blocked' else 'continued',
            decision=decision['decision'], explanation=decision['reason'])
        self.pending = None
