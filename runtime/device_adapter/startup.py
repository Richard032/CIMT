"""Retry only a read-only startup probe before any application action."""

import time
from errors import DeviceCommandTimeout, DeviceServerStartupError, InfrastructureError, LimitReached


class DeviceStartup:
    """Owns a bounded readiness window, not app actions or stopping scope."""

    WINDOW_SECONDS = 90
    RETRY_DELAY_SECONDS = 1

    def __init__(self, commands, deadline, check=lambda: None, clock=time.time,
                 sleep=time.sleep, on_retry=None):
        self.commands = commands
        self.deadline = deadline
        self.check = check
        self.clock = clock
        self.sleep = sleep
        self.on_retry = on_retry

    def wait(self):
        until = min(self.deadline, self.clock() + self.WINDOW_SECONDS)
        attempts = 0
        last_error = None
        while True:
            remaining = self._remaining(until, attempts, last_error)
            attempts += 1
            try:
                # Keep the probe fixed: never retry a caller-supplied app action.
                inventory = self.commands.native(["apps", "list"], timeout=min(30, remaining))
            except DeviceServerStartupError as error:
                last_error = error
            except DeviceCommandTimeout as error:
                # A final clipped probe can reach the window's end in flight.
                # Other command timeouts are not startup failures to retry.
                if last_error is not None and self.clock() >= until:
                    self._remaining(until, attempts, error)
                raise
            else:
                self._remaining(until, attempts, last_error)
                if not isinstance(inventory, dict) or not isinstance(inventory.get("data"), list):
                    raise InfrastructureError("Device startup probe returned an invalid app inventory")
                return
            remaining = self._remaining(until, attempts, last_error)
            if self.on_retry:
                self.on_retry(attempts, last_error, remaining)
            self._pause(min(until, self.clock() + self.RETRY_DELAY_SECONDS))

    def _remaining(self, until, attempts, error):
        self.check()
        now = self.clock()
        if now >= self.deadline:
            raise LimitReached("Whole-run time limit reached")
        if now >= until:
            message = ("Device adapter startup did not become ready within "
                       + str(self.WINDOW_SECONDS) + " seconds after " + str(attempts)
                       + " read-only probes. Last failure: " + str(error))
            raise DeviceServerStartupError(message) from error
        return until - now

    def _pause(self, until):
        # Short waits let cancellation stop recovery without another probe.
        while self.clock() < until:
            self.check()
            self.sleep(min(0.1, until - self.clock()))
