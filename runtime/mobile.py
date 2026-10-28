"""Device adapter facade. Each service below owns a separate responsibility."""

from app_lifecycle import AppLifecycle
from device_commands import NativeDevice, DeviceReadiness, DeviceStatus
from mcp_client import Mcp
from redaction import Redactor, ScreenMasker
from screen_capture import ScreenCapture


class Mobile:
    """Exposes the device operations needed by a scenario."""

    def __init__(
        self, binary, device, folder, context, redactor, commands=None, client_factory=Mcp
    ):
        self.device = device
        self.folder = folder
        self.context = context
        self.redactor = redactor
        self.commands = commands or NativeDevice(binary, device, context)
        self.guard = DeviceReadiness(self.commands, folder)
        self.status = DeviceStatus(self.commands, folder)
        self.lifecycle = AppLifecycle(self.commands, self.call)
        self.screen = ScreenCapture(
            self.call, self.commands.native, self.readiness, redactor, ScreenMasker(redactor)
        )
        self.client_factory = client_factory
        self.client = None

    def connect(self):
        """Check the device lock before starting its MCP connection."""
        self.readiness()
        self.client = self.client_factory(
            self.folder, self.commands.env, self.redactor, self.context["deadline"]
        )

    def readiness(self):
        self.guard.readiness()

    def call(self, name, timeout=45, **arguments):
        return self.client.call(name, dict(device=self.device["id"], **arguments), timeout)

    def reset(self, artifact, app_id, target):
        self.lifecycle.reset(artifact, app_id, target)

    def snapshot(self):
        return self.screen.snapshot()

    def foreground(self):
        return self.status.foreground()

    def running(self, app_id, executable):
        return self.status.running(app_id, executable)

    def crashes(self):
        return self.status.crashes()

    def close(self):
        if self.client:
            self.client.close()
