"""Copy configured local test files into an installed app before launch."""

import hashlib
from pathlib import Path, PurePosixPath
import shlex
import shutil
import subprocess
import tempfile
import time
from errors import DeviceCommandTimeout, InfrastructureError
from .target import DeviceTarget


class ExternalFiles:
    def __init__(self, commands, check=lambda: None):
        self.commands = commands
        self.check = check

    def copy(self, app_id):
        for entry in self.commands.context.get("externalFiles", []):
            if entry["platform"] != self.commands.device["platform"]:
                continue
            self.check()
            source = Path(entry["source"])
            destination = entry["destination"]
            self._check_destination(destination)
            try:
                expected = self._hash(source)
                if self.commands.device["platform"] == "android":
                    actual = self._android(source, destination, app_id)
                elif self.commands.device.get("type", "real") == "simulator":
                    actual = self._simulator(source, destination, app_id)
                else:
                    actual = self._ios_device(source, destination, app_id)
            except OSError:
                raise InfrastructureError("External test file could not be read or copied") from None
            if actual != expected:
                raise InfrastructureError("External test file verification failed")
            self.check()

    @staticmethod
    def _check_destination(destination):
        parts = destination.replace("\\", "/").split("/")
        if (not destination or destination.startswith("/") or "\\" in destination or ":" in destination
                or any(ord(c) < 32 or ord(c) == 127 for c in destination)
                or any(part in ("", ".", "..") for part in parts)):
            raise InfrastructureError("External file destination must remain inside the app data container")

    @staticmethod
    def _hash(path):
        digest = hashlib.sha256()
        with path.open("rb") as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(block)
        return digest.hexdigest()

    def _run(self, arguments, **options):
        self.check()
        remaining = self.commands.context.get("deadline", time.time() + 60) - time.time()
        if remaining <= 0:
            self.check()
            raise DeviceCommandTimeout("External file transfer deadline expired")
        try:
            result = self.commands.run_command(arguments, capture_output=True,
                env=self.commands.env, timeout=min(60, remaining), **options)
        except subprocess.TimeoutExpired:
            raise DeviceCommandTimeout("External file transfer timed out") from None
        if result.returncode:
            # Do not leak device file contents or command output into reports or AI input.
            raise InfrastructureError("External file transfer command failed; verify app data access")
        self.check()
        return result

    def _simulator(self, source, destination, app_id):
        result = self._run(["xcrun", "simctl", "get_app_container", self.commands.device["id"], app_id, "data"], text=True)
        container = Path(result.stdout.strip())
        if not container.is_absolute() or not container.is_dir():
            raise InfrastructureError("Simulator app data container was not found")
        target = container / destination
        if not target.resolve().is_relative_to(container.resolve()):
            raise InfrastructureError("External file destination escapes the simulator app data container")
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        return self._hash(target)

    def _android(self, source, destination, app_id):
        serial = DeviceTarget(self.commands.device, self.commands.run_command).adb_serial()
        adb = ["adb", "-s", serial, "shell"]
        parent = str(PurePosixPath(destination).parent)
        self._run(adb + [shlex.join(["run-as", app_id, "mkdir", "-p", parent])], text=True)
        # run-as keeps the file app-private and requires a debuggable application.
        script = "cat > " + shlex.quote(destination)
        self._run(adb + [shlex.join(["run-as", app_id, "sh", "-c", script])], input=source.read_bytes())
        result = self._run(adb + [shlex.join(["run-as", app_id, "sha256sum", destination])], text=True)
        return result.stdout.split()[0] if result.stdout.split() else ""

    def _ios_device(self, source, destination, app_id):
        common = ["--device", self.commands.device["id"], "--domain-type", "appDataContainer",
                  "--domain-identifier", app_id, "--timeout", "60"]
        self._run(["xcrun", "devicectl", "device", "copy", "to", *common,
                   "--source", str(source), "--destination", destination], text=True)
        with tempfile.TemporaryDirectory(prefix="cimt-external-file-") as directory:
            received = Path(directory) / "verify-file"
            self._run(["xcrun", "devicectl", "device", "copy", "from", *common,
                       "--source", destination, "--destination", str(received)], text=True)
            return self._hash(received)
