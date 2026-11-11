"""Provide resources and loop feedback without evaluating AI response format."""

from contextlib import nullcontext
from ai_instructions.context import InstructionContext


class AiInteraction:
    """Coordinates AI requests and recovery notices outside the instruction layer."""

    def __init__(self, inputs, config, redactor, control, activity=None):
        self.redactor = redactor
        self.control = control
        self.activity = activity
        self.instructions = InstructionContext(inputs, config.get("credentials", {}), redactor)

    def choose(self, mobile, session, agent, evidence, publish):
        self.control.check()
        with self._operation('Refresh AI screen evidence', mobile, session):
            self.instructions.observe(mobile, session, evidence)
        publish()
        with self._operation('Prepare AI context', mobile, session):
            arguments = self.instructions.prepare(session, mobile.device, evidence)
        operation = 'AI action decision'
        try:
            with self._operation(operation, mobile, session):
                reply = agent.choose(*arguments)
        finally:
            timing = getattr(agent, 'last_request_timing', None)
            if self.activity and timing is not None:
                status = 'stopped' if self.control.interrupted else timing['status']
                self.activity.write('AI provider response', status, timing['kind'],
                    mobile.device, session.result['target'], seconds=timing['seconds'])
        if getattr(agent, 'last_user_message', None) is not None:
            session.conversation.append(agent.last_user_message)
            session.conversation.append(dict(role='assistant',
                content=self.redactor.text(reply.get('modelResponse', ''))))
        session.feedback.delivered()
        return reply

    def _operation(self, name, mobile, session):
        return (self.activity.operation(name, mobile.device, session.result['target'])
                if self.activity else nullcontext())

    def request_recovery(self, mobile, session, kind, reason, publish, evidence=None, refresh=True):
        session.recovery.request(kind, reason, len(session.result['steps']))
        session.result['recoveries'] = [self.redactor.records.recovery(row) for row in session.recovery.records]
        publish()
        if self.activity:
            self.activity.write('AI-directed recovery', 'waiting',
                'Request ' + str(session.recovery.pending['id']) + ' (' + kind
                + '); fresh evidence and an AI assessment required. Details are in the scenario report.',
                mobile.device, session.result['target'])
        if refresh:
            self.control.check()
            self.instructions.observe(mobile, session, evidence)
            publish()
