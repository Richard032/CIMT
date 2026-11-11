import json
import pathlib
import tempfile
import sys
import time
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "runtime"))

from agent import Agent
from budget import Budget
from instruction_proposal import InstructionProposal
from redaction import Redactor
from run_control import RunControl

MODEL = "gpt-5.4-mini-2026-03-17"


class Transport:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def request(self, path, body):
        self.calls.append((path, body))
        return {"status": "completed", "usage": {"input_tokens": 10, "output_tokens": 10},
                "output": [{"type": "message", "content": [{"type": "output_text", "text": self.response}]}]}


class Activity:
    def __init__(self):
        self.events = []

    def write(self, *event):
        self.events.append(event)


class InstructionProposalTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.config = {"ai-model": {"name": MODEL, "api-key": "secret-key"},
                       "credentials": {"user": {"password": "secret-password"}}}
        self.redactor = Redactor(self.config)
        self.budget = Budget(MODEL, 5, "USD")
        self.transport = Transport(json.dumps({"instructions": "Check field", "setup": "Open settings",
                                                "evidence": "Screen observed"}))
        self.agent = Agent(self.config, self.budget, time.time() + 60, transport=self.transport)
        self.control = RunControl(time.time() + 60)
        self.activity = Activity()

    def create(self, results=None):
        proposal = InstructionProposal(self.folder.name, {"instructions": "secret-password", "setup": "Original"},
                                       results if results is not None else [{"index": 1, "observation": "secret-password"}],
                                       self.redactor, self.control, self.agent, self.activity)
        proposal.create()
        return pathlib.Path(self.folder.name, "instruction-setup-proposal.md").read_text()

    def test_saves_separate_sections_and_redacts_request(self):
        output = self.create()
        self.assertIn("## Proposed instructions\n\nCheck field", output)
        self.assertIn("## Proposed setup\n\nOpen settings", output)
        self.assertIn("Screen observed", output)
        self.assertNotIn("secret-password", json.dumps(self.transport.calls))
        self.assertEqual(self.budget.snapshot()["requests"], 1)
        self.assertEqual(self.budget.snapshot()["requestUsage"][0]["kind"], "instruction proposal")

    def test_exhausted_budget_records_reason_without_request(self):
        self.budget.limit = 0
        output = self.create()
        self.assertIn("No AI proposal was generated", output)
        self.assertIn("budget", output)
        self.assertEqual(self.transport.calls, [])

    def test_interruption_records_reason_without_request(self):
        self.control.interrupt()
        output = self.create()
        self.assertIn("interrupted", output)
        self.assertEqual(self.transport.calls, [])

    def test_invalid_response_records_failure(self):
        self.transport.response = "not JSON"
        output = self.create()
        self.assertIn("not valid JSON", output)
        self.assertEqual(self.activity.events[-1][1], "failed")


if __name__ == "__main__":
    unittest.main()
