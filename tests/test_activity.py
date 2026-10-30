"""Activity tests use local files and fake device operations only."""

from concurrent.futures import ThreadPoolExecutor
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "runtime"))
from activity import ActivityLog
from device_runner import DeviceRunner
from errors import InfrastructureError, LimitReached
from evidence import RunJournal
from redaction import Redactor
from run_control import RunControl
from run_signals import RunSignals
import signal


class ActivityTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.output = io.StringIO()
        self.redactor = Redactor({"ai-model": {"api-key": "synthetic-secret"}})
        self.activity = ActivityLog(self.root, self.redactor, self.output)
        self.device = {"platform": "android", "id": "fixture-phone"}

    def records(self):
        return [json.loads(line) for line in (self.root / "activity.jsonl").read_text().splitlines()]

    def test_stop_marker_is_a_user_interruption(self):
        marker = self.root / 'stop-requested'
        control = RunControl(100, clock=lambda: 0, stop_file=marker)
        marker.write_text('User interruption')
        with self.assertRaisesRegex(LimitReached, 'User interrupted'):
            control.check()

    def test_interrupt_signal_sets_stop_flag_and_restores_previous_handler(self):
        control = RunControl(100, clock=lambda: 0)
        before = signal.getsignal(signal.SIGINT)
        with RunSignals(control):
            signal.raise_signal(signal.SIGINT)
            self.assertTrue(control.interrupted)
        self.assertEqual(signal.getsignal(signal.SIGINT), before)

    def test_interrupted_adapter_error_is_saved_as_user_stop(self):
        control = RunControl(100, clock=lambda: 0)
        journal = RunJournal(self.root, self.redactor, SimpleNamespace(snapshot=lambda: {}))
        def interrupted_connect():
            control.interrupt()
            raise BrokenPipeError('helper stopped')
        mobile = SimpleNamespace(connect=interrupted_connect, close=lambda: None, device=self.device)
        runner = DeviceRunner({'report': str(self.root), 'builds': []}, self.redactor, control,
            journal, None, lambda *args: mobile, lambda: None, activity=self.activity)
        runner.run(self.device, 1)
        result = journal.results[0]
        self.assertIsNone(result['error'])
        self.assertIn('User interrupted', result['stoppingReason'])

    def test_completed_operation_records_duration_and_context(self):
        ticks = iter([10, 12.25])
        self.activity.clock = lambda: next(ticks)
        with self.activity.operation("Install application", self.device, "Debug_Generic"):
            pass
        started, finished = self.records()
        self.assertEqual(started["status"], "started")
        self.assertEqual(finished["status"], "completed")
        self.assertEqual(finished["durationSeconds"], 2.25)
        self.assertEqual(finished["target"], "Debug_Generic")
        self.assertEqual(finished["device"], "fixture-phone")

    def test_failure_preserves_exception_and_redacts_saved_and_terminal_text(self):
        error = InfrastructureError("capture synthetic-secret failed")
        with self.assertRaises(InfrastructureError) as raised:
            with self.activity.operation("Capture", self.device):
                raise error
        self.assertIs(raised.exception, error)
        failed = self.records()[-1]
        self.assertEqual(failed["status"], "failed")
        self.assertEqual(failed["exceptionType"], "InfrastructureError")
        self.assertIn("test_activity.py:", failed["details"])
        self.assertNotIn("synthetic-secret", (self.root / "activity.jsonl").read_text())
        self.assertNotIn("synthetic-secret", self.output.getvalue())

    def test_other_worker_stop_is_recorded_as_cancellation(self):
        with self.assertRaises(LimitReached):
            with self.activity.operation("Execute target", self.device):
                raise LimitReached("Run stopped after another worker reached a blocking condition")
        self.assertEqual(self.records()[-1]["status"], "cancelled")

    def test_time_limit_is_a_stop_and_keeps_its_reason(self):
        with self.assertRaises(LimitReached):
            with self.activity.operation("Request AI action", self.device):
                raise LimitReached("Whole-run time limit reached")
        self.assertEqual(self.records()[-1]["status"], "stopped")
        self.assertIn("time limit", self.records()[-1]["message"])

    def test_two_workers_write_complete_independent_records(self):
        def record(index):
            self.activity.write("Fixture operation", "completed", device=self.device, target=str(index))
        with ThreadPoolExecutor(max_workers=2) as workers:
            list(workers.map(record, range(12)))
        self.assertEqual(len(self.records()), 12)
        self.assertEqual({row["target"] for row in self.records()}, {str(i) for i in range(12)})

    def test_device_failure_is_saved_and_explained_without_stderr_exception(self):
        control = RunControl(100, clock=lambda: 0)
        journal = RunJournal(self.root, self.redactor, SimpleNamespace(snapshot=lambda: {"requests": 0}))
        mobile = SimpleNamespace(connect=lambda: None, close=lambda: None, device=self.device)

        def fail(*args):
            raise InfrastructureError("Required mask geometry changed during screenshot capture")

        runner = DeviceRunner({"report": str(self.root), "builds": [{"target": "Debug_Generic", "platform": "android"}]},
            self.redactor, control, journal, SimpleNamespace(run=fail), lambda *args: mobile,
            lambda: object(), activity=self.activity)
        runner.run(self.device, 1)
        result = json.loads((self.root / "ui-results.json").read_text())["devices"][0]
        self.assertIn("mask geometry changed", result["error"])
        self.assertIn("mask geometry changed", self.output.getvalue())
        self.assertTrue(control.stopped.is_set())
        self.assertTrue(any(row["target"] == "Debug_Generic" and row["status"] == "failed" for row in self.records()))

    def test_adapter_setup_failure_is_logged_before_device_execution_starts(self):
        journal = RunJournal(self.root, self.redactor, SimpleNamespace(snapshot=lambda: {}))

        def fail(*args):
            raise InfrastructureError("Adapter setup failed synthetic-secret")

        runner = DeviceRunner({"report": str(self.root), "builds": []}, self.redactor,
            RunControl(100, clock=lambda: 0), journal, None, fail, lambda: object(), activity=self.activity)
        with self.assertRaises(InfrastructureError):
            runner.run(self.device, 1)
        failed = self.records()[-1]
        self.assertEqual(failed["operation"], "Prepare device adapter")
        self.assertEqual(failed["status"], "failed")
        self.assertIn("Adapter setup failed", failed["message"])
        self.assertNotIn("synthetic-secret", self.output.getvalue())


if __name__ == "__main__":
    unittest.main()
