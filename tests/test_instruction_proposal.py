import json
import pathlib
import tempfile
import sys
import time
import unittest
from unittest.mock import patch

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "runtime"))

from agent import Agent
from budget import Budget
from run_ui import finalize_proposal

MODEL = "gpt-5.4-mini-2026-03-17"


class Transport:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def request(self, path, body):
        self.calls.append((path, body))
        return {"status": "completed", "usage": {"input_tokens": 10, "output_tokens": 10},
                "output": [{"type": "message", "content": [{"type": "output_text", "text": self.response}]}]}


class InstructionProposalTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.config = {"ai-model": {"name": MODEL, "api-key": "secret-key"},
                       "credentials": {"user": {"password": "secret-password"}}}
        self.report = pathlib.Path(self.folder.name)
        self.budget = Budget(MODEL, 5, "USD")
        self.transport = Transport(json.dumps({"interpretation": "Check the field after waiting",
            "instructions": "Check field", "setup": "Open settings", "evidence": "Screen observed"}))
        self.context = dict(config=dict(self.config, **{"ai-budget": {"amount": 5, "currency": "USD"}}),
            report=self.folder.name, deadline=time.time() + 60, inputs={"instructions": "secret-password", "setup": "Original"},
            outcome={"cancelled": False})

    def create(self):
        with patch("run_ui.Agent", side_effect=lambda config, budget, deadline:
                   Agent(config, budget, deadline, transport=self.transport)):
            self.assertEqual(finalize_proposal(self.context), 0)
        return (self.report / "instruction-setup-proposal.md").read_text()

    def ledger(self):
        return json.loads((self.report / "ai-budget.json").read_text())

    def evidence(self):
        return json.loads(self.transport.calls[0][1]["input"][1]["content"][0]["text"])

    def test_saves_separate_sections_and_redacts_request(self):
        output = self.create()
        self.assertIn("## Interpretation of the testing task\n\nCheck the field after waiting", output)
        self.assertIn("## Proposed instructions\n\nCheck field", output)
        self.assertIn("## Proposed setup\n\nOpen settings", output)
        self.assertIn("Screen observed", output)
        self.assertNotIn("secret-password", json.dumps(self.transport.calls))
        self.assertEqual(self.ledger()["requests"], 1)
        self.assertEqual(self.ledger()["requestUsage"][0]["kind"], "instruction proposal")
        request_file = self.report / "proposal-requests" / "ai-request-0000.json"
        recorded = request_file.read_text()
        self.assertNotIn("secret-password", recorded)
        self.assertIn("<redacted>", recorded)
        self.assertEqual(json.loads((self.report / "proposal-requests.json").read_text())["aiRequests"][0]["status"], "completed")

    def test_exhausted_budget_records_reason_without_request(self):
        self.context["config"]["ai-budget"]["amount"] = 0
        output = self.create()
        self.assertIn("No AI proposal was generated", output)
        self.assertIn("budget", output)
        self.assertIn("Original", output)
        self.assertNotIn("secret-password", output)
        self.assertEqual(self.transport.calls, [])

    def test_cancelled_run_reviews_partial_results_and_preserves_prior_charges(self):
        self.context["outcome"]["cancelled"] = True
        (self.report / "stop-requested").touch()
        (self.report / "ui-results.json").write_text(json.dumps({"devices": [{"index": 1, "observation": "Spinner"}]}))
        self.budget.reserve()
        (self.report / "ai-budget.json").write_text(json.dumps(self.budget.snapshot()))
        output = self.create()

        self.assertIn("Screen observed", output)
        self.assertTrue(self.evidence()["runOutcome"]["cancelled"])
        self.assertEqual(self.evidence()["devices"][0]["observation"], "Spinner")
        self.assertEqual(self.ledger()["requests"], 2)
        self.assertEqual(self.ledger()["pendingUpperCost"], "0.000000")
        self.assertEqual(self.ledger()["uncertainUpperCost"], str(self.budget.bound))

    def test_unstarted_run_can_review_its_inputs(self):
        self.create()
        self.assertEqual(self.evidence()["devices"], [])
        self.assertIn("instructions", self.evidence()["inputs"])

    def test_invalid_saved_budget_does_not_reset_spending_or_call_ai(self):
        ledger = self.report / "ai-budget.json"
        ledger.write_text("{}")
        self.assertIn("could not be restored safely", self.create())
        self.assertEqual(ledger.read_text(), "{}")
        self.assertEqual(self.transport.calls, [])

    def test_invalid_response_records_failure(self):
        self.transport.response = "not JSON"
        output = self.create()
        self.assertIn("not valid JSON", output)
        self.assertIn("No AI proposal was generated", output)

    def test_missing_interpretation_is_reported(self):
        self.transport.response = json.dumps(dict(instructions="Check field", setup="Open settings", evidence="Observed"))
        self.assertIn("missing required sections", self.create())


if __name__ == "__main__":
    unittest.main()
