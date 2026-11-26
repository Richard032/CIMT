# Debug TestPilot in VS Code

Open [TestPilot.code-workspace](TestPilot.code-workspace) in VS Code. Install the recommended C# and Python debugger extensions. From the workspace’s integrated terminal, run:

```bash
./scripts/testpilot-debug --help
```

For a test run, pass the same arguments you would pass to `testpilot`. Use absolute paths if the terminal is outside the test folder.

```bash
./scripts/testpilot-debug replay --config /path/to/default.private.yaml --run-config /path/to/application.yaml
```

1. Set C# breakpoints in the checkout, then select **TestPilot host · attach to terminal command** in Run and Debug. Choose the PID printed by the launcher. The host resumes after attachment and processes the original arguments.
2. Set Python breakpoints under `runtime/`. When the run reaches **Execute device tests**, start **TestPilot Python worker · attach** from the debug profile dropdown and its Start button. Keep the C# session running while you attach. The Python worker listens on the local loopback address on port 5678 and begins reading its request after attachment.

The launcher builds the C# host and uses the checkout's Python source with the tools and environment from your installation. It defaults to the Mac checkout-local installation at `~/Development/TestPilot/.local/install`. Set `TESTPILOT_INSTALL_ROOT` to use another installation. It finds debugpy in the VS Code Python Debugger extension. For a different debugpy installation, set `TESTPILOT_DEBUGPY_PATH` to the directory containing the `debugpy` package.

To attach during a different phase, prefix the command with `TESTPILOT_DEBUG_PYTHON=preflight` or `TESTPILOT_DEBUG_PYTHON=proposal`. Attach when that stage starts in the activity log. Use `TESTPILOT_DEBUG_PYTHON=off` for C# debugging alone. Only the selected worker pauses. Normal command deadlines continue while a debugger is paused, including the shorter preflight and proposal deadlines. Running `run` or `replay` under a debugger still uses the configured devices and AI provider.
