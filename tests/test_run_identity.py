"""A worker keeps the identity supplied by the host. No device or API is used."""

import io
import json
import pathlib
import sys
import tempfile
import unittest
from contextlib import redirect_stderr

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "runtime"))

from evidence import RunJournal
from run_ui import main
from runtime_protocol import read_request
from redaction import Redactor


class BudgetFixture:
    def snapshot(self):
        return {"requests": 0}


class RunIdentityTests(unittest.TestCase):
    def test_worker_results_keep_the_host_identity(self):
        with tempfile.TemporaryDirectory() as folder:
            journal = RunJournal(folder, Redactor({}), BudgetFixture(), "2026-10-28_14-30-00-123")
            journal.save()
            data = json.loads(pathlib.Path(folder, "ui-results.json").read_text())
            self.assertEqual(data["runId"], "2026-10-28_14-30-00-123")
            self.assertEqual(data["devices"], [])
            self.assertEqual(data["protocolVersion"], 1)

    def test_worker_accepts_current_and_legacy_request_envelopes(self):
        request = dict(config={}, report="/fixture", deadline=100, inputs={}, devices=[], builds=[])
        for value in (request, dict(request, protocolVersion=1)):
            with self.subTest(value=value):
                self.assertEqual(read_request(io.StringIO(json.dumps(value))), value)

    def test_worker_rejects_an_unknown_protocol_before_constructing_services(self):
        error = io.StringIO()
        with redirect_stderr(error):
            self.assertEqual(main(io.StringIO('{"protocolVersion":2}'), ['--preflight']), 3)
        self.assertIn('install matching TestPilot host and runtime', error.getvalue())


if __name__ == "__main__":
    unittest.main()
