"""Installation and reset of the application under test."""

import subprocess
import time
from errors import InfrastructureError
from .target import DeviceTarget


class AppLifecycle:
    """Resets the app container and runs optional application-specific hooks."""

    SETTLE_SECONDS = 20

    def __init__(self, commands, call, check=lambda: None, clock=time.monotonic, sleep=time.sleep):
        self.commands = commands
        self.call = call
        self.check = check
        self.clock = clock
        self.sleep = sleep

    def app_present(self, app_id):
        data = self.commands.native(["apps", "list"]).get("data", [])
        return any(app.get("packageName") == app_id for app in data)

    def reset(self, artifact, app_id, target):
        """Reset platform data and verify app hooks before launching the app."""
        self._check_app_id(app_id)
        self._remove_existing(app_id)
        self._install(artifact, app_id)
        self._clear_android_data(app_id)
        self._run_hooks(app_id, target)
        self.call("mobile_launch_app", packageName=app_id)

    def wait_after_launch(self):
        """Give the newly installed app time to settle before testing starts."""
        until = self.clock() + self.SETTLE_SECONDS
        while True:
            # Short waits keep user cancellation and the run deadline active.
            self.check()
            remaining = until - self.clock()
            if remaining <= 0:
                return
            self.sleep(min(0.1, remaining))

    @staticmethod
    def _check_app_id(app_id):
        if app_id.startswith(("com.apple.", "com.android.", "com.mobilenext.")):
            raise InfrastructureError(
                "Refusing to replace a system or automation-helper application"
            )

    def _remove_existing(self, app_id):
        if self.app_present(app_id):
            self.call("mobile_uninstall_app", packageName=app_id, timeout=120)
            if self.app_present(app_id):
                raise InfrastructureError("App removal/reset could not be verified")

    def _install(self, artifact, app_id):
        # On iOS this resets the container. Keychain/backend state needs hooks.
        self.call("mobile_install_app", path=artifact, timeout=180)
        if not self.app_present(app_id):
            raise InfrastructureError("Installed app identifier was not verified")

    def _clear_android_data(self, app_id):
        if self.commands.device["platform"] != "android":
            return
        result = self.commands.run_command(
            ["adb", "-s", DeviceTarget(self.commands.device, self.commands.run_command).adb_serial(), "shell", "pm", "clear", app_id],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode or result.stdout.strip() != "Success":
            raise InfrastructureError("Android data reset failed")

    def _run_hooks(self, app_id, target):
        context = self.commands.context
        for key in ["command", "verify-command"]:
            if key not in context["config"].get("reset", {}):
                continue
            env = dict(
                self.commands.env,
                CIMT_TARGET=target,
                CIMT_DEVICE=self.commands.device["id"],
                CIMT_APP_ID=app_id,
            )
            result = self.commands.run_command(
                context["config"]["reset"][key],
                env=env,
                cwd=context.get("resetDirectories", {}).get(key),
                capture_output=True,
                text=True,
                timeout=60,
            )
            if result.returncode:
                raise InfrastructureError("Configured reset/verification command failed")
