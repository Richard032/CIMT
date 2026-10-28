# CIMT product documentation

Version: 0.6  
Date: 28 October 2026  
Status: reviewed product behaviour, command responsibilities, and YAML fields approved  
Product: CIMT — Curtis Intelligent Mobile Test

**validate, default build workers, and an initial single-objective run engine are implemented. The real app test has not yet run with this engine. setup and replay report that they are unimplemented. See the [implementation status](implementation-status.md), [installation guide](installation.md), and [runnable main-branch example](../examples/econ-button-crash/README.md). Private keys are supplied locally; none are bundled.**

## 1. Purpose and environment

CIMT supports everyday testing of any configured .NET MAUI application. Developers invoke a terminal command; Jenkins pipelines invoke the same command on their Intel Mac execution node.

Give CIMT a Git repository/branch, configurable build targets, plain-text testing instructions, and optional requirements/setup inputs. CIMT builds the app, operates physical devices, and generates local HTML observations with evidence. It complements the existing validation system; AI exploration does not guarantee complete bug discovery.

One installation serves multiple repositories, with only one active run per Mac. All supported devices connected at startup participate, at most two simultaneously. New connections are excluded. Both platforms need not be present.

OpenAI supplies reasoning in the cloud. Device operation and report storage are local. App backends and external equipment are prepared separately.

## 2. Approved commands

```text
cimt setup --config setup.yaml
cimt validate --config default.yaml --run-config app.yaml
cimt run --config default.yaml --run-config app.yaml
cimt run --config default.yaml --run-config app.yaml --branch feature-to-test
cimt replay --config default.yaml --run-config app.yaml --scenario <saved-scenario-path>
```

| Command | Responsibility |
| --- | --- |
| setup | Prepare the Mac from installation settings and tested toolchain manifest; optionally validate a configured application's readiness. |
| validate | Check configuration, required values, paths/text inputs, Git access/branch, tool/device readiness, credential presence, and model/budget configuration. Produce local HTML without build, installation, reset, or paid AI calls. Actual login, signing, and model access are verified during execution. |
| run | Clone, build configured targets, and execute testing instructions on startup devices. |
| replay | Execute a saved scenario against the current repository/branch/build configuration, adapting navigation where needed and creating a new report. |

The reviewed syntax above is approved. Additional flags, help output, configuration discovery, and detailed process contracts still require specification. CIMT asks no runtime clarification questions.

## 3. Configuration files and precedence

| File | Contents |
| --- | --- |
| setup.yaml | Installation root, toolchain manifest, optional application-readiness validation. |
| default.yaml | Shared working/report roots, OpenAI model/key, run time limit, AI budget, and shared reporting settings. |
| app.yaml | Repository/build configuration, named app credentials, reset commands, masking rules, text input references, and optional default overrides. |

app.yaml is the reusable per-run override, not a separate fourth precedence layer. Users may choose different filenames or app configurations for different testing tasks.

Precedence: **default YAML → per-run YAML → terminal arguments**. Merge nested mappings; replace lists completely. Reject unknown keys and invalid values before building/testing. Record the effective configuration with secrets removed.

Explicit model, positive whole-run time limit, and AI budget are mandatory in the effective configuration. Missing/invalid values stop before testing and produce an error report.

## 4. setup.yaml example and Mac preparation

```yaml
installation:
  root: "/Users/Shared/CIMT"

toolchain:
  manifest: "./toolchain.yaml"

validation:
  config: "./default.yaml"
  run-config: "./app.yaml"
```

The installation path is an example, not a mandatory location. The manifest identifies tested pinned dependency versions; its schema/contents will be defined after validation. validation is optional and checks application readiness without building or testing.

Setup will inspect the Intel Mac/toolchain, install missing tools where feasible, reuse compatible versions, and silently replace incompatible CIMT-required tool versions without confirmation. Replacements are recorded. Setup supports reruns after interruption and reports installed/replaced components, validation results, and remaining manual steps.

Administrator privileges may be requested during setup; normal tests run without them. Manual documentation must cover Apple authentication/licenses, signing/provisioning, device trust/development access, Android USB authorization, Git access, private configuration, and external-equipment preparation. Supported dependency versions and exact steps await the compatibility evaluation.

Validate access under the actual executing account, including the Jenkins account. An installation alone does not configure another account's Git credentials or Apple signing access.

## 5. default.yaml example

