"""Small requirement mapping cases with no API or physical device calls."""

import pathlib
import json
import sys
import unittest
from types import SimpleNamespace

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "runtime"))

from check_results import scenario_verdict, validate_checks
from action_prompt import ActionPromptBuilder
from check_recorder import CheckRecorder
from errors import InfrastructureError
from requirement_results import RequirementResults
from redaction import Redactor

DEFINITION = {"id": "REQ-0001", "text": "Value stays saved.", "startLine": 1, "endLine": 1}


def check(status="passed", requirement_id="REQ-0001", quote=""):
    return {
        "subject": "Saved value",
        "source": "requirements",
        "status": status,
        "expected": "Value stays saved",
        "observed": "Saved value visible",
        "reason": "Instructions take priority" if status == "overridden" else "",
        "requirementId": requirement_id,
        "instructionQuote": quote,
        "step": 2,
    }


def validate(value):
    # The recorder adds the step; it is not a field supplied by the model.
    validate_checks([{key: item for key, item in value.items() if key != "step"}])


class RequirementResultTests(unittest.TestCase):
    def setUp(self):
        self.rows = RequirementResults.initial([DEFINITION])

    def test_every_item_starts_not_tested_with_a_reason(self):
        self.assertEqual(self.rows[0]["status"], "not tested")
        self.assertTrue(self.rows[0]["reason"])
        self.assertEqual(self.rows[0]["text"], DEFINITION["text"])

    def test_known_id_updates_the_matching_item(self):
        RequirementResults.validate([check()], self.rows, "")
        RequirementResults.record(self.rows, [check()])
        self.assertEqual(self.rows[0]["status"], "passed")
        self.assertEqual(self.rows[0]["step"], 2)

    def test_unknown_id_is_rejected_before_recording(self):
        with self.assertRaises(InfrastructureError):
            RequirementResults.validate([check(requirement_id="UNKNOWN")], self.rows, "")
        self.assertEqual(self.rows[0]["status"], "not tested")

    def test_failed_result_cannot_be_erased_by_a_retry(self):
        RequirementResults.record(self.rows, [check("failed")])
        RequirementResults.record(self.rows, [dict(check(), step=3)])
        self.assertEqual(self.rows[0]["status"], "failed")
        self.assertEqual(self.rows[0]["step"], 2)

    def test_valid_instruction_override_changes_the_applicable_expectation(self):
        failed = check("failed")
        override = check("overridden", quote="Explore only")
        objective = {"source": "instructions", "subject": "Objective", "status": "passed"}
        RequirementResults.validate([override], self.rows, "Explore only")
        RequirementResults.record(self.rows, [failed, override])
        self.assertEqual(self.rows[0]["status"], "overridden")
        self.assertEqual(
            scenario_verdict([failed, override, objective], False, True, self.rows), "passed"
        )

    def test_later_requirement_check_does_not_cancel_a_valid_override(self):
        RequirementResults.record(
            self.rows, [check("overridden", quote="Explore only"), check("failed")]
        )
        self.assertEqual(self.rows[0]["status"], "overridden")

    def test_crash_still_fails_when_a_requirement_is_overridden(self):
        RequirementResults.record(self.rows, [check("overridden", quote="Explore only")])
        self.assertEqual(scenario_verdict([], True, True, self.rows), "failed")

    def test_unknown_result_can_be_resolved_later(self):
        RequirementResults.record(self.rows, [dict(check("inconclusive"), reason="Hidden value")])
        RequirementResults.record(self.rows, [check()])
        self.assertEqual(RequirementResults.unresolved(self.rows), 0)

    def test_override_needs_an_exact_quote_from_instructions(self):
        with self.assertRaises(InfrastructureError):
            RequirementResults.validate(
                [check("overridden", quote="invented")], self.rows, "Explore only"
            )

    def test_valid_override_retains_reason_and_instruction(self):
        value = check("overridden", quote="Explore only")
        validate(value)
        RequirementResults.validate([value], self.rows, "Explore only")
        RequirementResults.record(self.rows, [value])
        self.assertEqual(self.rows[0]["instructionQuote"], "Explore only")
        self.assertEqual(self.rows[0]["status"], "overridden")

    def test_override_without_quote_is_rejected(self):
        with self.assertRaises(InfrastructureError):
            validate(check("overridden"))

    def test_a_requirement_check_cannot_omit_its_id(self):
        with self.assertRaises(InfrastructureError):
            validate(check(requirement_id=""))

    def test_subject_changes_do_not_change_requirement_identity(self):
        RequirementResults.record(self.rows, [check("failed")])
        RequirementResults.record(self.rows, [dict(check(), subject="Another label")])
        self.assertEqual(self.rows[0]["status"], "failed")

    def test_resolving_a_requirement_uses_its_id_even_if_the_label_changes(self):
        unknown = dict(check("inconclusive"), subject="Old label", reason="Value hidden")
        passed = dict(check(), subject="New label")
        objective = {"source": "instructions", "subject": "Objective", "status": "passed"}
        RequirementResults.record(self.rows, [unknown, passed])
        self.assertEqual(
            scenario_verdict([unknown, passed, objective], False, True, self.rows), "passed"
        )

    def test_one_pass_does_not_change_another_requirement(self):
        rows = RequirementResults.initial([DEFINITION, dict(DEFINITION, id="REQ-0002")])
        RequirementResults.record(rows, [check()])
        self.assertEqual(rows[1]["status"], "not tested")
        self.assertEqual(RequirementResults.unresolved(rows), 1)

    def test_evidence_is_attached_only_to_the_matching_decision(self):
        RequirementResults.record(self.rows, [check("failed")])
        RequirementResults.evidence(self.rows, [dict(check(), step=3)], path="wrong.png")
        self.assertEqual(self.rows[0]["screenshot"], "")
        RequirementResults.evidence(self.rows, [check("failed")], path="correct.png")
        self.assertEqual(self.rows[0]["screenshot"], "correct.png")

    def test_untested_requirement_prevents_a_pass(self):
        instruction = {"status": "passed", "source": "instructions", "subject": "Objective"}
        self.assertEqual(scenario_verdict([instruction], False, True, self.rows), "inconclusive")


