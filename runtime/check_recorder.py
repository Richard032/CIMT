"""Record checks and their evidence without owning scenario navigation."""

from check_results import scenario_verdict
from requirement_results import RequirementResults


class CheckRecorder:
    """Publish observations before saving their already masked image."""

    def __init__(self, redactor, evidence, publish):
        self.redactor = redactor
        self.evidence = evidence
        self.publish = publish

    def record(self, session, checks, instructions):
        rows = session.result["requirements"]
        if not checks:
            return
        index = len(session.result["steps"])
        safe = [self.redactor.records.check(check) for check in checks]
        first_id = len(session.result['checks'])
        recorded = [dict(check, step=index, id=first_id + number) for number, check in enumerate(safe)]
        session.result["checks"].extend(recorded)
        RequirementResults.record(rows, recorded)
        step = {
            "step": index,
            "action": "check",
            "observation": "; ".join(
                check["subject"] + ": " + check["status"] for check in recorded
            ),
        }
        session.result["steps"].append(step)
        session.result["verdict"] = scenario_verdict(
            session.result["checks"], bool(session.result["crashes"]), False, rows
        )
        self.publish()
        self._save_image(session, step, recorded)
        self.publish()

    def _save_image(self, session, step, checks):
        try:
            # This is the masked screen used for the decision, not a later screen.
            path = self.evidence.save_image(
                "check-" + str(step["step"]).zfill(4) + ".png", session.image
            )
            step["screenshot"] = path
            for check in checks:
                check["screenshot"] = path
            RequirementResults.evidence(session.result["requirements"], checks, path=path)
        except Exception as error:
            safe = self.redactor.text(str(error))
            step["evidenceError"] = safe
            RequirementResults.evidence(session.result["requirements"], checks, error=safe)
            self.publish()
            raise
