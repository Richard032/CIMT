"""Provide resources and loop feedback without evaluating AI response format."""

from contextlib import nullcontext
from copy import deepcopy
import json
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
                                  check_cancelled=self.control.check,
                                  previous_tool_result=self._previous_tool_result(session))
        with self._operation('AI action decision', mobile, session):
            reply = agent.decide(request)
        if reply.get('action') not in ('recall', 'note'):
            session.gesture_preview = None
        session.feedback.delivered()
        return reply

    def _previous_tool_result(self, session):
        call = session.commands.tool_call
        if call is None:
            return None
        batches = session.feedback.pending()
        if not batches:
            return None
        row = session.commands.records[-1]
        event = next((event for event in batches[-1]['path'] if event.get('commandId') == row['id']), None)
        if event is None:
            return None
        arguments = self.redactor.object(json.loads(call['arguments']))
        call = dict(call, arguments=json.dumps(arguments, ensure_ascii=False))
        result = {key: event[key] for key in ('status', 'step', 'observation', 'uiChange', 'error', 'actionFeedback')
                  if key in event}
        return call, self.redactor.object(result)

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
