"""Explicit test observations and a verdict policy without device or API calls."""

from errors import InfrastructureError

CHECK_FIELDS = [
    "subject",
    "source",
    "status",
    "expected",
    "observed",
    "reason",
    "requirementId",
    "instructionQuote",
]
CHECK_STATUSES = ["passed", "failed", "not tested", "inconclusive", "overridden"]
CHECK_SCHEMA = {
    "type": "object",
    "properties": {
        "subject": {"type": "string"},
        "source": {"type": "string", "enum": ["instructions", "requirements"]},
        "status": {"type": "string", "enum": CHECK_STATUSES},
        "expected": {"type": "string"},
        "observed": {"type": "string"},
        "reason": {"type": "string"},
        "requirementId": {"type": "string"},
        "instructionQuote": {"type": "string"},
    },
    "required": CHECK_FIELDS,
    "additionalProperties": False,
}


def validate_checks(checks):
    """Reject missing or ambiguous results before they can affect a verdict."""
    if not isinstance(checks, list):
        raise InfrastructureError("Test checks must be a list")
    for check in checks:
        _validate_check(check)


def _validate_check(check):
    if not isinstance(check, dict) or set(check) != set(CHECK_FIELDS):
        raise InfrastructureError("A test check has invalid fields")
    if any(not isinstance(value, str) for value in check.values()):
        raise InfrastructureError("Test check values must be text")
    if not check["subject"].strip() or check["source"] not in ["instructions", "requirements"]:
        raise InfrastructureError("A test check needs a subject and a valid source")
    if check["status"] not in CHECK_STATUSES:
        raise InfrastructureError("A test check has an invalid status")
    if check["source"] == "requirements" and not check["requirementId"].strip():
        raise InfrastructureError("A requirement check needs its catalogue ID")
    if check["source"] == "instructions" and check["requirementId"]:
        raise InfrastructureError("An instructions check cannot use a requirement ID")
    if check["status"] == "overridden" and not check["instructionQuote"].strip():
        raise InfrastructureError("An overridden requirement needs an instruction quote")
    _validate_evidence(check)


def _validate_evidence(check):
    if check["status"] in ["passed", "failed"]:
        if not check["expected"].strip() or not check["observed"].strip():
            raise InfrastructureError("A decided check needs expected and observed behavior")
    elif not check["reason"].strip():
        raise InfrastructureError("An unresolved or overridden check needs an explanation")
    if check["status"] == "overridden" and check["source"] != "requirements":
        raise InfrastructureError("Only a requirement can be overridden by instructions")


def scenario_verdict(checks, has_crash, complete, requirements=None):
    """A known failure stays failed. Finishing navigation alone cannot prove a pass."""
    requirements = requirements or []
    if any(check.get("status") not in CHECK_STATUSES for check in checks + requirements):
        raise InfrastructureError("An invalid check status cannot produce a verdict")
    # Retain old observations, but do not judge an overridden expectation as a failure.
    overridden = {row["id"] for row in requirements if row["status"] == "overridden"}
    checks = [
        check
        for check in checks
        if check["source"] != "requirements" or check["requirementId"] not in overridden
    ]
    if has_crash or any(check["status"] == "failed" for check in checks + requirements):
        return "failed"
    if any(row["status"] in ["not tested", "inconclusive"] for row in requirements):
        return "inconclusive"
    if not complete or not checks:
        return "inconclusive"
    # Later evidence may resolve an unknown check. Keep every observation in the report.
    latest = {
        (
            check["source"],
            check["requirementId"] if check["source"] == "requirements" else check["subject"],
        ): check
        for check in checks
    }
    if any(check["status"] in ["not tested", "inconclusive"] for check in latest.values()):
        return "inconclusive"
    objective_checked = any(
        check["source"] == "instructions" and check["status"] == "passed" for check in checks
    )
    return "passed" if objective_checked else "inconclusive"
