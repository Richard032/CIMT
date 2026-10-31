"""Small policy tests. These tests do not use phones, threads, or an API."""

import pathlib
import subprocess
import sys
import time
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "runtime"))

from check_results import scenario_verdict, validate_checks
from device_commands import NativeDevice
from device_scheduler import DeviceScheduler
from errors import AppLaunchError, DeviceLocked, InfrastructureError, LimitReached
from redaction import Redactor
from stopping_policy.policy import matching_crash_limit_reached, stops_entire_run


def check(status="passed", source="instructions"):
    return {
        "taskId": 0,
        "subject": "Save setting",
        "source": source,
        "status": status,
        "expected": "Value stays saved",
        "observed": "Value is visible",
        "reason": "",
        "requirementId": "REQ-0001" if source == "requirements" else "",
        "instructionQuote": "",
    }


class StoppingPolicyTests(unittest.TestCase):
    def test_launch_failure_stops_only_the_affected_device(self):
        self.assertFalse(stops_entire_run(AppLaunchError('Could not launch the app')))

    def test_locked_device_does_not_stop_other_devices(self):
        self.assertFalse(stops_entire_run(DeviceLocked('Unlock this device')))

    def test_budget_deadline_and_user_interruption_stop_the_whole_run(self):
        for reason in ['AI budget exhausted', 'Whole-run time limit reached', 'User interrupted']:
            with self.subTest(reason=reason):
                self.assertTrue(stops_entire_run(LimitReached(reason)))

    def test_error_text_cannot_change_the_stopping_scope(self):
        self.assertTrue(stops_entire_run(LimitReached('Shared resource is locked')))

    def test_shared_infrastructure_failure_stops_the_whole_run(self):
        self.assertTrue(stops_entire_run(InfrastructureError('AI service unavailable')))

    def test_third_matching_crash_stops_the_scenario(self):
        for attempts in [1, 2]:
            self.assertFalse(matching_crash_limit_reached(attempts))
        for attempts in [3, 4]:
            self.assertTrue(matching_crash_limit_reached(attempts))


class CheckResultTests(unittest.TestCase):
    def test_observed_functional_failure_is_failed(self):
        self.assertEqual(scenario_verdict([check("failed")], False, True), "failed")

    def test_failure_survives_a_later_pass(self):
        self.assertEqual(scenario_verdict([check("failed"), check()], False, True), "failed")

    def test_failure_survives_incomplete_exploration(self):
        self.assertEqual(scenario_verdict([check("failed")], False, False), "failed")

    def test_crash_is_failed_without_any_check(self):
        self.assertEqual(scenario_verdict([], True, False), "failed")

    def test_finished_navigation_without_checks_is_inconclusive(self):
        self.assertEqual(scenario_verdict([], False, True), "inconclusive")

    def test_an_explicit_objective_check_can_pass(self):
        self.assertEqual(scenario_verdict([check()], False, True), "passed")

    def test_requirement_checks_alone_do_not_prove_the_objective(self):
        self.assertEqual(
            scenario_verdict([check(source="requirements")], False, True), "inconclusive"
        )

    def test_unresolved_check_prevents_a_pass(self):
        for status in ["not tested", "inconclusive"]:
            with self.subTest(status=status):
                unresolved = dict(check(status), reason="Screen is unavailable")
                self.assertEqual(
                    scenario_verdict([check(), unresolved], False, True), "inconclusive"
                )

    def test_later_evidence_can_resolve_an_unknown_check(self):
        unknown = dict(check("inconclusive"), reason="Value is not visible yet")
        self.assertEqual(scenario_verdict([unknown, check()], False, True), "passed")

    def test_decided_check_needs_observed_evidence(self):
        with self.assertRaises(InfrastructureError):
            validate_checks([dict(check(), observed="")])

    def test_unresolved_check_needs_a_reason(self):
        with self.assertRaises(InfrastructureError):
            validate_checks([check("not tested")])

    def test_instruction_cannot_be_overridden(self):
        with self.assertRaises(InfrastructureError):
            validate_checks([dict(check("overridden"), reason="Conflicting request")])

    def test_requirement_can_be_overridden_with_a_reason(self):
        overridden = dict(
            check("overridden", "requirements"),
            reason="Instructions take priority",
            instructionQuote="Explore only",
        )
        validate_checks([overridden])
        self.assertEqual(scenario_verdict([check(), overridden], False, True), "passed")


class RecordingExecutor:
    """Run submitted jobs in order and record the requested worker limit."""

    def __init__(self):
        self.jobs = []
        self.maximum = None

    def __call__(self, jobs, run_job, maximum_active):
        self.jobs = jobs
        self.maximum = maximum_active
        for job in jobs:
            run_job(job)


class RecordingWorker:
    def __init__(self):
        self.calls = []

    def run(self, device, index):
        self.calls.append((device, index))


class SchedulingTests(unittest.TestCase):
    def setUp(self):
        self.executor = RecordingExecutor()
        self.worker = RecordingWorker()
        self.scheduler = DeviceScheduler(self.executor)

    def test_no_devices_does_not_start_an_executor(self):
        self.scheduler.run([], self.worker)
        self.assertIsNone(self.executor.maximum)
        self.assertEqual(self.worker.calls, [])

    def test_one_device_is_submitted_once(self):
        self.scheduler.run(["phone-a"], self.worker)
        self.assertEqual(self.worker.calls, [("phone-a", 1)])

    def test_two_devices_use_a_two_worker_limit(self):
        self.scheduler.run(["phone-a", "phone-b"], self.worker)
        self.assertEqual(self.executor.maximum, 2)
        self.assertEqual(self.worker.calls, [("phone-a", 1), ("phone-b", 2)])

    def test_third_device_is_queued_with_the_same_limit(self):
        self.scheduler.run(["phone-a", "phone-b", "phone-c"], self.worker)
        self.assertEqual(self.executor.maximum, 2)
        self.assertEqual(self.worker.calls, [("phone-a", 1), ("phone-b", 2), ("phone-c", 3)])


class NativeCommandFixture:
    """Return one process result, or raise a configured command error."""

    def __init__(self, result=None, error=None):
        self.result = result
        self.error = error

    def __call__(self, arguments, **options):
        if self.error:
            raise self.error
        return self.result


class NativeCommandTests(unittest.TestCase):
    def native(self, result=None, error=None):
        redactor = Redactor({"ai-model": {"api-key": "synthetic-secret"}})
        return NativeDevice(
            "unused",
            {"id": "fixture"},
            {"nativeHome": "/unused", "deadline": time.time() + 30},
            redactor,
            NativeCommandFixture(result, error),
        )

    def test_success_returns_json(self):
        result = subprocess.CompletedProcess([], 0, '{"data": []}', "")
        self.assertEqual(self.native(result).native(["device", "info"]), {"data": []})

    def test_nonzero_exit_reports_a_redacted_error(self):
        result = subprocess.CompletedProcess([], 1, "", "failed synthetic-secret")
        with self.assertRaises(InfrastructureError) as raised:
            self.native(result).native([])
        self.assertNotIn("synthetic-secret", str(raised.exception))
        self.assertIn("failed", str(raised.exception))

    def test_invalid_json_is_an_infrastructure_error(self):
        with self.assertRaisesRegex(InfrastructureError, "invalid JSON"):
            self.native(subprocess.CompletedProcess([], 0, "invalid", "")).native([])

    def test_timeout_is_an_infrastructure_error(self):
        with self.assertRaisesRegex(InfrastructureError, "timed out"):
            self.native(error=subprocess.TimeoutExpired("unused", 1)).native([])


if __name__ == "__main__":
    unittest.main()