class MappingPromptTests(unittest.TestCase):
    def test_model_receives_ids_source_text_and_current_statuses(self):
        rows = RequirementResults.initial([DEFINITION])
        body = ActionPromptBuilder("fixture").build(
            "Explore", "Value stays saved.", "", [], b"masked", [], [], {}, rows
        )
        state = json.loads(body["input"][1]["content"][0]["text"])
        self.assertEqual(state["requirementResults"], rows)
        fields = body["text"]["format"]["schema"]["properties"]["checks"]["items"]["required"]
        self.assertIn("requirementId", fields)
        self.assertIn("instructionQuote", fields)


class MemoryEvidence:
    """Record image names or simulate a storage failure."""

    def __init__(self, fail=False):
        self.fail = fail

    def save_image(self, name, image):
        if self.fail:
            raise OSError("image storage failed")
        return "devices/fixture/" + name


class CheckRecorderTests(unittest.TestCase):
    def setUp(self):
        self.session = SimpleNamespace(
            image=b"masked",
            result={
                "requirements": RequirementResults.initial([DEFINITION]),
                "checks": [],
                "steps": [],
                "crashes": [],
                "verdict": "inconclusive",
            },
        )
        self.published = []

    def publish(self):
        self.published.append(self.session.result["verdict"])

    def record(self, value, fail=False):
        value = {key: item for key, item in value.items() if key != "step"}
        CheckRecorder(Redactor({}), MemoryEvidence(fail), self.publish).record(
            self.session, [value], "Explore only"
        )

    def test_recorded_result_uses_the_host_step_and_image(self):
        self.record(check())
        row = self.session.result["requirements"][0]
        self.assertEqual(row["step"], 0)
        self.assertEqual(row["screenshot"], "devices/fixture/check-0000.png")

    def test_storage_failure_keeps_the_requirement_failure(self):
        with self.assertRaises(OSError):
            self.record(check("failed"), fail=True)
        row = self.session.result["requirements"][0]
        self.assertEqual(row["status"], "failed")
        self.assertIn("storage failed", row["evidenceError"])
        self.assertEqual(self.published[0], "failed")

    def test_invalid_mapping_cannot_partially_update_the_ledger(self):
        with self.assertRaises(InfrastructureError):
            self.record(check(requirement_id="UNKNOWN"))
        self.assertEqual(self.session.result["checks"], [])


if __name__ == "__main__":
    unittest.main()
