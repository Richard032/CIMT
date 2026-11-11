# Configure and run CIMT

Documentation baseline: 1.0. Updated: 10 November 2026.

This guide describes implemented commands. [Requirements](requirements.md) define the approved product; [release readiness](release-1.0.md) identifies unfinished work. Older proposals and dated usage notes are preserved in [product-guide history](product-guide-history.md). Install first using the [Mac how-to](installation.md).

## Commands

| Command | What happens |
| --- | --- |
| `cimt validate --config default.private.yaml --run-config application.yaml` | Validate inputs, configuration, Git branch access, tools and selected device readiness; write a local report. No paid inference, clone, application build, reset or test. |
| `cimt run --config default.private.yaml --run-config application.yaml` | Prepare, check model access, clone the configured remote branch, build, reset/install and test; write a new report. |
| `cimt replay --config default.private.yaml --run-config application.yaml` | Test current instructions against one retained successful build set; no clone, submodule update, restore or application build. |

`--config` is required; `--run-config` is an optional override. `--branch <branch>` overrides the repository branch for the invocation. Use `cimt --help` for the installed command. YAML-driven `setup` and saved-scenario `replay --scenario` are not implemented. A source folder copied into a test folder is not a substitute for a CIMT retained build. There is no implemented command to rebuild an arbitrary existing checkout without cloning.

Run and replay operate applications and may spend the configured AI budget. They are separate actions from validation. Replay is another AI test using current text, not playback of a saved sequence of taps. See [retained work and replay](work-retention-and-replay.md).

## Configuration files and precedence

Keep shared secrets in a private default file and application/test settings in a per-run file. Merge order is **default YAML → per-run YAML → terminal override**. Nested mappings merge; lists replace completely. Unknown keys, placeholders and invalid values are rejected. Relative values retain the origin of the YAML that declares them.

Example private defaults, with illustrative limits:

```yaml
execution:
  time-limit-minutes: 60
  interactive-pauses: false
ai-model:
  name: "<supported-model-profile>"
  api-key: "<private-key>"
ai-budget:
  amount: 5
  currency: USD
reports:
  sections: [requirements, scenarios, findings, interpretations, diagnostics]
```

Replace placeholders locally and restrict the private file, for example `chmod 600 default.private.yaml`. Do not commit it. Select an implemented pricing profile from `runtime/budget.py` in the installed source revision; do not assume every provider model works. Model, positive whole-run time limit and positive budget are mandatory. No model fallback is applied. [Dependency selection](dependencies.md) explains version ownership; budget mechanics are in the [run engine](run-engine.md).

Example application settings, using the paths and branch from our keyboard-regression workflow:

```yaml
repository:
  url: https://subgit.curtis.ch/ECON/ag-econ-mobile.git
  branch: issue/CE1-I560_string_parameter_hidden_by_keyboard
  solution: EconMobile.sln
inputs:
  instructions: ./instructions.txt
  requirements: ./requirements.txt
  setup: ./setup.txt
execution:
  device-kind: virtual
build:
  targets:
    - name: Release_Generic
      configuration: Release_Generic
      project: EconMobile.Common/EconMobile.Common.csproj
      android:
        framework: net10.0-android36.0
        script: ./build/android.sh
        properties:
          AndroidPackageFormats: apk
          EmbedAssembliesIntoApk: true
      ios:
        framework: net10.0-ios
        script: ./build/ios.sh
        properties:
          RuntimeIdentifier: iossimulator-arm64
          EnableCodeSigning: true
external-files:
  - source: ./test.xpa
    platform: ios
    destination: Documents/test.xpa
```

This is a concrete example, not a universal project/framework/signing profile. Use the tested branch, application identifiers, platform destination and properties required by your application. The XPA entry above provisions only iOS; add an Android entry with that app's expected container-relative destination when testing Android. Keep the fixture alongside the configuration. For private packages, add an explicit `RestoreConfigFile` property to **each** platform as described in [installation](installation.md#9-prepare-private-git-and-nuget-access). `$HOME` inside a YAML property is not shell-expanded; use the real absolute path.

## Device selection

Select `execution.device-kind: virtual` for booted iOS simulators/Android emulators, or `physical` for connected phones. Omission defaults to physical. Optional `execution.device-ids` is a nonempty list of exact IDs from local discovery. All listed devices must be present. Without the list, all discovered startup devices of the selected kind participate. New connections do not join an active run. Physical and virtual devices are separate run kinds; at most two workers run simultaneously, with sequential target work on each device. Both platforms need not be present, but an absent platform is not a passed test.

