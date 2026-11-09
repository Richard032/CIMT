"""Requirement results for one target/device objective. No device or API access."""


UNRESOLVED = {"not tested", "inconclusive"}


class RequirementResults:
    """Keep every catalogue item, including items with no observation yet."""

    @staticmethod
    def initial(definitions):
        return [
            dict(
                item,
                status="not tested",
                expected="",
                observed="",
                reason="No observation has evaluated this requirement yet.",
                instructionQuote="",
                step=None,
                screenshot="",
                evidenceError="",
            )
            for item in definitions
        ]


    @staticmethod
    def record(rows, checks):
        by_id = {row["id"]: row for row in rows}
        for check in checks:
            if check["source"] != "requirements":
                continue
            row = by_id.get(check["requirementId"])
            if row is None:
                continue
            # Instructions change the applicable expectation. A normal pass cannot erase a failure.
            if row["status"] == "overridden":
                continue
            if row["status"] != "failed" or check["status"] == "overridden":
                for key in ["status", "expected", "observed", "reason", "instructionQuote", "step"]:
                    row[key] = check[key]
                row["screenshot"] = ""
                row["evidenceError"] = "Evidence storage has not completed."

    @staticmethod
    def evidence(rows, checks, path="", error=""):
        for row in rows:
            if any(
                check["requirementId"] == row["id"] and check["step"] == row["step"]
                for check in checks
            ):
                row["screenshot"] = path
                row["evidenceError"] = error

    @staticmethod
    def unresolved(rows):
        return sum(row["status"] in UNRESOLVED for row in rows)
