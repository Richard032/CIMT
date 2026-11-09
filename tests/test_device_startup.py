"""Startup recovery uses a fake clock and never operates a real device."""

import ast
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'runtime'))
from device_adapter.mobile import Mobile
from device_adapter.app_lifecycle import AppLifecycle
from run_control import RunControl
from device_adapter.startup import DeviceStartup
from errors import DeviceCommandTimeout, DeviceLocked, DeviceServerStartupError, InfrastructureError, LimitReached
from redaction import Redactor


class Clock:
    def __init__(self):
        self.now = 0

    def __call__(self):
        return self.now

    def sleep(self, seconds):
        self.now += seconds


class LaunchWaitTests(unittest.TestCase):
    def setUp(self):
        self.clock = Clock()
        self.control = RunControl(100, clock=self.clock)
        self.lifecycle = AppLifecycle(SimpleNamespace(), lambda *args, **kwargs: None,
            check=self.control.check, clock=self.clock, sleep=self.clock.sleep)

    def test_newly_installed_app_gets_twenty_seconds_before_testing(self):
        self.lifecycle.wait_after_launch()
        self.assertAlmostEqual(self.clock.now, 20)

    def test_cancel_before_the_wait_does_not_sleep(self):
        self.control.interrupt()
        with self.assertRaisesRegex(LimitReached, 'User interrupted'):
            self.lifecycle.wait_after_launch()
        self.assertEqual(self.clock.now, 0)

    def test_cancellation_during_the_wait_ends_it_before_twenty_seconds(self):
        def sleep(seconds):
            self.clock.sleep(seconds)
            self.control.interrupt()
        self.lifecycle.sleep = sleep
        with self.assertRaisesRegex(LimitReached, 'User interrupted'):
            self.lifecycle.wait_after_launch()
        self.assertLessEqual(self.clock.now, 0.1)

    def test_run_deadline_stops_the_wait(self):
        self.control.deadline = 0.25
        with self.assertRaisesRegex(LimitReached, 'Whole-run time limit'):
            self.lifecycle.wait_after_launch()
        self.assertLessEqual(self.clock.now, 0.35)

    def test_another_workers_stop_prevents_further_waiting(self):
        self.control.stop()
        with self.assertRaisesRegex(LimitReached, 'another worker'):
            self.lifecycle.wait_after_launch()
        self.assertEqual(self.clock.now, 0)


class ProbeCommands:
    def __init__(self, clock, outcomes=None):
        self.clock = clock
        self.outcomes = list(outcomes or [])
        self.calls = []

    def native(self, arguments, timeout):
        self.calls.append((arguments, timeout))
        outcome = self.outcomes.pop(0) if self.outcomes else DeviceServerStartupError('helper startup failed')
        self.clock.sleep(min(5, timeout))
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


class StartupTests(unittest.TestCase):
    def setUp(self):
        self.clock = Clock()

    def startup(self, commands, deadline=200, **options):
        return DeviceStartup(commands, deadline, clock=self.clock, sleep=self.clock.sleep, **options)

    def test_first_success_needs_only_one_read_only_probe(self):
        commands = ProbeCommands(self.clock, [{'data': []}])
        self.startup(commands).wait()
        self.assertEqual(commands.calls, [(['apps', 'list'], 30)])

    def test_known_startup_failure_can_recover_without_an_app_action(self):
        commands = ProbeCommands(self.clock, [DeviceServerStartupError('startup failed'), {'data': []}])
        retries = []
        self.startup(commands, on_retry=lambda *values: retries.append(values)).wait()
        self.assertEqual([args for args, _ in commands.calls], [['apps', 'list'], ['apps', 'list']])
        self.assertEqual(len(retries), 1)
        self.assertEqual(retries[0][0], 1)
        self.assertEqual(retries[0][2], 85)

    def test_repeated_startup_failure_stops_at_ninety_seconds(self):
        commands = ProbeCommands(self.clock)
        with self.assertRaisesRegex(DeviceServerStartupError, '90 seconds.*read-only probes.*startup failed'):
            self.startup(commands).wait()
        self.assertAlmostEqual(self.clock.now, 90)
        self.assertTrue(all(args == ['apps', 'list'] for args, _ in commands.calls))

    def test_run_deadline_shorter_than_the_window_wins(self):
        commands = ProbeCommands(self.clock)
        with self.assertRaisesRegex(LimitReached, 'Whole-run time limit'):
            self.startup(commands, deadline=12).wait()
        self.assertAlmostEqual(self.clock.now, 12)

    def test_probe_timeout_is_clipped_to_the_available_window(self):
        commands = ProbeCommands(self.clock, [{'data': []}])
        self.startup(commands, deadline=10).wait()
        self.assertEqual(commands.calls[0][1], 10)

    def test_cancel_before_probe_does_not_call_the_helper(self):
        commands = ProbeCommands(self.clock)
        def cancel():
            raise LimitReached('User interrupted')
        with self.assertRaisesRegex(LimitReached, 'User interrupted'):
            self.startup(commands, check=cancel).wait()
        self.assertEqual(commands.calls, [])

    def test_cancel_during_retry_wait_prevents_another_probe(self):
        commands = ProbeCommands(self.clock)
        def cancel():
            if self.clock.now > 5:
                raise LimitReached('User interrupted')
        with self.assertRaisesRegex(LimitReached, 'User interrupted'):
            self.startup(commands, check=cancel).wait()
        self.assertEqual(len(commands.calls), 1)
        self.assertLess(self.clock.now, 6)

    def test_cancel_after_success_is_observed_before_app_setup(self):
        commands = ProbeCommands(self.clock, [{'data': []}])
        def cancel():
            if self.clock.now >= 5:
                raise LimitReached('Another worker stopped')
        with self.assertRaisesRegex(LimitReached, 'Another worker stopped'):
            self.startup(commands, check=cancel).wait()

    def test_generic_infrastructure_error_is_not_retried(self):
        commands = ProbeCommands(self.clock, [InfrastructureError('connection lost')])
        with self.assertRaisesRegex(InfrastructureError, 'connection lost'):
            self.startup(commands).wait()
        self.assertEqual(len(commands.calls), 1)

    def test_device_lock_is_not_retried(self):
        commands = ProbeCommands(self.clock, [DeviceLocked('locked')])
        with self.assertRaises(DeviceLocked):
            self.startup(commands).wait()
        self.assertEqual(len(commands.calls), 1)

    def test_generic_command_timeout_is_not_retried(self):
        commands = ProbeCommands(self.clock, [DeviceCommandTimeout('command timed out')])
        with self.assertRaisesRegex(DeviceCommandTimeout, 'command timed out'):
            self.startup(commands).wait()
        self.assertEqual(len(commands.calls), 1)

    def test_final_clipped_command_reports_startup_window_exhaustion(self):
        class ClippedCommands(ProbeCommands):
            def native(self, arguments, timeout):
                self.calls.append((arguments, timeout))
                self.clock.sleep(min(7, timeout))
                if timeout < 7:
                    raise DeviceCommandTimeout('command timed out')
                raise DeviceServerStartupError('helper startup failed')
        commands = ClippedCommands(self.clock)
        with self.assertRaisesRegex(DeviceServerStartupError, '90 seconds.*command timed out'):
            self.startup(commands).wait()
        self.assertAlmostEqual(self.clock.now, 90)

    def test_invalid_inventory_is_not_treated_as_ready_or_retried(self):
        commands = ProbeCommands(self.clock, [{'data': 'invalid'}])
        with self.assertRaisesRegex(InfrastructureError, 'invalid app inventory'):
            self.startup(commands).wait()
        self.assertEqual(len(commands.calls), 1)

    def test_adapter_layer_does_not_import_ai_or_stopping_policy(self):
        forbidden = {'agent', 'actions', 'scenario', 'run_ui', 'test_planning', 'ai_instructions', 'stopping_policy'}
        for path in (Path(__file__).resolve().parents[1] / 'runtime/device_adapter').glob('*.py'):
            for node in ast.walk(ast.parse(path.read_text())):
                if isinstance(node, ast.Import):
                    self.assertFalse({item.name.split('.')[0] for item in node.names} & forbidden)
                elif isinstance(node, ast.ImportFrom) and node.level == 0:
                    self.assertNotIn((node.module or '').split('.')[0], forbidden)


