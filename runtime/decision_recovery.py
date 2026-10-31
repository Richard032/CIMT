"""Provide resources and loop feedback without evaluating AI response format."""

import json
from errors import NoProgressAction


class DecisionRecovery:
    """Supplies evidence and recovery information. It never approves a plan."""

    def __init__(self, inputs, config, redactor, control, activity=None):
        self.inputs = inputs
        self.config = config
        self.redactor = redactor
        self.control = control
        self.activity = activity

    def choose(self, mobile, session, agent, evidence, publish):
        self.control.check()
        feedback = session.resource_feedback
        action = self._request(agent, session, feedback, mobile.device, evidence)
        if session.recovery.pending is None:
            try:
                session.planner.memory.check_repetition(session.elements, action)
            except NoProgressAction as error:
                return action, str(error)
        return action, None

    def request_recovery(self, mobile, session, kind, reason, publish, evidence=None):
        session.recovery.request(kind, reason, len(session.result['steps']))
        session.result['recoveries'] = [self.redactor.records.recovery(row) for row in session.recovery.records]
        publish()
        if self.activity:
            self.activity.write('AI-directed recovery', 'waiting',
                'Request ' + str(session.recovery.pending['id']) + ' (' + kind
                + '); fresh evidence and an AI assessment required. Details are in the scenario report.',
                mobile.device, session.result['target'])
        self._refresh(mobile, session, publish, evidence)

    def _request(self, agent, session, feedback, device, evidence):
        arguments = [
            self.inputs["instructions"], self.inputs.get("requirements", ""),
            self._scoped_setup(session, device), session.elements, session.image, session.history,
            list(self.config.get("credentials", {})), session.coverage.snapshot(),
            session.result["requirements"],
        ]
        screenshots = list(evidence.images.values())
        session.result['screenshots'] = screenshots
        memory = session.planner.context(session.elements, session.history,
            session.result['requirements'], session.result.get('checks', []), session.result.get('decisions', []),
            session.coverage.snapshot(), screenshots)
        if session.recovery.pending is not None:
            memory['recoveryRequest'] = self.redactor.records.recovery(session.recovery.pending)
        memory = self.redactor.records.request_context(memory)
        # Bootstrap exposes addresses only. Historical pixels require an explicit AI selection.
        memory['historicalImages'] = evidence.load_images(memory['selectedScreenshots']) if session.planner.context_memory.selection is not None else []
        arguments.extend([feedback, memory])
        return agent.choose(*arguments)

    def _scoped_setup(self, session, device):
        """Keep one worker's remaining plan separate from work on other devices."""
        scope = {"platform": device.get("platform", ""), "deviceId": device.get("id", ""),
                 "target": session.result["target"]}
        return self.inputs.get("setup", "") + "\nCIMT execution scope: " + json.dumps(scope) + (
            "\nExecute the supplied objective only for this device and target. "
            "Report remaining work only within this scope. Other devices and targets "
            "are scheduled independently; do not claim they were or were not tested."
        )


    def _refresh(self, mobile, session, publish, evidence=None):
        self.control.check()
        session.elements, session.image = mobile.snapshot()
        session.planner.observe(session.elements)
        session.result.update(self.redactor.records.planning(session.planner.saved()))
        session.coverage.observe(session.elements)
        session.result["coverage"] = session.coverage.snapshot()
        if evidence is not None:
            evidence.save_step('observation-' + str(len(evidence.images)).zfill(4), session.elements, session.image)
            session.result['screenshots'] = list(evidence.images.values())
        publish()
