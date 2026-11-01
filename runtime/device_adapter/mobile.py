"""Device adapter facade. Each service below owns a separate responsibility."""

from .app_lifecycle import AppLifecycle
from .native import NativeDevice
from .readiness import DeviceReadiness
from .status import DeviceStatus
from .startup import DeviceStartup
from .mcp_client import Mcp
from redaction import ScreenMasker
from .screen_capture import ScreenCapture
from contextlib import nullcontext


class Mobile:
    """Exposes the device operations needed by a scenario."""

    def __init__(
        self, binary, device, folder, context, redactor, commands=None, client_factory=Mcp,
        activity=None, check=lambda: None,
    ):
        self.device = device
        self.folder = folder
        self.context = context
        self.redactor = redactor
        self.activity = activity
        self.check = check
        self.target = ""
        self.app_id = ""
        self.commands = commands or NativeDevice(binary, device, context, redactor)
        self.guard = DeviceReadiness(self.commands, folder)
        self.status = DeviceStatus(self.commands, folder)
        self.lifecycle = AppLifecycle(self.commands, self.call, check=self.check)
        self.screen = ScreenCapture(
            self.call,
            self.commands.native,
            self.readiness,
            redactor,
            ScreenMasker(redactor),
            image_reader=self.commands.screenshot,
            deadline=context.get("deadline"),
            on_retry=self._capture_retry,
        )
        self.client_factory = client_factory
        self.client = None

    def connect(self):
        """Check the device lock before starting its MCP connection."""
        self.check()
        self.readiness()
        with self._operation("Check device adapter startup"):
            DeviceStartup(self.commands, self.context["deadline"], self.check,
                          on_retry=self._startup_retry).wait()
        self.readiness()
        self.check()
        self.client = self.client_factory(
            self.folder, self.commands.env, self.redactor, self.context["deadline"]
        )

    def readiness(self):
        self.guard.readiness()

    def call(self, name, timeout=45, **arguments):
        # Arguments can contain typed credentials. Log only the operation name and outcome.
        with self._operation(name):
            return self.client.call(name, dict(device=self.device["id"], **arguments), timeout)

    def reset(self, artifact, app_id, target):
        self.target = target
        with self._operation("Reset, install, and request app launch"):
            self.lifecycle.reset(artifact, app_id, target)
            self.app_id = app_id
        with self._operation(f"Wait {AppLifecycle.SETTLE_SECONDS} seconds after app installation and launch"):
            self.lifecycle.wait_after_launch()

    def snapshot(self):
        with self._operation("Capture and validate masked screenshot"):
            return self.screen.snapshot()

    def _startup_retry(self, attempt, error, remaining):
        if self.activity:
            self.activity.write("Retry device adapter startup", "retrying",
                "Read-only attempt " + str(attempt) + " failed; "
                + format(remaining, ".1f") + " seconds remain in the startup window. "
                + str(error), self.device, self.target)

    def _capture_retry(self, attempt, error):
        if self.activity:
            self.activity.write("Retry unstable screenshot", "retrying",
                "Discarded capture " + str(attempt) + " of " + str(ScreenCapture.MAX_ATTEMPTS)
                + "; waiting for a stable screen. " + str(error), self.device, self.target)

    def _operation(self, name):
        return self.activity.operation(name, self.device, self.target) if self.activity else nullcontext()

    def foreground(self):
        return self.status.foreground()

    def running(self, app_id, executable):
        return self.status.running(app_id, executable)

    def crashes(self):
        return self.status.crashes()

    def close(self):
        if self.client:
            self.client.close()
