"""Small redaction cases use invented secrets, pictures, and local result files."""

import io
import json
import pathlib
import sys
import tempfile
import unittest
from types import SimpleNamespace

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "runtime"))

from PIL import Image
from check_recorder import CheckRecorder
from check_results import scenario_verdict
from coverage_tracker import CoverageTracker
from device_runner import result_exit_code
from errors import InfrastructureError
from evidence import RunJournal
from redaction import Redactor, ScreenMasker
from requirement_results import RequirementResults
from scenario import ScenarioRunner


def redactor(secret):
    return Redactor({"credentials": {"test": {"password": secret}}})


def check(status="failed", source="instructions", requirement_id=""):
    return dict(
        taskId=0,
        subject="Save",
        source=source,
        status=status,
        expected="Save the value",
        observed="The value is absent",
        reason="",
        requirementId=requirement_id,
        instructionQuote="",
    )


class TextRedactionTests(unittest.TestCase):
    def test_one_digit_secret_does_not_change_numbers(self):
        self.assertEqual(
            redactor("1").object({"number": 1, "text": "value 1"}),
            {"number": 1, "text": "value <redacted>"},
        )

    def test_existing_marker_survives_repeated_redaction(self):
        scrub = redactor("e")
        self.assertEqual(scrub.text(scrub.text("secret")), "s<redacted>cr<redacted>t")

    def test_secret_starting_with_the_marker_is_removed_completely(self):
        self.assertEqual(redactor("<redacted>private").text("<redacted>private"), "<redacted>")

    def test_json_escaped_unicode_is_removed_from_logs(self):
        self.assertEqual(redactor("páss").text(r"log p\u00e1ss"), "log <redacted>")

    def test_json_escaped_quote_is_removed_from_logs(self):
        self.assertEqual(redactor('a"b').text(r"log a\"b"), "log <redacted>")

    def test_json_escaped_backslash_is_removed_from_logs(self):
        self.assertEqual(redactor("a\\b").text(r"log a\\b"), "log <redacted>")

    def test_longer_secret_is_removed_before_a_shorter_secret(self):
        scrub = Redactor({"credentials": {"test": {"username": "abc", "password": "ab"}}})
        self.assertEqual(scrub.text("abc ab"), "<redacted> <redacted>")

    def test_untrusted_status_field_is_still_text(self):
        self.assertEqual(redactor("failed").object({"status": "failed"}), {"status": "<redacted>"})

    def test_check_metadata_stays_intact_while_observations_are_scrubbed(self):
        value = dict(check(), observed="failed")
        safe = redactor("failed").records.check(value)
        self.assertEqual(safe["status"], "failed")
        self.assertEqual(safe["observed"], "<redacted>")

    def test_requirement_id_is_not_redacted(self):
        value = check(source="requirements", requirement_id="REQ-0001")
        self.assertEqual(redactor("REQ-0001").records.check(value)["requirementId"], "REQ-0001")

    def test_metadata_exemption_cannot_hide_nested_text(self):
        with self.assertRaises(InfrastructureError):
            redactor("private").records.check(dict(check(), status={"text": "private"}))

    def test_unknown_status_cannot_produce_a_pass(self):
        with self.assertRaises(InfrastructureError):
            scenario_verdict([check("<redacted>"), check("passed")], False, True)


