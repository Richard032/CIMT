# Initial run engine

Updated: 28 October 2026. Status: implemented and checked with simulations; real application run pending the existing API key.

The [approved requirements](requirements.md) remain the release target. This document describes the smaller implementation that can now be exercised through cimt run. It is not a release-acceptance claim.

## Execution path

The .NET command holds the Mac-wide lock, loads merged YAML and text inputs, checks model access without inference, snapshots connected physical devices, clones the configured branch and its recorded submodules, and builds each applicable target/platform. Successful installable artifacts are saved under the local report. Build errors remain exit 3 while other targets are attempted.

The Python support worker uses the installed Mobile MCP server and its native helper. All startup devices are scheduled, with at most two active. Targets on one device execute sequentially. Each target/device currently receives one objective from the supplied instructions and requirements. The model selects one action from the masked screen and UI elements; host code validates and executes it. Credentials are requested by alias and entered locally without supplying their values to the model.

Before each objective the app is reinstalled; Android data clear is verified. Optional reset and verification hooks receive CIMT_TARGET, CIMT_DEVICE, and CIMT_APP_ID, with their working directory resolved from the declaring YAML. iOS reinstall verifies the app container; Keychain/backend state requires app-specific hooks. Reset or masking failures stop the run. A locked device receives no application actions and is marked incomplete.

The native daemon has a run-specific home. Ownership markers and a registry restrict clone cleanup to CIMT-created work, including interrupted work on the next run. Reports survive cleanup. This does not delete the developer's existing checkout.

## AI limits and evidence

The current validated pricing profile is gpt-5.4-mini-2026-03-17 in USD. Its standard rates and context limit are recorded with the [official model source](https://developers.openai.com/api/docs/models/gpt-5.4-mini). Unknown model/currency combinations are rejected before inference. The model response cap is 2,048 tokens. No hosted tools, priority processing, or automatic paid retries are enabled.

Every paid request reserves the full 400,000-token input context cost plus the output cap: USD 0.309216. This intentionally overestimates typical input rather than estimating image tokens. A shared lock accounts for both device workers. Usage releases unused reservation; missing/uncertain usage retains the full amount. Reservations and usage are journaled locally. Remaining funds below the reservation stop further requests even if a typical request would cost less. This is a conservative run budget, not an exact provider invoice or account-wide spending limit.

The whole-run deadline starts at CLI entry and includes preparation and builds. Screenshots are masked before storage or submission. Sensitive fields are read before and after image capture, including screens that initially have no sensitive fields. A change in their presence or geometry stops capture before image return. Missing reliable masking geometry stops execution. The report includes steps, observations, interpreted instructions, discovered/attempted controls, blocked paths, crash evidence where available, and the stopping reason. Known crashes are recorded and published before image capture or storage. Evidence failures are reported separately and do not erase the finding or performed action. Unexpected process termination without a matching native crash report is labelled suspected. Three matching crash attempts cancel the affected objective; successful retry at that point clears its counter.

The worker records explicit checks with subject, instruction/requirement source, status, expected behavior, observed behavior, and reason. Each check links to the masked screen used by the model. Passed/failed checks need expected and observed evidence; unresolved/overridden checks need a reason. A failed check or crash keeps the scenario failed even after a later pass or limit. A validated instruction override changes the applicable requirement expectation while retaining its earlier observations; it cannot hide an app crash or instruction failure. A completed objective needs a passed instruction check; navigation alone cannot pass. An unresolved latest check prevents a pass. Later evidence can resolve an unknown result for the same source and subject; any recorded failure remains a failure. A requirement may be overridden by instructions with an explanation. The host now saves a complete catalogue before runtime preflight/builds. Checks map to its stable IDs, source text, and line references. Every applicable target/device pair is reported, including failed builds and work that never started. Unknown IDs or invalid instruction quotes are rejected. Unresolved requirements keep coverage incomplete. See [mapping rules](requirement-mapping.md).

The example objective is to click reachable buttons looking for crashes. Coverage counts describe observed control/state combinations. They do not establish exhaustive coverage of every possible screen or hidden state. Verdict and completion remain separate. Exit precedence is infrastructure/configuration/build error (3), test failure (1), incomplete (2), pass (0).

## User example and checks

Use the [example folder](../examples/econ-button-crash/README.md) for the exact public commands, private YAML template, two build configurations, text inputs, and macOS build adapter. No API key, login secret, physical-device identifier, or signing identity is bundled.

Development verification from the source folder:

```bash
source /Users/Shared/CIMT/environment.sh
dotnet build src/Cimt/Cimt.csproj -c Release
dotnet run --project tests/Cimt.Checks/Cimt.Checks.csproj -c Release
dotnet build tools/Cimt.BuildWorker/Cimt.BuildWorker.csproj -c Release
python3 tests/check-build-contract.py
/Users/Shared/CIMT/tools/python/bin/python tests/check-runtime.py
/Users/Shared/CIMT/tools/python/bin/python tests/check-example-build.py
```

The checks cover configuration and CLI behavior, owned cleanup, failure precedence, concurrent budget reservations, uncertain API usage, secret masking, crash counters, action bounds, build metadata, and the macOS target import. They use simulations/fixtures. No real MAUI app pass or live OpenAI access is inferred from them.

## Remaining release work

- Verify real APK/IPA builds and user-command exploration on both connected devices.
- Qualify input, reset, login, masking, crash reproduction, concurrency, and limits with real application evidence.
- Complete semantic scenario decomposition, adaptive replay, YAML-driven setup, supported toolchain manifest, and all command/reset demonstrations.
- Demonstrate Jenkins and a second Intel Mac; complete the adapter-selection and release acceptance gates.

On the development Mac the public example validation currently stops at an empty private API-key field (exit 3), before provider access or app interactions. The user chose an existing key; its usable local source has not yet been supplied.


## Internal structure and development verification

The host, build worker, and device worker are split into services with narrow responsibilities. See the [development guide](development.md) for the component map and [AGENTS.md](../AGENTS.md) for coding rules. Run the full source verification with bash scripts/check-development.sh. After the complete mapping increment, 207 unit tests (119 .NET and 88 Python) and 23 regression/contract checks pass: 230 checks total. The resolution record is in the [product review](reviews/2026-10-28-product-implementation-review.md). These use simulated dependencies and do not establish real-device acceptance.

The complete mapping increment adds catalogue, scoped-status, response-validation, and reporting tests, plus a public-command failed-build matrix check. The [implementation status](implementation-status.md) records current counts and the [offline mapping demonstration](../examples/requirement-mapping/README.md) covers all five statuses. No extra paid planning call is added.

Run folders now use one [shared identity](run-identity.md) from invocation through reporting/cleanup. Work and report names have exactly the same UTC millisecond timestamp; collisions advance the pair together without changing the actual start/deadline. Portable identity metadata remains in the report, and unsafe report placement is rejected.