class ConnectionTests(unittest.TestCase):
    def mobile(self, folder, events, error=None, check=lambda: None):
        def probe(arguments, timeout):
            events.append(('probe', arguments))
            if error:
                raise error
            return {'data': []}
        def lock_query(arguments, **options):
            events.append(('lock', arguments))
            return subprocess.CompletedProcess(arguments, 0, 'showing=false\n', '')
        def client(*arguments):
            events.append(('mcp', None))
            return SimpleNamespace(close=lambda: None)
        commands = SimpleNamespace(device={'platform': 'android', 'id': 'fixture'},
            context={}, run_command=lock_query, native=probe, env={}, screenshot=lambda: b'')
        return Mobile('helper', commands.device, Path(folder), {'deadline': 99999999999},
                      Redactor({}), commands=commands, client_factory=client, check=check)

    def test_launch_wait_uses_the_executions_shared_stop_check(self):
        def cancel():
            raise LimitReached('User interrupted')
        with tempfile.TemporaryDirectory() as folder:
            mobile = self.mobile(folder, [], check=cancel)
            with self.assertRaisesRegex(LimitReached, 'User interrupted'):
                mobile.lifecycle.wait_after_launch()

    def test_successful_app_setup_waits_before_returning_to_screen_checks(self):
        with tempfile.TemporaryDirectory() as folder:
            events = []
            mobile = self.mobile(folder, events)
            mobile.lifecycle = SimpleNamespace(
                reset=lambda *args: events.append(('install/reset/launch', None)),
                wait_after_launch=lambda: events.append(('wait', 20)))
            mobile.reset('fixture.apk', 'com.example.app', 'Debug')
            events.append(('screen/startup checks can begin', None))
        self.assertEqual([kind for kind, _ in events],
            ['install/reset/launch', 'wait', 'screen/startup checks can begin'])
        self.assertEqual(mobile.app_id, 'com.example.app')

    def test_failed_app_setup_does_not_wait(self):
        def fail(*args):
            raise InfrastructureError('Launch failed')
        with tempfile.TemporaryDirectory() as folder:
            events = []
            mobile = self.mobile(folder, events)
            mobile.lifecycle = SimpleNamespace(reset=fail,
                wait_after_launch=lambda: events.append(('wait', 20)))
            with self.assertRaisesRegex(InfrastructureError, 'Launch failed'):
                mobile.reset('fixture.apk', 'com.example.app', 'Debug')
        self.assertEqual(events, [])

    def test_readiness_probe_precedes_mcp_and_rechecks_lock(self):
        with tempfile.TemporaryDirectory() as folder:
            events = []
            self.mobile(folder, events).connect()
        self.assertEqual([kind for kind, _ in events], ['lock', 'probe', 'lock', 'mcp'])

    def test_failed_probe_never_connects_mcp_or_starts_app_setup(self):
        with tempfile.TemporaryDirectory() as folder:
            events = []
            with self.assertRaisesRegex(InfrastructureError, 'invalid helper'):
                self.mobile(folder, events, InfrastructureError('invalid helper')).connect()
        self.assertEqual([kind for kind, _ in events], ['lock', 'probe'])