class ScreenSecretTests(unittest.TestCase):
    def assert_masked(self, secret):
        scrub = redactor(secret)
        item = dict(
            identifier="ordinary-label",
            type="Label",
            text=secret,
            coordinates=dict(x=5, y=5, width=10, height=10),
        )
        image = io.BytesIO()
        Image.new("RGB", (30, 30), "white").save(image, format="PNG")
        safe, encoded = ScreenMasker(scrub).capture(
            [item], image.getvalue(), dict(width=30, height=30)
        )
        with Image.open(io.BytesIO(encoded)) as picture:
            self.assertEqual(picture.getpixel((10, 10)), (0, 0, 0))
            self.assertEqual(picture.getpixel((29, 29)), (255, 255, 255))
        self.assertEqual(safe[0]["text"], "<masked>")

    def test_unicode_secret_masks_pixels(self):
        self.assert_masked("páss")

    def test_quote_in_secret_masks_pixels(self):
        self.assert_masked('a"b')

    def test_backslash_in_secret_masks_pixels(self):
        self.assert_masked("a\\b")

    def test_newline_in_secret_masks_pixels(self):
        self.assert_masked("a\nb")

    def test_nested_original_string_is_detected(self):
        self.assertTrue(redactor("páss").sensitive({"attributes": [{"value": "páss"}]}))

    def test_sensitive_label_without_bounds_stops(self):
        image = io.BytesIO()
        Image.new("RGB", (30, 30), "white").save(image, format="PNG")
        with self.assertRaises(InfrastructureError):
            ScreenMasker(redactor("páss")).capture(
                [{"text": "páss"}], image.getvalue(), dict(width=30, height=30)
            )

    def test_non_sensitive_label_needs_no_mask(self):
        self.assertFalse(redactor("páss").sensitive({"text": "Public value"}))

    def test_element_id_mask_hides_nested_unknown_text(self):
        scrub = Redactor({"masking": {"rules": [{"element-id": "Login"}]}})
        item = dict(
            identifier="Login",
            ref="1",
            attributes=[{"value": "unknown secret"}],
            coordinates=dict(x=5, y=5, width=10, height=10),
        )
        image = io.BytesIO()
        Image.new("RGB", (30, 30), "white").save(image, format="PNG")
        safe, _ = ScreenMasker(scrub).capture([item], image.getvalue(), dict(width=30, height=30))
        self.assertEqual(safe[0]["attributes"][0]["value"], "<masked>")
        self.assertEqual(safe[0]["ref"], "1")

    def test_ui_reference_and_type_are_metadata(self):
        item = dict(ref="1", type="Button", label="value 1")
        safe = redactor("1").records.element(item)
        self.assertEqual(safe["ref"], "1")
        self.assertEqual(safe["type"], "Button")
        self.assertEqual(safe["label"], "value <redacted>")


class MemoryEvidence:
    def save_image(self, name, image):
        return "devices/1/" + name


class BudgetFixture:
    def snapshot(self):
        return {"requests": 1, "accountedUpperCost": "0.01"}


class ResultRedactionTests(unittest.TestCase):
    def session(self, definitions=None):
        return SimpleNamespace(
            image=b"masked",
            coverage=CoverageTracker(),
            result=dict(
                requirements=RequirementResults.initial(definitions or []),
                checks=[],
                steps=[],
                crashes=[],
            ),
        )

    def test_failed_password_cannot_turn_instruction_failure_into_a_pass(self):
        scrub = redactor("failed")
        session = self.session()
        CheckRecorder(scrub, MemoryEvidence(), lambda: None).record(
            session, [check(), dict(check("passed"), subject="Load")], "Test save and load"
        )
        ScenarioRunner._complete(
            session, dict(remaining=[], completion="complete", observation="Finished")
        )
        device = dict(
            index=1,
            device=dict(id="1", platform="android"),
            scenarios=[session.result],
            error=None,
            stoppingReason=None,
        )
        with tempfile.TemporaryDirectory() as folder:
            journal = RunJournal(folder, scrub, BudgetFixture(), "2026-10-28_12-00-00-001")
            journal.publish(device)
            self.assertEqual(result_exit_code(journal.results), 1)
            data = json.loads(pathlib.Path(folder, "ui-results.json").read_text())
        self.assertEqual(data["devices"][0]["scenarios"][0]["verdict"], "failed")
        self.assertEqual(data["devices"][0]["scenarios"][0]["checks"][0]["status"], "failed")

    def test_requirement_id_password_does_not_break_recording(self):
        session = self.session([dict(id="REQ-0001", text="Save works")])
        CheckRecorder(redactor("REQ-0001"), MemoryEvidence(), lambda: None).record(
            session, [check(source="requirements", requirement_id="REQ-0001")], "Test save"
        )
        self.assertEqual(session.result["requirements"][0]["status"], "failed")

    def test_journal_preserves_ids_and_evidence_links(self):
        value = dict(
            index=1,
            device=dict(id="1", platform="android", name="Device 1"),
            scenarios=[
                dict(
                    target="Release1",
                    appId="app.1",
                    verdict="failed",
                    completion="complete",
                    checks=[dict(check(), screenshot="devices/1/check-0001.png")],
                )
            ],
            error=None,
            stoppingReason=None,
        )
        with tempfile.TemporaryDirectory() as folder:
            journal = RunJournal(folder, redactor("1"), BudgetFixture(), "2026-10-28_12-00-00-001")
            journal.publish(value)
            data = json.loads(pathlib.Path(folder, "ui-results.json").read_text())
        self.assertEqual(data["runId"], "2026-10-28_12-00-00-001")
        self.assertEqual(data["devices"][0]["device"]["id"], "1")
        self.assertEqual(data["devices"][0]["device"]["name"], "Device <redacted>")
        self.assertEqual(
            data["devices"][0]["scenarios"][0]["checks"][0]["screenshot"],
            "devices/1/check-0001.png",
        )


if __name__ == "__main__":
    unittest.main()