```yaml
workspace:
  root: "./work"

reports:
  root: "./reports"
  sections:
    - requirements
    - scenarios
    - findings
    - interpretations
    - diagnostics

execution:
  time-limit-minutes: 60

ai-model:
  name: "<validated-model>"
  api-key: "<private-key>"

ai-budget:
  amount: 5.00
  currency: USD
```

The time/budget values are illustrative. The model/pricing combination must support conservative upper bounds; supported currencies and price validation remain implementation decisions. Strict budget enforcement is mandatory, with no disable switch.

reports.sections selects detailed sections. Run summary, final outcome, coverage, and stopping reasons always remain visible. Step screenshots and saved actions are always collected.

All-startup-device selection, at-most-two device concurrency, and reset before every scenario are fixed behaviour, not optional execution switches.

## 6. app.yaml example

```yaml
repository:
  url: "git@github.com:team/mobile-app.git"
  branch: "main"
  solution: "MobileApp.sln"

build:
  targets:
    - name: Release_Generic
      configuration: Release_Generic
      project: src/MobileApp/MobileApp.csproj
      android:
        framework: "<android-target-framework>"
        properties: {}
      ios:
        framework: "<ios-target-framework>"
        properties: {}

inputs:
  instructions: "./tests/instructions.txt"
  requirements: "./tests/requirements.txt"
  setup: "./tests/setup.txt"

credentials:
  test-user:
    username: "<test-username>"
    password: "<test-password>"

reset:
  command: ["./scripts/reset-test-data.sh"]
  verify-command: ["./scripts/verify-reset.sh"]

masking:
  rules:
    - element-id: "PasswordEntry"
    - element-id: "AccessTokenEntry"
```

Repository URL, branch, and solution are explicit; no branch is assumed. Existing host Git credentials support private cloning. A target name identifies results; configuration selects the .NET build configuration. Target names such as Release_Generic are examples, not fixed product values.

Frameworks must match the application and tested toolchain. properties holds additional per-platform build properties, including signing settings. Exact validation constraints await implementation.

inputs.instructions is required; requirements and setup are optional. Each accepts a local text path or an unauthenticated web link to text content. app.yaml may also override execution, ai-model, ai-budget, and reports sections using the same fields as default.yaml.

All example script paths refer to optional user-provided files, not scripts shipped in this documentation revision. Omit optional reset commands when no additional reset is needed. Application setup text may say “Log in using test-user”; CIMT resolves the named credentials locally and enters them through device controls without sending values to AI.

Masking supports **element-id rules only**, with no screen-region coordinates. Secrets must be masked in screenshots/UI text before saving or AI processing. If required masking cannot be applied reliably, stop and report. Named credential references, not secret values, are stored in action recordings.

## 7. Path rules and run folders

| Path | Resolution |
| --- | --- |
| Repository solution/project | Cloned repository root. |
| YAML artifact fallback | Cloned repository root. |
| Local text inputs | Folder containing the YAML file that declares the value. |
| Replacement build/reset scripts | Folder containing the declaring YAML file. |
| Default build scripts | CIMT installation. |
| Other relative configuration paths | Folder containing the declaring YAML file. |

Absolute paths are accepted where applicable. Inherited relative values retain their declaring-file origin.

For example, corresponding run folders are:

```text
<working-root>/work_2026-10-28_14-30-00-123/   # temporary
<report-root>/report_2026-10-28_14-30-00-123/  # retained
```

Both use the same UTC timestamp with millisecond precision. A collision advances both names together by one millisecond; it never adds a separate suffix, reuses existing data, or changes the actual start/deadline. run-identity.json retains the paired names and identity beside the report. See [run identity](run-identity.md). Reports must sit outside the temporary cleanup folder. Each clone is deleted after success, failure, incompletion, or interruption; reports remain until manually deleted.

## 8. Default and replacement build scripts

Default Android/iOS build scripts are implemented and installed. Their simulated request/result checks pass; actual application build acceptance is blocked by the source pre-build and signing prerequisites recorded in the [build contract](build-script-contract.md). Replacement scripts are supported by the initial run engine; public-command fallback handling has regression tests. See [implementation status](implementation-status.md) for the remaining real-app acceptance work.

Default scripts use configured project, configuration, framework, and build properties; they build and locate installable artifacts and app identifiers.

Users may customize the scripts or reference separate replacements:

```yaml
build:
  targets:
    - name: Release_Generic
      configuration: Release_Generic
      project: src/MobileApp/MobileApp.csproj
      android:
        framework: "<android-target-framework>"
        script: "./scripts/custom-android-build.sh"
        properties: {}
        artifact: "artifacts/android/app.apk"
        app-id: "com.example.app"
```

