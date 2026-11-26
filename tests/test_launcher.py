"""Verify the shipped launcher loads its installation environment automatically."""

import os
import pathlib
import shutil
import subprocess
import tempfile
import unittest


class LauncherTests(unittest.TestCase):
    def test_installed_launcher_discovers_its_environment_without_a_root_variable(self):
        self.check_launcher(installed=True)

    def test_source_launcher_discovers_the_local_install_environment(self):
        self.check_launcher(installed=False)

    def check_launcher(self, installed):
        source = pathlib.Path(__file__).resolve().parents[1] / "scripts" / "testpilot"
        with tempfile.TemporaryDirectory(prefix="testpilot launcher ") as folder:
            root = pathlib.Path(folder)
            launcher = root / ("bin" if installed else "scripts") / "testpilot"
            launcher.parent.mkdir()
            shutil.copy2(source, launcher)
            installation = root if installed else root / ".local" / "install"
            installation.mkdir(parents=True, exist_ok=True)
            (installation / "environment.sh").write_text("export TESTPILOT_SETUP_LOADED=yes\n")
            if installed:
                assembly = root / "lib" / "testpilot" / "testpilot.dll"
                assembly.parent.mkdir(parents=True)
                assembly.write_text("fixture")
            tools = root / "fake tools"
            tools.mkdir()
            dotnet = tools / "dotnet"
            dotnet.write_text('#!/bin/sh\nprintf "%s\\n" "$TESTPILOT_INSTALL_ROOT" "$TESTPILOT_SETUP_LOADED" "$@"\n')
            dotnet.chmod(0o700)
            environment = dict(os.environ)
            environment.pop("TESTPILOT_INSTALL_ROOT", None)
            environment["PATH"] = str(tools) + os.pathsep + os.defpath
            result = subprocess.run(["/bin/bash", str(launcher), "--help"], env=environment,
                                    capture_output=True, text=True, check=True)
            lines = result.stdout.splitlines()
            self.assertEqual(lines[0], str(installation))
            self.assertEqual(lines[1], "yes")
            self.assertEqual(lines[-1], "--help")
