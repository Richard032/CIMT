"""Provide resources and loop feedback without evaluating AI response format."""

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
        self.instructions.observe(mobile, session, evidence)
        publish()
        arguments = self.instructions.prepare(session, mobile.device, evidence)
        return agent.choose(*arguments)

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