Use a simulator runtime identifier matching host architecture (`iossimulator-arm64` on our Apple Silicon Mac, `iossimulator-x64` on Intel). Physical iOS needs its own signing and installable artifact profile. See [virtual devices](virtual-devices.md) and [installation](installation.md).

## Path rules and run folders

The folder containing `--run-config`, or `--config` when used alone, is the input folder and output parent. CIMT runs from any launch directory. Repository solution/project and YAML artifact fallback paths resolve from the clone root. Text inputs, replacement scripts and reset commands resolve from their declaring YAML. External fixture sources have stricter containment rules described below.

```text
CE1-I560/
  README.md
  default.private.yaml
  application.yaml
  setup.txt
  instructions.txt
  requirements.txt
  test.xpa
  build/
    build.sh
    android.sh
    ios.sh
  CIMT output/                           # generated by CIMT
    retained-builds.json                  # after successful artifact publication
    work/work_<UTC-date-time>/            # retained clone/build work
    reports/report_<same-date-time>/      # new report per invocation
```

The [test-input how-to](test-inputs.md) explains this real-life layout and what validation actually enforces. Do not create work/report folders or add `workspace.root`/`reports.root`; these legacy keys are ignored with a notice. Reports survive later runs. Previous verified owned work for these same inputs is removed only immediately before a new clone; validation, replay and failed preflight preserve it. Never copy a developer checkout over owned work to imitate a cache. [Run identity](run-identity.md) defines the paired timestamp and collision rules.

## Build scripts and project authority

The installed defaults forward explicit project, configuration, framework and properties. They preserve the application's build/pre-build targets, including CuRMiTagger. CIMT does not inject a substitute tagger invocation or silently skip an incompatible command. Fix/configure the application or provide an explicitly authorized wrapper for the owned clone.

For the layout above, copy all three supplied wrappers together:

```bash
mkdir -p ./build
cp "$CIMT_INSTALL_ROOT/templates/test-run/build/"*.sh ./build/
```

`android.sh` and `ios.sh` call their adjacent `build.sh`, which delegates to installed backends. The source templates are in `scripts/test-run/build`. Do not install these forwarding wrappers over the backend scripts they call. Keep custom preparation in the test folder's wrapper; an installation update does not update that custom copy.

A normal run builds the **remote** branch. Required application changes must already be committed and pushed; local application edits are not used. NuGet sources and signing are the application's build prerequisites, not an effect of successful CIMT compilation. [Build-script contract](build-script-contract.md) defines environment variables, JSON handoff, artifact ambiguity and error handling.

## External test files

Declare fixtures in `external-files`, as in the XPA example. `source` must be a readable file beside its declaring YAML or in a subfolder; absolute paths, URLs and parent traversal are rejected. `platform` is `ios` or `android`; `destination` is a file path relative to the tested app's data container. Destinations must be unique per platform, including case-insensitive iOS checks.

CIMT checks source readability before model access/reset, then copies and verifies SHA-256 after every reset and optional reset hooks, before app launch. Replay repeats this provisioning using current settings. Transfer/verification failure stops setup; the original host file is preserved. Fixture bytes are not supplied as AI instructions. iOS Simulator uses `simctl`; physical iOS uses authorized `devicectl` transfer/read-back; Android uses `adb run-as` and requires a debuggable app. Offline command coverage is not live qualification of every device type.

Providing an XPA file does not teach the AI to open it. Put the actual navigation in `setup.txt`, expected behavior in `requirements.txt`, and regression steps in `instructions.txt`. See [test inputs](test-inputs.md).

## Credentials, reset and privacy

Named credentials belong in private YAML:

```yaml
credentials:
  test-user:
    username: "<test-username>"
    password: "<test-password>"
masking:
  rules:
    - element-id: PasswordEntry
```

Instructions refer to the alias, never the value. Credential commands require an explicit field and verifiable target. CIMT resolves, focuses, masks and replaces the field contents locally rather than appending or sending values to AI. Repeating the command leaves one configured value; adapter completion does not prove login succeeded. Ordinary text entry retains ordinary semantics.

Before each current objective CIMT reinstalls/resets the app, then runs optional `reset.command` and `reset.verify-command` argument lists. Hooks receive `CIMT_TARGET`, `CIMT_DEVICE`, and `CIMT_APP_ID`. Failure stops setup. iOS reinstall does not promise to clear Keychain/server state; supply authorized hooks where needed. Prepare external equipment separately and state which scenarios depend on it.

