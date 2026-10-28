"""A worker keeps the identity supplied by the host. No device or API is used."""

import json
import pathlib
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "runtime"))

from evidence import RunJournal
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


if __name__ == "__main__":
    unittest.main()
