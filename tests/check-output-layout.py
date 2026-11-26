#!/usr/bin/env python3
"""Check the public launcher from different folders. Use fake readiness tools, never an API."""

import argparse
import asyncio
import json
import os
from pathlib import Path
import shlex
import tempfile


def write_tools(installation):
    """Keep readiness checks local and predictable."""
    tools = installation / "fake-tools"
    tools.mkdir(parents=True)
    replies = {
        "git": "0000000000000000000000000000000000000000 refs/heads/main",
        "adb": "List of devices attached\\nfixture-device\\tdevice",
        "xcrun": "Fixture iPhone connected wired",
        "java": "fixture java version",
        "xcodebuild": "fixture Xcode version",
    }
    for name, reply in replies.items():
        path = tools / name
        path.write_text("#!/bin/bash\nprintf '%b\\n' " + shlex.quote(reply) + "\n")
        path.chmod(0o700)
    module = installation / "tools/node-packages/lib/node_modules/@mobilenext/mobile-mcp/lib/mobilecli.js"
    module.parent.mkdir(parents=True)
    module.write_text("""
module.exports.Mobilecli = class {
    getDevices({ type }) {
        const device = { id: 'fixture-device', platform: 'android', state: 'online', type: 'real' };
        return { data: { devices: type === device.type ? [device] : [] } };
    }

    getPath() {
        return '/fixture/mobilecli';
    }
};
""".lstrip())
    (installation / "environment.sh").write_text(
        "export PATH=" + shlex.quote(str(tools)) + ':"$PATH"\n'
    )


def write_inputs(shared, inputs):
    """Provide only user inputs. TestPilot must create every output folder itself."""
    shared.mkdir()
    inputs.mkdir()
    settings = shared / "default.yaml"
    settings.write_text("""
workspace: {root: ./legacy-work}
reports: {root: ./legacy-reports}
repository: {url: 'https://example.invalid/app.git', branch: main, solution: App.sln}
execution: {time-limit-minutes: 5}
ai-model: {name: fixture-model, api-key: synthetic-credential}
ai-budget: {amount: 1, currency: USD}
inputs: {instructions: ./unused.txt}
build: {targets: [{name: fixture, configuration: Release, project: App.csproj, android: {framework: net10.0-android}}]}
""".lstrip())
    settings.chmod(0o600)
    (inputs / "app.yaml").write_text("inputs: {instructions: ./instructions.txt}\n")
    (inputs / "instructions.txt").write_text("Check a button. Fixture only.\n")
    return settings


async def invoke(command, cwd, settings, run_file, env):
    """Capture command output in memory, including paths containing spaces."""
    process = await asyncio.create_subprocess_exec(
        str(command),
        "validate",
        "--config",
        str(settings),
        "--run-config",
        str(run_file),
        "--branch",
        "main",
        cwd=cwd,
        env=env,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=60)
    return process.returncode, (stdout + stderr).decode()


def check_report(inputs, count):
    """Check retained output while ensuring validation created no clone work."""
    root = inputs / "TestPilot output"
    reports = list((root / "reports").glob("report_*"))
    assert len(reports) == count
    assert all((report / "index.html").is_file() for report in reports)
    assert not (root / "work").exists()
    return reports


async def check_launcher(command, root):
    """Exercise successful, repeated, and invalid-input invocations."""
    installation = root / "isolated-installation-state"
    write_tools(installation)
    inputs = root / "FirstRun with spaces"
    shared = root / "shared"
    other = root / "another launch folder"
    other.mkdir()
    settings = write_inputs(shared, inputs)
    env = dict(os.environ, TESTPILOT_INSTALL_ROOT=str(installation))
    env.pop("OPENAI_API_KEY", None)
    help_process = await asyncio.create_subprocess_exec(
        str(command), "--help", cwd=other, env=env,
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
    )
    help_output, _ = await asyncio.wait_for(help_process.communicate(), timeout=60)
    assert help_process.returncode == 0
    assert b"Usage: testpilot <command>" in help_output
    print("PASS renamed launcher exposes the documented testpilot command")
    assert not (inputs / "TestPilot output").exists()

    code, output = await invoke(command, inputs, settings, Path("app.yaml"), env)
    assert code == 0, output
    first = check_report(inputs, 1)[0]
    original = (first / "index.html").read_bytes()
    print("PASS output folders are created from user inputs only")

    code, output = await invoke(command, other, settings, inputs / "app.yaml", env)
    assert code == 0, output
    check_report(inputs, 2)
    assert not (other / "TestPilot output").exists()
    assert not (shared / "TestPilot output").exists()
    assert not (installation / "reports").exists()
    assert (first / "index.html").read_bytes() == original
    print("PASS another launch folder keeps output with the same inputs and preserves reports")

    layout = json.loads((first / "output-layout.json").read_text())
    assert layout["legacyRootSettingsIgnored"] is True
    assert not (shared / "legacy-reports").exists()
    print("PASS legacy output paths cannot redirect generated files")

    (inputs / "app.yaml").write_text("inputs: [invalid yaml\n")
    code, _ = await invoke(command, other, settings, inputs / "app.yaml", env)
    assert code == 3
    check_report(inputs, 3)
    print("PASS invalid YAML still creates its error report with the inputs")

    (inputs / "app.yaml").unlink()
    code, _ = await invoke(command, other, settings, inputs / "app.yaml", env)
    assert code == 3
    check_report(inputs, 4)
    print("PASS missing configuration still creates its error report with the inputs")


async def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--command", type=Path, default=Path(__file__).resolve().parents[1] / "scripts" / "testpilot"
    )
    options = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="testpilot-output-layout-") as folder:
        await check_launcher(options.command.resolve(), Path(folder))
    print("6 public output-layout checks passed. No API or physical device was used.")


if __name__ == "__main__":
    asyncio.run(main())