When script is omitted, CIMT uses its installed default. A CIMT update replaces supplied defaults and preserves separate user-customized copies.

CIMT supplies a result-file path to the script. A successful script writes JSON such as:

```json
{
  "artifact": "/absolute/path/to/app.apk",
  "app-id": "com.example.app"
}
```

Build logs remain separate from the result file. Script-returned values take precedence per field; YAML artifact/app-id values supply missing fields. A successful script may omit the result file when YAML supplies both values. Invalid returned values are reported rather than silently replaced by YAML. The returned artifact path is absolute; the YAML fallback resolves from the clone root. CIMT installs the matching build on each compatible startup device. The [build contract](build-script-contract.md) defines the implemented environment and JSON request/result handoff.

A build target failure is reported while other targets continue. It produces final exit code 3.

## 9. Additional reset commands

CIMT performs the platform reset before each scenario. Optional reset.command and reset.verify-command augment that reset for app/backend state and verification. Commands receive the current target, device, and app identifier through environment variables; they are CIMT_TARGET, CIMT_DEVICE, and CIMT_APP_ID. See [run-engine notes](run-engine.md) for the current reset limits.

Exit code 0 means success. Any other exit code stops the run and produces a report. Reset completion must be verified; setup and login repeat when needed.

External equipment is prepared manually. Missing equipment skips dependent scenarios, explains why, and permits remaining scenarios to continue.

## 10. Testing instructions

A useful instruction file states the objective, expected results, exact steps when necessary, permitted exploration, equipment dependencies, and failure rules. Example:

```text
Objective: investigate crashes in seat configuration.

Exact scenario:
Open seat configuration.
Select the options listed in the bug description.
Save, reopen, and verify the selected values remain.

Exploratory scenario:
Explore other seat configurations and repeated saves.

Expected:
The app remains running and saved values are retained.

Equipment:
A prepared test seat controller is required.
Skip equipment-dependent scenarios if it is unavailable.

Failure criteria:
An app crash or loss of a successfully saved configuration is a failure.
```

This is an input example, not a bundled demo app or mandatory text grammar. AI may divide instructions into scenarios when boundaries are not specified. It records ambiguity and its interpretation without asking questions.

Instructions override conflicting requirements. Mark affected requirements overridden and explain the conflict. Default failure criteria apply when the instructions do not supply them.

## 11. Limits, crashes, and outcomes

The time limit covers the whole run. The AI budget is shared across workers. Before each request, reserve the maximum possible charge; if insufficient budget remains, stop incomplete, potentially below the cap. Reporting is local and requires no final AI call.

CIMT relaunches after a crash. Three consecutive matching crashes cancel only the scenario. Matching uses scenario/action or screen, with a matching crash signature when available; a successful retry resets the counter. AI chooses other reproduction effort within limits.

Device disconnection or a blocking AI/infrastructure failure stops execution and generates a report. Unclear instructions continue with recorded interpretation. No startup devices means stop/report.

Without instruction-specific failure rules: confirmed requirement failures or app crashes mean failed; unfinished/inconclusive testing means incomplete; otherwise passed. Reports separately retain test verdict, completion, and execution errors.

| Exit code | Meaning |
| --- | --- |
| 0 | Complete and passed. |
| 1 | Confirmed test failure. |
| 2 | Incomplete/inconclusive without confirmed failure. |
| 3 | Configuration/infrastructure error, including failed build targets after other targets continue. |

Precedence when conditions coexist: **3 → 1 → 2 → 0**. All observations remain in the report.

After power loss or forced termination, next-launch recovery removes abandoned CIMT-owned clones, preserves existing evidence/reports, and records the interruption.

## 12. Reports and replay

One HTML report groups observations by build target, device, and scenario. It records branch/commit, build/device details, redacted effective configuration, coverage, observations, expected results, attempts, crashes, ambiguities, overrides, diagnostics, and stopping/cleanup details.

| Requirement result | Meaning |
| --- | --- |
| Passed | Evidence supports the expected behaviour. |
| Failed | Evidence contradicts the effective expectation. |
| Not tested | Not evaluated; explanation provided. |
| Inconclusive | Attempted but evidence cannot establish pass/fail. |
| Overridden | Conflicting instructions took priority; explanation provided. |

Every meaningful device action or check is a step with its result and a screenshot afterward. Credentials are masked. Internal AI reasoning/build operations are logged separately. Missing evidence must be disclosed.