Masking is element-ID based. Lossless PNG screenshots and UI text must be masked before storage or AI submission; unreliable required geometry stops execution. See [redaction](redaction.md) and [screenshot masking](screenshot-masking.md). Outputs can still contain sensitive application data; keep work and reports private.

## Interactive pauses

Set `execution.interactive-pauses: true` for local acknowledgement before model access, repository/build access, and AI testing. Waiting consumes the same whole-run deadline. Use false/omit for Jenkins. The checkpoints do not ask the operator to interpret test instructions. Launcher discovery and its local `environment.sh` are automatic; routine invocation does not require manually sourcing it.

## AI interaction, limits and outcomes

AI chooses actions, targets, exploration and recovery. CIMT supplies original instructions, current masked evidence, available resources and AI-selected context. It checks executable syntax, capabilities, coordinates, privacy and shared limits, then returns actual feedback. It does not choose another button because a requested menu is absent. Mobile MCP is a tool adapter, not another agent.

Commands execute FIFO. Failure cancels the pending tail; complete ordered results are supplied to the next normal decision request, subject to stopping rules. Targeted swipes preserve the requested target/distance; refs resolve from current bounds, coordinates are absolute device coordinates. Invalid arguments return generic corrective feedback. Picker guidance explains gesture direction and observation, but the AI must identify the desired picker/value from test instructions and verify it. See [command resources](ai-resource-exchange.md), [command queue](command-queue.md), [batch feedback](batch-feedback.md), and [instruction context](ai-instruction-context.md).

Instructions take priority over conflicting requirements; report the conflict and interpretation. The host retains unresolved checks and observed failures. AI working memory is scenario-local; automatic cross-run app learning is not implemented. Maintain shared reviewed app knowledge as explicit text inputs in Git, with private data excluded.

The deadline starts at invocation and includes preparation/builds. Budget is shared across workers and reserves a conservative maximum before each paid request. Remaining funds can therefore stop testing below the configured cap. A launch failure stops that device; three matching crashes stop the affected objective. Blocking transport/reset/privacy failures and shared limits follow the [execution stopping policy](execution-stopping.md).

| Exit | Meaning |
| --- | --- |
| 0 | Passed and completed under recorded checks. |
| 1 | Test failure. |
| 2 | Incomplete/inconclusive work without a higher-priority error. |
| 3 | Configuration, build or infrastructure error. |

Precedence is 3, then 1, then 2, then 0. Verdict and completion are separate. Navigation, successful builds, tool-call completion and screenshot capture do not prove a requirement passed.

## Review the proposed instructions and setup

After a run or replay, including one stopped with Ctrl+C, CIMT asks the configured AI to review the recorded results and writes `instruction-setup-proposal.md` in that invocation's report folder. It explains how the AI interpreted the goals, details, timing and stopping conditions, then gives draft instructions, reusable app setup and supporting evidence. Review and edit the draft before applying it; original input files are never rewritten. Current testing instructions retain priority.

The proposal uses one inference request within the run's remaining budget and deadline. If testing ended early, the review uses available inputs and partial results. When interactive pauses are enabled, the AI testing checkpoint must already have been acknowledged. If a limit, checkpoint or provider failure prevents generation, the file records the reason and includes the available original instructions and setup. The recorded test verdict stays independent of the review. Proposal text and evidence may be private. Review before sharing.

## Open a run or replay report

Use the exact `index.html` path printed by that invocation, under `CIMT output/reports/report_<timestamp>/`. Each invocation gets a new folder. Inspect the summary, source commit, selected devices, build results, scoped checks, findings, chronological activity and stopping reasons. Evidence links are relative to that report.

While running, `result.json` can contain `inProgress: true` and a provisional incomplete result. This is not the final process exit. After completion, check `inProgress: false`, completion, verdict and exit together. A user interruption preserves available partial evidence. A hard kill cannot guarantee finalization; use the interim report honestly. [Diagnostic reporting](diagnostic-reporting.md) explains the report fields.

For replay, first inspect `CIMT output/retained-builds.json` for the source commit and available platform artifacts. Editing build properties does not change cached binaries. Missing, incompatible or corrupt artifacts stop explicitly; replay never silently builds. Use `run` for a new commit, framework/property change or missing platform.
