# Development guide

Updated: 28 October 2026.

The repository rules are in [AGENTS.md](../AGENTS.md). The product requirements remain in [requirements.md](requirements.md). The refactor and defect fixes keep the approved public commands, YAML fields, limits, and outcome rules. The review and its resolution record are in [the product review](reviews/2026-10-28-product-implementation-review.md).

## Keep each part small

A class owns one area of work. A method has one purpose. A workflow method may call several steps in order; the details belong to those steps. Prefer clear names and normal control flow. Add an interface only where a dependency needs replacement in a test. Constructor injection and ordered workflow steps are the main patterns used here. Do not use the proxy pattern.

Keep methods short enough to read without searching through unrelated work. Long request/schema literals are data; they are not a reason to mix more behavior into a method. Put test setup in named helpers so each test shows its action and expected result clearly. If a unit test needs complicated or advanced code, simplify the tested source first. If it is still complicated, split the behavior into several simple cases. Do not replace methods at runtime to build a test fixture.

## Comments

Use short sentences in simple English. Explain what a component owns and why an important rule exists. For example: “The registry and folder must agree before any recursive deletion.” Avoid unexplained abbreviations and comments that only repeat an obvious assignment. Add a summary for public behavior and document important private rules beside the code. Keep comments up to date when behavior changes.

Use normal formatting: one statement per line, four spaces for indentation, and visible method boundaries. [.editorconfig](../.editorconfig) records shared formatting choices.

## Host code

| Location | Responsibility | How to test it |
| --- | --- | --- |
| src/Cimt/Cli | Parse commands, load settings, and route handlers. | Supply a settings reader, readiness service, run function, and report writer. |
| src/Cimt/Settings | Read YAML, validate sections, and redact secrets. | Validate in-memory nodes; replace the file reader when testing overrides. |
| src/Cimt/Execution | Order run steps, enforce deadlines, discover devices, check out source, and build targets. | Replace ICommandRunner, IRunStep, cleanup, progress, or text input at their boundaries. |
| src/Cimt/Reporting | Calculate outcomes and render local reports. | Supply saved JSON and configuration; no device or API is needed. |
| src/Cimt/Infrastructure | Start processes and hold the Mac lock. | Use fake process runners for unit tests; keep actual lock/process checks in regression tests. |
| tools/Cimt.BuildWorker | Read a build request, create arguments, publish, select artifacts, and write metadata. | Test command/outcome policies directly; replace IBuildProcess for workflow tests. |

RunState stores data only. RunCoordinator orders steps and handles failure/cleanup. It does not implement Git, builds, device access, or HTML. Production services are connected at Entry and RunEngine. There is no dependency-injection container to configure.

## Device and AI worker

| Module | Responsibility |
| --- | --- |
| run_ui.py, device_runner.py | Connect services and handle one device's failures. |
| device_scheduler.py | Submit startup devices with a two-worker limit. |
| check_results.py | Validate explicit observations and calculate the scenario verdict. |
| check_recorder.py, requirement_results.py | Record mapped checks/evidence and update per-objective requirement decisions. |
| scenario.py | Order one objective using local scenario state. |
| actions.py | Validate and execute allowed actions; enter credentials locally. |
| coverage_tracker.py | Track observed and activated controls. |
| crashes.py | Observe terminations and apply startup/retry/cancel rules. |
| evidence.py | Save redacted worker snapshots and masked images. |
| budget.py, run_control.py | Enforce shared cost and time/stop rules. |
| action_prompt.py, agent.py, openai_transport.py | Build model input, reserve cost, parse actions, and send HTTPS requests. |
| mobile.py | Connect the device services used by a scenario. |
| app_lifecycle.py, device_commands.py | Install/reset the tested app and query readiness/status. |
| redaction.py, screen_capture.py | Identify sensitive fields and produce masked screen evidence. |
| mcp_client.py, rpc_messages.py | Own the MCP connection and parse complete RPC messages. |

Each objective has its own ScenarioSession. Workers share only the run stop signal, budget, and synchronized journal. Tests provide fake phones, agents, HTTP transport, process functions, and clocks through normal constructors. Do not bypass constructors to create test objects.

## Run the checks

On a prepared development Mac, from the CIMT folder:

```bash
bash scripts/check-development.sh
```

This runs xUnit host/build-policy tests, Python unit tests, the existing CLI/cleanup regression checks, four simulated build-contract checks, and the macOS build-adapter fixture. It does not call OpenAI, operate physical phones, or build the real MAUI application. The xUnit project pins its test dependencies; the Python tests use unittest from the standard library and the installed CIMT support dependencies.

Unit tests cover behavior at the extracted boundaries: failure precedence, deadlines, cleanup after failure, argument validation, safe HTML, build properties, metadata fallback, budget reservation, masking, rejected actions, startup crashes, repeated action crashes, reset failures, RPC parsing, and submission of every startup device with a two-worker limit. Scheduling tests use a recording executor and worker in separate one-, two-, and three-device cases. They do not use barriers, locks, temporary reports, or method replacement. The production executor uses a bounded thread pool; the small tests verify its submission contract, not physical-device concurrency. Real-device acceptance remains a separate gate.

Expected result: all checks pass. A failure makes the script return a nonzero code. Investigate the failing component before running the real-app example. Fixes that require changing the product definition must be discussed with the product owner first.

## Defect boundaries

Checks have explicit expected and observed behavior. A failed effective expectation remains failed after a later pass or an execution limit. A validated instruction override changes the applicable requirement expectation, while preserving the original observation in history; it cannot hide app crashes or instruction failures. Finishing navigation without an explicit objective check is inconclusive. Each recorded check points to the masked screen used for that decision. RequirementCatalogue now preserves every nonblank source item, text, line range, and stable ID. RequirementReportBuilder constructs scoped coverage from configured targets and startup devices. Full semantic scenario planning and real application acceptance remain release work.

Capture reads sensitive field positions before and after taking an image, even when the first screen has no sensitive field. Changed fields stop capture before the image can be returned. Known crash findings are published before capture or image storage; capture errors are separate evidence errors. The performed action is retained when capture or recovery throws.

BuildResultResolver is a pure per-field policy. BuildArtifactStore reads metadata and saves artifacts; ApplicationBuilder records an unusable target and permits later targets. Helper shutdown and owned work deletion are separate cleanup attempts. Ownership checks still apply when helper shutdown fails.

The mapping demo uses the real input and report services with synthetic observations. It is separate from the small unit tests. See [mapping rules](requirement-mapping.md) for the catalogue contract and status precedence. The action schema follows [official Structured Outputs guidance](https://developers.openai.com/api/docs/guides/structured-outputs?api-mode=responses); local mapping/quote validation remains mandatory.