Keep the whole report folder when copying or archiving; evidence/actions/logs use relative references so the folder remains useful after clone deletion.

Replay loads saved scenario objectives, expected results, and action history, then uses current repository/branch/build settings and credentials. It resets/setup/logs in, uses the same device/time/budget/crash rules, and creates a new report leaving the original unchanged. Navigation may adapt; record all deviations. Mark inconclusive if adaptation cannot preserve original meaning.

## 13. Examples, demos, and Jenkins

Every command and build/reset integration requires documentation plus runnable demonstrations covering configuration, invocation, expected output, and failures. Demos use a **user-supplied application repository** and secret placeholders. No demo MAUI application will be included.

The current examples document the interface. validate has been exercised against the supplied repository and connected devices, and build workers have simulated contract checks. Successful application builds and end-to-end setup/run/replay/reset demos remain pending; no sample configuration contains real credentials.

Jenkins invokes the same CLI on the Intel Mac account with device/toolchain access. It retains/archives the entire local report folder as pipeline configuration directs. Pipeline scheduling must respect the single-run-per-Mac rule.

Illustrative pipeline command:

```text
cimt run --config /private/path/default.yaml --run-config /private/path/nightly.yaml
```

Use the approved exit codes for pipeline results and preserve reports even on failure. Concrete Jenkins labels, artifact collection, service account, and toolchain versions remain environment-specific.

## 14. Readiness and remaining decisions

Demonstrate setup on a second Intel Mac and two build targets on a physical Android phone and iPhone. See [acceptance criteria](requirements.md#7-first-release-acceptance-criteria).

Reviewed CLI responsibilities, YAML fields, path rules, script/result contracts, validation/replay behaviour, and masking scope are approved. Final adapter selection, a supported compatibility matrix, full schema constraints, live reset/credential/billing verification, complete scenario/replay/setup engines, and release acceptance remain pending. The installed prerequisite profile and initial execution paths are recorded in the implementation documents.

## Review record — version 0.3

This revision records the product owner's command/configuration approvals and corrections. ai-model/ai-budget are separate, default scripts belong to the CIMT installation, run folders use work_/report_ timestamps, masking uses element IDs only, and examples/demos use a user-supplied app. No software was installed or replaced.

## Current command/build implementation

Activate /Users/Shared/CIMT/environment.sh, then run cimt --help or cimt validate with real private YAML. Placeholder keys/models are rejected. validate checks credential presence only; it makes no paid AI calls and does not verify provider access, application signing, or behaviour.

Default scripts are installed in /Users/Shared/CIMT/scripts/build. The [build contract](build-script-contract.md) now defines their JSON request/result environment handoff. Source examples are in examples/default.example.yaml and examples/econ-app.example.yaml. They contain no secrets and no bundled demo app.

Use the [step reviews](implementation-status.md) to distinguish implemented foundations, blocked validation, and remaining product work.

The [button/crash example](../examples/econ-button-crash/README.md) contains both build targets, platform settings, instructions, requirements, setup notes, and application-specific macOS build support. Its public cimt run invocation uses the configured main branch. Reports and disposable work are local subfolders of that example. The existing API key belongs in ignored, owner-only default.private.yaml, never the tracked template.

The current run engine performs one objective per target/device, with at most two devices active. It reports observed controls, attempted controls, remaining paths, screenshots, and confirmed or suspected terminations. It cannot promise to reach hidden or equipment-dependent buttons. Limits and blocking conditions produce incomplete reports. Only the documented model snapshot/USD profile is currently supported; other models need a validated pricing bound before use. See [run-engine limits](run-engine.md).


The internal code now uses smaller services, simple English comments, and replaceable dependencies for unit tests. This does not change the operator commands or configuration. Development rules and checks are described in the [development guide](development.md).

The current worker records explicit instruction/requirement checks with expected behavior, observed behavior, status, and evidence. A functional failure affects the verdict even without a crash. Navigation completion alone cannot pass. The host catalogue now accounts for every supplied nonblank source item. Every applicable target/device pair has a status, evidence, or an explanation of missing evidence. Items with several conditions require all conditions to be checked; use separate paragraphs/list items when separate decisions are needed. Unknown or ambiguous items remain unresolved rather than being dropped. See [complete mapping rules](requirement-mapping.md) and the [runnable offline example](../examples/requirement-mapping/README.md). Real-app mapping acceptance remains pending.
