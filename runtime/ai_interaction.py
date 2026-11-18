"""Provide resources and loop feedback without evaluating AI response format."""

from contextlib import nullcontext
from copy import deepcopy
from ai_instructions.context import InstructionContext
from request_journal import RequestJournal
from decision_agent import DecisionAgent, DecisionRequest


class AiInteraction:
    """Coordinates AI requests and recovery notices outside the instruction layer."""

    def __init__(self, inputs, config, redactor, control, activity=None, budget=None):
        self.redactor = redactor
        self.control = control
        self.activity = activity
        self.budget = budget
        self.instructions = InstructionContext(inputs, config.get("credentials", {}), redactor)

    def choose(self, mobile, session, agent: DecisionAgent, evidence, publish):
        self.control.check()
        with self._operation('Refresh AI screen evidence', mobile, session):
            self.instructions.observe(mobile, session, evidence)
        publish()
        with self._operation('Prepare AI context', mobile, session):
            arguments = self.instructions.prepare(session, mobile.device, evidence)
        observer = RequestJournal(session.result, evidence, self.redactor, publish)

        def report_timing(timing):
            if self.activity:
                status = 'stopped' if self.control.interrupted else timing['status']
                self.activity.write('AI provider response', status, timing['kind'],
                    mobile.device, session.result['target'], seconds=timing['seconds'])

        # Isolate agent context edits from live evidence; keep service hooks shared.
        request = DecisionRequest(*deepcopy(arguments), request_observer=observer, report_timing=report_timing,
                                  budget=self.budget, deadline=self.control.deadline,
                                  check_cancelled=self.control.check)
        with self._operation('AI action decision', mobile, session):
            reply = agent.decide(request)
        if reply.get('action') not in ('recall', 'note'):
            session.gesture_preview = None
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
