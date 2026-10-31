"""Correct invalid AI decisions before recording checks or executing actions."""

import json
from action_prompt import validate_action
from errors import InvalidAgentResponse, NoProgressAction, ExplorationStalled
from requirement_results import RequirementResults

MAX_DECISION_ATTEMPTS = 3


class DecisionRecovery:
    """Owns bounded response correction. It never executes a device action."""

    def __init__(self, inputs, config, redactor, control, activity=None):
        self.inputs = inputs
        self.config = config
        self.redactor = redactor
        self.control = control
        self.activity = activity

    def choose(self, mobile, session, agent, evidence, publish):
        feedback = []
        for attempt in range(1, MAX_DECISION_ATTEMPTS + 1):
            self.control.check()
            action = None
            try:
                action = self._request(agent, session, feedback, mobile.device)
                validate_action(action)
                RequirementResults.validate(
                    action["checks"], session.result["requirements"], self.inputs["instructions"]
                )
                session.planner.validate(action, session.elements)
            except InvalidAgentResponse as error:
                rejected = self._record_rejection(
                    session, action if action is not None else error.response,
                    error, attempt, evidence, publish,
                )
                self._event(mobile, session, "rejected", attempt, str(error))
                if attempt == MAX_DECISION_ATTEMPTS:
                    if isinstance(error, NoProgressAction):
                        raise ExplorationStalled("Exploration blocked: repeated actions made no observed progress") from error
                    raise InvalidAgentResponse(
                        "AI response correction exhausted after " + str(MAX_DECISION_ATTEMPTS)
                        + " attempts: " + str(error)
                    ) from error
                feedback.append({"error": rejected["error"], "response": rejected["response"]})
                self._refresh(mobile, session, publish)
                continue
            if feedback:
                self._event(mobile, session, "corrected", attempt, "Response accepted; no action repeated")
            return action

    def _request(self, agent, session, feedback, device):
        arguments = [
            self.inputs["instructions"], self.inputs.get("requirements", ""),
            self._scoped_setup(session, device), session.elements, session.image, session.history,
            list(self.config.get("credentials", {})), session.coverage.snapshot(),
            session.result["requirements"],
        ]
        memory = session.planner.context(session.elements)
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

    def _record_rejection(self, session, response, error, attempt, evidence, publish):
        rejected = {
            "attempt": attempt,
            "step": len(session.result["steps"]),
            "status": "unaccepted",
            "error": self.redactor.text(str(error)),
            # Invalid metadata is untrusted text too; do not use the typed action redactor.
            "response": self.redactor.object(response),
        }
        records = session.result.setdefault("rejectedResponses", [])
        records.append(rejected)
        publish()
        try:
            rejected["screenshot"] = evidence.save_image(
                "rejected-" + str(len(records)).zfill(4) + ".png", session.image
            )
        except Exception as error:
            rejected["evidenceError"] = self.redactor.text(str(error))
            publish()
            raise
        publish()
        return rejected

    def _refresh(self, mobile, session, publish):
        self.control.check()
        session.elements, session.image = mobile.snapshot()
        session.planner.observe(session.elements)
        session.result.update(self.redactor.records.planning(session.planner.saved()))
        session.coverage.observe(session.elements)
        session.result["coverage"] = session.coverage.snapshot()
        publish()

    def _event(self, mobile, session, status, attempt, message):
        if self.activity:
            self.activity.write(
                "AI response correction", status,
                "Attempt " + str(attempt) + "/" + str(MAX_DECISION_ATTEMPTS) + ": " + message,
                mobile.device, session.result["target"],
            )
