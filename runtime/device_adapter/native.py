"""Read-only calls to the installed native helper."""

import json
import os
import re
import subprocess
import time
from errors import DeviceCommandTimeout, DeviceServerStartupError, InfrastructureError, LimitReached


class NativeDevice:
    """Runs the native helper with one fixed device and run-specific home."""

    def __init__(self, binary, device, context, redactor, run_command=subprocess.run):
        self.binary = binary
        self.device = device
        self.context = context
        self.run_command = run_command
        self.redactor = redactor
        self.env = dict(os.environ, MOBILECLI_HOME=context["nativeHome"])
        self.env.pop("OPENAI_API_KEY", None)

    def native(self, arguments, timeout=30):
        """Call the native helper for this fixed device within the run deadline."""
        result = self._run(arguments, timeout, text=True)
        try:
            return json.loads(result.stdout)
        except ValueError:
            raise InfrastructureError("Device command returned invalid JSON") from None

    def screenshot(self):
        """Read lossless pixels in memory. Never create a raw screenshot file."""
        return self._run(["screenshot", "--format", "png", "--output", "-"], 30, text=False).stdout

    def _run(self, arguments, timeout, text):
        remaining = self.context["deadline"] - time.time()
        if remaining <= 0:
            raise LimitReached("Whole-run time limit reached")
        try:
            r = self.run_command(
                [self.binary] + arguments + ["--device", self.device["id"]],
                capture_output=True,
                text=text,
                env=self.env,
                timeout=min(timeout, remaining),
            )
        except subprocess.TimeoutExpired:
            raise DeviceCommandTimeout("Device command timed out") from None
        if r.returncode != 0:
            error = r.stderr.decode(errors="replace") if isinstance(r.stderr, bytes) else r.stderr
            message = self.redactor.text(error[-1000:] or "Device command failed")
            # Only this known helper startup failure can enter startup recovery.
            if re.search(r"device server did not start within \d+(?:\.\d+)?s on port \d+", error):
                raise DeviceServerStartupError(message)
            raise InfrastructureError(message)
        return r
