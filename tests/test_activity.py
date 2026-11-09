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
from stopping_policy.policy import result_exit_code
from errors import AppLaunchError, InfrastructureError, LimitReached
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
        self.activity.interrupted = lambda: control.interrupted
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
        self.assertNotIn('failed', [row['status'] for row in self.records()])
        self.assertNotIn('helper stopped', self.output.getvalue())

    def test_interrupted_nested_operations_report_a_stop_instead_of_pipe_failures(self):
        self.activity.interrupted = lambda: True
        with self.assertRaisesRegex(LimitReached, 'User interrupted'):
            with self.activity.operation('Capture screenshot'):
                with self.activity.operation('Read UI'):
                    raise BrokenPipeError('Broken pipe')
        stopped = [row for row in self.records() if row['status'] != 'started']
        self.assertEqual([row['status'] for row in stopped], ['stopped', 'stopped'])
        self.assertNotIn('Broken pipe', self.output.getvalue())

    def test_pipe_failure_without_interruption_remains_a_failure(self):
        with self.assertRaises(BrokenPipeError):
            with self.activity.operation('Read UI'):
                raise BrokenPipeError('Broken pipe')
        self.assertEqual(self.records()[-1]['status'], 'failed')
        self.assertEqual(self.records()[-1]['exceptionType'], 'BrokenPipeError')

    def test_successful_cleanup_is_still_completed_after_interruption(self):
        self.activity.interrupted = lambda: True
        with self.activity.operation('Close device connection'):
            pass
        self.assertEqual(self.records()[-1]['status'], 'completed')

    def test_a_saved_failure_is_not_reclassified_after_interruption(self):
        with self.assertRaises(InfrastructureError):
            with self.activity.operation('Install application'):
                raise InfrastructureError('Install failed')
        self.activity.interrupted = lambda: True
        with self.assertRaises(LimitReached):
            with self.activity.operation('Close device connection'):
                raise BrokenPipeError('Broken pipe')
        finished = [row for row in self.records() if row['status'] != 'started']
        self.assertEqual([row['status'] for row in finished], ['failed', 'stopped'])
        self.assertEqual(finished[0]['message'], 'Install failed')

    def test_interrupted_close_failure_publishes_partial_observations_and_original_verdict(self):
        control = RunControl(100, clock=lambda: 0)
        self.activity.interrupted = lambda: control.interrupted
        journal = RunJournal(self.root, self.redactor, SimpleNamespace(snapshot=lambda: {}))

        def observe_failure(mobile, build, result, agent, publish):
            result['scenarios'].append({'target': 'fixture', 'crashes': [],
                'verdict': 'failed', 'completion': 'incomplete', 'steps': [{'step': 0}]})
            control.interrupt()
            control.check()

        def close():
            raise BrokenPipeError('Broken pipe')

        mobile = SimpleNamespace(connect=lambda: None, close=close, device=self.device)
        runner = DeviceRunner({'report': str(self.root), 'builds': [{'platform': 'android', 'target': 'fixture'}]},
            self.redactor, control, journal, SimpleNamespace(run=observe_failure), lambda *args: mobile,
            lambda: None, activity=self.activity)
        runner.run(self.device, 1)
        saved = json.loads((self.root / 'ui-results.json').read_text())['devices'][0]
        self.assertEqual(saved['scenarios'][0]['steps'], [{'step': 0}])
        self.assertIsNone(saved['error'])
        self.assertIn('User interrupted', saved['stoppingReason'])
        self.assertEqual(result_exit_code([saved]), 1)
        self.assertNotIn('failed', [row['status'] for row in self.records()])

    def test_close_failure_without_interruption_is_saved_as_infrastructure_error(self):
        journal = RunJournal(self.root, self.redactor, SimpleNamespace(snapshot=lambda: {}))

        def close():
            raise BrokenPipeError('Broken pipe')

        mobile = SimpleNamespace(connect=lambda: None, close=close, device=self.device)
        runner = DeviceRunner({'report': str(self.root), 'builds': []}, self.redactor,
            RunControl(100, clock=lambda: 0), journal, None, lambda *args: mobile,
            lambda: None, activity=self.activity)
        runner.run(self.device, 1)
        saved = json.loads((self.root / 'ui-results.json').read_text())['devices'][0]
        self.assertIn('BrokenPipeError', saved['error'])
        self.assertEqual(result_exit_code([saved]), 3)

    def test_cleanup_failure_does_not_replace_the_original_device_error(self):
        journal = RunJournal(self.root, self.redactor, SimpleNamespace(snapshot=lambda: {}))

        def connect():
            raise InfrastructureError('Original connection failure')

        def close():
            raise BrokenPipeError('Cleanup pipe failure')

        mobile = SimpleNamespace(connect=connect, close=close, device=self.device)
        runner = DeviceRunner({'report': str(self.root), 'builds': []}, self.redactor,
            RunControl(100, clock=lambda: 0), journal, None, lambda *args: mobile,
            lambda: None, activity=self.activity)
        runner.run(self.device, 1)
        saved = json.loads((self.root / 'ui-results.json').read_text())['devices'][0]
        self.assertEqual(saved['error'], 'Original connection failure')
        self.assertIn('Cleanup pipe failure', self.output.getvalue())

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

    def test_failed_launch_does_not_cancel_testing_on_the_other_platform(self):
        for failed_platform, continuing_platform in [('ios', 'android'), ('android', 'ios')]:
            with self.subTest(failed_platform=failed_platform):
                control = RunControl(100, clock=lambda: 0)
                journal = RunJournal(self.root, self.redactor, SimpleNamespace(snapshot=lambda: {}))

                def test_target(mobile, build, result, agent, publish):
                    control.check()
                    result['scenarios'].append(dict(target='fixture', crashes=[], steps=[],
                        verdict='inconclusive', completion='incomplete'))
                    if mobile.device['platform'] == failed_platform:
                        raise AppLaunchError('Application relaunch failed')
                    result['scenarios'][-1].update(verdict='passed', completion='complete')

                def mobile(device, folder):
                    return SimpleNamespace(device=device, connect=lambda: None, close=lambda: None)

                builds = [dict(platform=platform, target='fixture') for platform in ['ios', 'android']]
                runner = DeviceRunner(dict(report=str(self.root), builds=builds), self.redactor,
                    control, journal, SimpleNamespace(run=test_target), mobile, lambda: None,
                    activity=self.activity)
                runner.run(dict(platform=failed_platform, id='failed-device'), 1)
                runner.run(dict(platform=continuing_platform, id='continuing-device'), 2)

                failed, continued = sorted(journal.results, key=lambda row: row['index'])
                self.assertEqual(failed['error'], 'Application relaunch failed')
                self.assertEqual(continued['scenarios'][0]['completion'], 'complete')
                self.assertIsNone(continued['error'])
                self.assertIsNone(continued['stoppingReason'])
                self.assertFalse(control.stopped.is_set())
                self.assertEqual(result_exit_code(journal.results), 3)

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
