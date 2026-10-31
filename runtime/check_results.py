"""Explicit test observations and a verdict policy without device or API calls."""


CHECK_FIELDS = [
    "taskId",
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
CHECK_OBJECT_SCHEMA = {
    "type": "object",
    "properties": {
        "taskId": {"type": "integer", "minimum": 0},
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


def _source_schema(source, identifier):
    """Describe the identifiers used to link optional finding records."""
    return dict(CHECK_OBJECT_SCHEMA, properties=dict(
        CHECK_OBJECT_SCHEMA["properties"],
        source={"type": "string", "enum": [source]},
        requirementId=identifier,
    ))


CHECK_SCHEMA = {"anyOf": [
    _source_schema("instructions", {"type": "string", "enum": [""]}),
    _source_schema("requirements", {"type": "string", "pattern": r"\S"}),
]}


def scenario_verdict(checks, has_crash, complete, requirements=None):
    """A known failure stays failed. Finishing navigation alone cannot prove a pass."""
    requirements = requirements or []
    # Retain old observations, but do not judge an overridden expectation as a failure.
    overridden = {row["id"] for row in requirements if row["status"] == "overridden"}
    checks = [
        check
        for check in checks
        if check["source"] != "requirements" or check["requirementId"] not in overridden
    ]
    if has_crash or any(check["status"] == "failed" for check in checks + requirements):
        return "failed"
    if any(check.get('status') not in CHECK_STATUSES for check in checks + requirements):
        return 'inconclusive'
    if any(row["status"] in ["not tested", "inconclusive"] for row in requirements):
        return "inconclusive"
    if not complete or not checks:
        return "inconclusive"
    # Later evidence may resolve an unknown check. Keep every observation in the report.
    latest = {
        (
            check["source"],
            check["requirementId"] if check["source"] == "requirements" else check.get('taskId', check["subject"]),
        ): check
        for check in checks
    }
    if any(check["status"] in ["not tested", "inconclusive"] for check in latest.values()):
        return "inconclusive"
    objective_checked = any(
        check["source"] == "instructions" and check["status"] == "passed" for check in checks
    )
    return "passed" if objective_checked else "inconclusive"
