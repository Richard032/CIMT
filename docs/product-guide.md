# CIMT product documentation

Version: 0.36
Date: 1 November 2026  
Status: reviewed product behaviour, command responsibilities, and YAML fields approved  
Product: CIMT — Curtis Intelligent Mobile Test

**validate, default build workers, and an initial single-objective run engine are implemented. User-started real-app runs have exercised device interaction; full end-to-end acceptance remains open. setup and saved-action-history replay remain unimplemented; replay without --scenario reuses built apps for current instructions. See the [implementation status](implementation-status.md), [installation guide](installation.md), and [runnable main-branch example](../examples/econ-button-crash/README.md). Private keys are supplied locally; none are bundled.**

## 1. Purpose and environment

CIMT supports everyday testing of any configured .NET MAUI application. Developers invoke a terminal command; Jenkins pipelines invoke the same command on their Intel Mac execution node.

Give CIMT a Git repository/branch, configurable build targets, plain-text testing instructions, and optional requirements/setup inputs. CIMT builds the app, operates selected physical or virtual devices, and generates local HTML observations with evidence. It complements the existing validation system; AI exploration does not guarantee complete bug discovery.

One installation serves multiple repositories, with only one active run per Mac. All supported devices connected at startup participate, at most two simultaneously. New connections are excluded. Both platforms need not be present.

OpenAI supplies reasoning in the cloud. Device operation and report storage are local. App backends and external equipment are prepared separately.

## 2. Approved commands

```text
cimt setup --config setup.yaml
cimt validate --config default.yaml --run-config app.yaml
cimt run --config default.yaml --run-config app.yaml
cimt run --config default.yaml --run-config app.yaml --branch feature-to-test
cimt replay --config default.yaml --run-config app.yaml
```

| Command | Responsibility |
| --- | --- |
| setup | Prepare the Mac from installation settings and tested toolchain manifest; optionally validate a configured application's readiness. |
| validate | Check configuration, required values, paths/text inputs, Git access/branch, tool/device readiness, credential presence, and model/budget configuration. Produce local HTML without build, installation, reset, or paid AI calls. Actual login, signing, and model access are verified during execution. |
| run | Clone, build configured targets, and execute testing instructions on startup devices. |
| replay | Reuse the latest retained app builds for these inputs, execute current text instructions, and create a new report without Git or builds. Saved-action-history replay remains unfinished. |

The reviewed syntax above is approved. Additional flags, help output, configuration discovery, and detailed process contracts still require specification. CIMT asks no runtime clarification questions about test instructions. Optional execution checkpoints described below ask only for operational acknowledgement.

## 3. Configuration files and precedence

| File | Contents |
| --- | --- |
| setup.yaml | Installation root, toolchain manifest, optional application-readiness validation. |
| default.yaml | OpenAI model/key, run time limit, AI budget, and shared reporting settings. |
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
reports:
  sections:
    - requirements
    - scenarios
    - findings
    - interpretations
    - diagnostics

execution:
  time-limit-minutes: 60
  interactive-pauses: false

ai-model:
  name: "<validated-model>"
  api-key: "<private-key>"

ai-budget:
  amount: 5.00
  currency: USD
```

The time/budget values are illustrative. Current supported profiles are gpt-5.4-mini-2026-03-17 and gpt-5.6-luna, with USD accounting and validated conservative pricing bounds. Strict budget enforcement is mandatory, with no disable switch. See [model selection](#select-the-ai-model).

reports.sections selects detailed sections. Run summary, final outcome, coverage, and stopping reasons always remain visible. Step screenshots and saved actions are always collected.

All-startup-device selection, at-most-two device concurrency, and reset before every scenario are fixed behaviour, not optional execution switches.

### Interactive pauses

To display the next operation and wait for your acknowledgement during a local run, add this to the per-run YAML:

```yaml
execution:
  interactive-pauses: true
```

Use the same command:

```bash
cimt run --config ./default.private.yaml --run-config ./application.yaml
```

CIMT displays generic information at three points:

| Before | Information shown |
| --- | --- |
| OpenAI model access | CIMT will check model access using the configured API key. No inference is requested in this check. |
| Repository access and builds | CIMT will access the repository and build the application, including Git, submodules, and package restore. |
| AI testing, if a build succeeded | CIMT will use OpenAI and the configured API key to test the application. AI requests may incur charges. |

Each message is followed by: `Press Enter to continue. Waiting counts toward the run time limit.` Complete any preparation you need, then press Enter. CIMT does not prescribe network names or changes. The key remains in ai-model.api-key and is loaded locally at startup. It is never displayed; authenticated OpenAI requests wait for acknowledgement. Terminal response text is not recorded.

Waiting uses the normal whole-run time limit. Deadline expiry stops the run and reports incomplete work with normal exit precedence. Closed terminal input stops with an infrastructure error. Enabled pauses reject redirected input rather than continue automatically. The final checkpoint is skipped if no build succeeded. validate has no run-stage checkpoints.

Omit the setting or use false for unattended execution, including Jenkins. This is the default and reads no terminal input. The public ECON example enables interactive pauses; disable them in the Jenkins per-run YAML. The former execution.network-switch-pauses field has been replaced by execution.interactive-pauses. Public examples and FirstRun have been updated; migrate any separate copied configurations.

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

Redaction removes credential values from observations and text before JSON/HTML encoding. It preserves test statuses, generated IDs, numbers, and evidence links, including when their characters happen to match a credential. Screenshot masking searches original UI strings, including Unicode and escaped characters, and masks nested text in sensitive elements. See [redaction behavior and verification](redaction.md).

Screenshots use lossless PNG and are masked before storage or AI processing. CIMT rejects unreliable bounds, changed screen dimensions, and ambiguous image mapping. Masked containers also hide child UI text. Output removes image metadata and hidden transparent pixels. No screen-region setting is needed. See [screenshot masking and acceptance limits](screenshot-masking.md).

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

CIMT can be launched from any folder using the installed command. Supply only configuration, text inputs, and any custom scripts. Do not create work, reports, or evidence folders. The input folder is the folder containing --run-config, or --config when no run override is supplied. For example:

```text
FirstRun/
  default.private.yaml
  application.yaml
  inputs/
  build/                                   # only if custom scripts are needed
  CIMT output/                             # CIMT creates everything below here
    work/work_2026-10-29_14-30-00-123/       # retained until a later clone
    reports/report_2026-10-29_14-30-00-123/  # retained
```

Both use the same UTC timestamp with millisecond precision. A collision advances both names together by one millisecond; it never adds a separate suffix, reuses existing data, or changes the actual start/deadline. run-identity.json retains the paired names and identity beside the report. See [run identity](run-identity.md). Reports sit outside work replaced before a later clone. Work, publish folders, and intermediates remain after execution. Earlier verified owned work for these inputs is removed only immediately before the next clone. Validation, preflight failure, and replay do not clear it. Reports remain until manually deleted.

Legacy workspace.root/reports.root values still load but are ignored. CIMT prints a notice and records this in output-layout.json. reports.sections still selects report content. Missing/invalid YAML errors also stay below the selected input folder. If CIMT cannot safely write there, it reports the failure in the terminal instead of creating output elsewhere. Invalid command syntax without a selected input uses the launch folder. Installation tools and the machine-wide lock remain with the installation.

Long input paths need no manual shortening. CIMT manages the helper's short transport address automatically and keeps its actual files inside the output tree. Helper failures include redacted diagnostic details; available helper logs remain in the retained report after cleanup.

## 8. Default and replacement build scripts

Default Android/iOS build scripts are implemented and installed. Their simulated request/result checks pass; actual application build acceptance remains open. The example wrappers delegate to the installed defaults without editing project files; both the earlier tagger override and resource-copy replacement have been removed. See the [build contract](build-script-contract.md). Replacement scripts are supported by the initial run engine; public-command fallback handling has regression tests. See [implementation status](implementation-status.md) for the remaining real-app acceptance work.

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

The AI chooses ordinary interactions using the latest screen, earlier observations, its plan or expected app behavior. A tap is not restricted to a control listed or enabled in the latest UI tree. CIMT passes the chosen ref or valid coordinates to the adapter; refs can expire or fail to resolve. An answered interaction failure is recorded and returned with the next evidence so the AI can decide what to do next. CIMT does not choose a replacement button. It distinguishes requested targets from observed controls and does not count unmatched requests as observed coverage. Secret credential entry still needs a verifiable maskable field, and supported commands, coordinate bounds, budgets, masking and authorized permissions still apply.

The time limit covers the whole run. The AI budget is shared across workers. Before each request, reserve the maximum possible charge; if insufficient budget remains, stop incomplete, potentially below the cap. Reporting is local and requires no final AI call.

CIMT relaunches after a crash. Three consecutive matching crashes cancel only the scenario. Matching uses scenario/action or screen, with a matching crash signature when available; a successful retry resets the counter. AI chooses other reproduction effort within limits.

Device disconnection or a blocking AI/infrastructure failure stops execution and generates a report. An adapter-reported failure to launch or relaunch the tested app stops only that device; other active and queued devices continue. This applies to both platforms and physical or virtual devices. The final report keeps the failed device's error and partial observations alongside the other devices' results, and the launch error still contributes exit 3. Adapter connection/protocol/timeouts and failed reset verification keep their blocking behavior. Unclear instructions continue with recorded interpretation. No startup devices means stop/report. See the [Execution Stopping Policy](execution-stopping.md).

Without instruction-specific failure rules: confirmed requirement failures or app crashes mean failed; unfinished/inconclusive testing means incomplete; otherwise passed. Reports separately retain test verdict, completion, and execution errors.

| Exit code | Meaning |
| --- | --- |
| 0 | Complete and passed. |
| 1 | Confirmed test failure. |
| 2 | Incomplete/inconclusive without confirmed failure. |
| 3 | Configuration/infrastructure error, including failed build targets after other targets continue. |

Precedence when conditions coexist: **3 → 1 → 2 → 0**. All observations remain in the report.

After power loss or forced termination, a later run recovers the verified owned helper and preserves work. Earlier owned work for these inputs is removed only at a new clone boundary; reports remain.

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

Current replay uses the latest published successful app builds from this input folder with current instructions/requirements/setup and credentials. It performs normal reset/device/AI/masking/limit checks, verifies the original app digests and branch/profile compatibility, and creates a new report with the original build run/commit. It does not clone, restore, or build. Missing or incompatible retained apps fail explicitly. Build-property changes cannot alter an already built app; use run for a new build. Saved-action-history replay under FR-22 is unfinished and --scenario is explicitly rejected. See the [walkthrough](work-retention-and-replay.md).

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

The current run engine performs one objective per target/device, with at most two devices active. It reports observed controls, attempted controls, remaining paths, screenshots, and confirmed or suspected terminations. It cannot promise to reach hidden or equipment-dependent buttons. Limits and blocking conditions produce incomplete reports. The supported USD profiles are gpt-5.4-mini-2026-03-17 and gpt-5.6-luna; other models need a validated pricing bound before use. See [run-engine limits](run-engine.md).


The internal code now uses smaller services, simple English comments, and replaceable dependencies for unit tests. This does not change the operator commands or configuration. Development rules and checks are described in the [development guide](development.md).

The current worker records explicit instruction/requirement checks with expected behavior, observed behavior, status, and evidence. A functional failure affects the verdict even without a crash. Navigation completion alone cannot pass. The host catalogue accounts for requirement entries and retains explicit Markdown headings separately as context. Headings have no test result and do not block completion; their section meaning accompanies each requirement. Every applicable target/device pair has a status, evidence, or an explanation of missing evidence. Items with several conditions require all conditions to be checked; use separate paragraphs/list items when separate decisions are needed. Unknown or ambiguous prose and table rows remain unresolved rather than being dropped. See [complete mapping rules](requirement-mapping.md) and the [runnable offline example](../examples/requirement-mapping/README.md). Real-app mapping acceptance remains pending.

## Project-configured build steps

The selected branch and configured project determine tool integrations, including CuRMiT configured through Visual Studio/MSBuild. CIMT must preserve those steps and imported targets. Application adapters must not force a tool that a branch removed. The ECON example calls the installed default worker without editing the project or build request. It adds no tagger command, Mono dependency, or resource-copy replacement. Platform-specific compatibility must be handled by the application project; original build failures remain visible. See [FR-58/AC-31](requirements.md).

## Build-property and work-retention update

The default worker no longer forces packaging, runtime, or archive settings. YAML properties are forwarded unchanged; remaining values come from the selected project/SDK. Configure installable output explicitly when the project needs it. CIMT reports missing APK/IPA output rather than changing the settings automatically. Existing FirstRun YAML was preserved. See [retained work and replay](work-retention-and-replay.md) for lifecycle, optional explicit properties, replay provenance, and current limitations.

## Detailed run diagnostics

New run/replay HTML reports always include Run overview, Chronological activity, and Failures and stopping reasons. Read these before optional raw diagnostic sections. The overview shows actual build configuration alongside the target label, source identity, UTC times, available builds/devices, and recorded AI request count. The timeline shows operations that started, completed, failed, stopped, or were cancelled, including duration and device/target context. Expand exception details and follow related log links when needed. These sections remain visible even when optional report sections are disabled.

A worker's real error is now carried into the run summary even when its stderr is empty. Infrastructure and masking failures remain distinct from application-test failures. A second device cancelled after a blocking failure has a separate explanation. activity.jsonl, result.json, and related logs remain local with the portable report. An older report has no reconstructed timestamps. Changed mask geometry rejects that frame. Capture now tries up to three fresh frames for screen transitions, then stops if no verified image is possible; invalid masking data still stops immediately. See [diagnostic reporting](diagnostic-reporting.md). Existing command/YAML inputs are unchanged; no extra verbosity option is required.

Remaining/blocked work keeps the latest AI plan even if a scenario stops during preparation, an action, recovery, or a run limit. Incomplete scenarios also show known untested requirement/control counts. If specific tasks are unavailable, CIMT states that the objective is unfinished and coverage is unconfirmed. Completed scenarios clear obsolete pending tasks. This correction applies to new reports; existing reports are preserved.

## Permission dialogs and screenshot availability

An OS permission question is a normal test screen. If it appears while a screenshot is being checked, CIMT discards that changing frame and tries a fresh capture, up to three attempts with 250 ms between attempts. The wait counts toward the run limit. Only verified masked images reach the report or AI. Retry activity is visible in the timeline. Missing/invalid mask geometry, invalid images, tool errors, or a locked device still stop safely.

Accepted screenshots appear with recorded steps. If no screenshot passed verification, the HTML says so and retains the stopping reason. Older rejected captures cannot be recovered; new run/replay execution is needed to collect new evidence. No private YAML change is required.

Permission decisions are controlled by testing instructions. The AI guidance requires explicit authorization to accept or deny an OS request; otherwise a blocking prompt is reported as blocked/incomplete, not a permission-only app failure. Capture retries only collect images and never click dialog buttons. For the local TestRun_SingleDevice_SingleTarget inputs only, instructions now authorize Allow (or its equivalent) for the tested ECON-M application. FirstRun and public example instructions were not given that authorization.

## AI replies and resource feedback

CIMT no longer evaluates response format or stops after three response-correction attempts. The AI receives instructions, requirements, masked evidence, its selected context and available commands. Plan IDs, quotes and reporting fields do not approve device actions. A reply without one readable command is kept as a note and returned with resource feedback; CIMT does not guess a command. HTML shows full redacted replies and resource feedback. Older Unaccepted AI responses sections describe historical runs. Time, spending, cancellation, privacy and real provider/resource failures retain their normal policies. See [AI Resource Exchange](ai-resource-exchange.md).

## Exploration progress and stopping a run

CIMT remembers explored controls, outcomes, untried paths, and the pending plan for each device/target scenario. Each AI request receives a relevant memory summary with current control references. Reports show observed outcomes and the saved exploration memory. An unchanged screen is recorded as such; a successful tap alone does not verify the requested behavior.

After three unchanged attempts, or repeated travel along a path without discovering new paths, CIMT asks the AI to try another route or explain a blocked path. Every renewed signal asks the AI for recovery. There is no fixed recovery-episode or response-format attempt limit; the shared time and spending limits still apply. AI can finish blocked with remaining work. For an intentional repetition, write the count or reproduction task explicitly in testing instructions, for example: “Tap Refresh five times and check for a crash.” The AI must quote that instruction and explain the repeat in its response. No new YAML field is required.

Press Ctrl+C once to stop. CIMT requests cancellation, allows the device worker up to five seconds to finish saving, closes owned helpers, and writes a final incomplete report. Earlier failures remain failures. Work already in flight may be interrupted. Wait for the report path before closing the terminal. Interrupted host stages, device operations and action records show stopped with the user-interruption reason. If observation was interrupted, its outcome states that interruption instead of claiming the screen changed or stayed unchanged. Successful cleanup still shows completed. A connection/pipe failure without a known user stop remains a real failure. Partial observations survive a connection-close error, and earlier failures keep their original outcome. This applies to new execution reports; saved historical reports are unchanged.

You can open index.html while testing is running. CIMT saves a clearly labelled partial report at stage boundaries and updates it about every two seconds during device testing; reload the page to see newer saved observations. The latest AI count comes from the saved budget ledger. If the process is force-killed, the last saved page remains available and explicitly partial. A final report removes that marker. This feature starts with new runs/replays after installation; it does not rewrite the previous interrupted run.

## Execution speed

Recent AI action history now contains compact navigation facts and actual outcomes, with critical failure/override summaries. CIMT keeps the full history and findings in reports. The AI is asked to avoid repeating unchanged not-tested/inconclusive assessments on every step; unresolved catalogue items remain visible in the report. There is no new configuration, model, or API key.

In an offline comparison using the saved run from 30 October, the latest 24 history records decreased from 46,184 to 4,840 serialized bytes (89.5%). This measures the history portion only. It does not establish the same reduction in total request size, cost, or run time. Device actions and screenshot validation still take time. See [performance findings](performance.md).

## Select the AI model

CIMT uses the effective ai-model.name for both access validation during run/replay and testing. To select Luna, change only this existing field in your local configuration, keeping the current API key and ai-budget settings:

```yaml
ai-model:
  name: gpt-5.6-luna
```

This fragment merges with your existing settings; it is not a complete standalone configuration. The supported profiles are gpt-5.4-mini-2026-03-17 and gpt-5.6-luna, both in USD. CIMT does not switch models automatically. The validate command remains a readiness check without provider calls; run/replay check actual access to the configured model without inference before building/testing. Access checks cannot establish every inference capability or account limit.

Strict spending limits remain mandatory. Mini reserves USD 0.309216 and Luna reserves USD 0.5286864 before each inference request. Luna reserves its full context at higher long-context rates, including default cache-write charges. This deliberately large reservation can stop a run early even though a typical request costs much less. Recorded usage settles at conservative rates and ignores cache-read savings; the report is not an exact invoice. No private file or selected model is changed by installing this update. Model quality and real execution speed still need a user-started comparison; multi-step plans and automatic price retrieval are not included.

## Open a run or replay report

New reports use five sections: **Overview**, **Findings**, **Devices**, **Requirements** and **Activity**. Start with the whole-run device/target table. It includes blocked and unstarted combinations, separates actions from recorded steps, and separates confirmed crashes from suspected terminations. No recorded crash is not proof that an application passed.

Follow a failure's recorded-step link to its exact device/scenario record. Step 0 stays step 0. Open a screenshot to use the local viewer, previous/next within the same scenario/evidence type, zoom and Escape/close. Ordinary image links remain available. Missing or unsafe files have explicit explanations. A screenshot is not labelled as an action result unless its record establishes that relationship.

Use the section's device/target/status filters or text search; visible counts and selected scope describe what is shown. Clear filters restores all records. Overview totals always describe the whole run. A direct step link reveals the destination even if an earlier filter hid it. Without JavaScript, all report content and ordinary links remain available; only enhancements are omitted.

Activity holds compact operation/status groups, the complete ordered journal, build provenance, redacted input details and technical downloads. Grouping does not imply that repeated operations were paired or completed. UTC time and durations are readable, with exact timestamps in details. Budget fields distinguish accounted, uncertain and pending conservative costs; they are not a verified provider invoice.

The report opens directly from disk and works offline after its whole folder is moved. No browser service, new YAML field or new key is needed. Existing reports retain their previous layout; a later user-started run/replay creates a new report with this design. No real test is started by opening a report.

Each invocation has its own report:

```text
<input-folder>/CIMT output/reports/report_<date-time>/index.html
```

Use the exact Report path printed when cimt run or cimt replay finishes. A replay creates a new timestamped report folder even though it reuses application builds from an earlier execution. Its own index.html contains all recorded device results and relative screenshot/log links for that replay. Earlier report folders remain unchanged.

Partial snapshots and final output update the index.html inside the same allocated folder. A partial page is labelled until finalization, including after cancellation. Reload that execution's page for newer saved observations. Headers and browser titles identify run versus replay and the execution identity. Early execution errors keep their own command and identity too.

CIMT does not create a shared latest HTML file at reports/index.html. An already open report remains that execution's report; it does not become a later replay. For the reviewed dual-platform replay, open report_2026-10-30_16-43-21-093/index.html inside TestRun_ios_android_SingleTarget/CIMT output/reports.

## Virtual-device execution

The product owner approved Android Emulator and iOS Simulator execution on 31 October 2026. See [the configuration, device abstraction, build differences and Mac preparation](virtual-devices.md). Physical devices remain the default. Use explicit compatible build properties; do not change tested application source. Offline validation and real-run qualification are separate.

### Screenshot mapping tolerance

CIMT accepts a ±5% difference in the ratio between horizontal and vertical image scaling on every supported device. It expands secret masks to cover accepted mapping uncertainty. Larger mismatches still stop testing with an evidence error. Reports distinguish these CIMT evidence failures from verified application failures.


## Instruction-driven plans and application maps

CIMT now uses a separate Test Planning and Exploration layer. Keep using the same terminal/Jenkins commands and input text files. Instructions define the task and permitted exploration; requirements define expected behavior. A focused request such as test language settings must not expand silently to all app features. A broad request can explore discovered reachable paths within the configured limits.

Before an action, the AI must select a concrete goal linked to the instructions or a requirement. The plan and unfinished tasks persist through the scenario. Available input controls and AI-identified visible controls become map candidates. The AI explains whether a discovered path is relevant, blocked or outside scope. Unclassified paths and unfinished relevant work keep the run incomplete; unrelated excluded controls do not force unwanted actions. The original control/state counters are still shown as raw observations, not a completeness percentage.

The map grows while CIMT navigates. It records states, paths, outcomes and last-observed configuration. For example, English and German values can produce separate observed states and checks can evaluate whether a language remains after restart. A remembered setting is not proof of persistence or correct behavior; checks still need observed evidence against your requirements. For a requested persistence check, the restart action closes and reopens the tested app without resetting its data. Known return routes help the AI continue its plan, while every action still uses current screen evidence.

The HTML Devices section includes Testing plan, Discovered application paths and Observed application map. Work status pending/active/blocked/tested is separate from passed/failed/not-tested results. Visiting a screen or tapping a button is not a passed test. The detailed map includes last-observed configuration provenance. Existing reports remain unchanged. See the [generic planning example](../examples/test-planning/README.md). No new YAML field, key or Appium installation is needed for this increment; live application qualification remains separate.

## AI working memory and loop recovery

The AI decides which history to keep in its working context, summarise, omit or retrieve. CIMT keeps complete records locally and never picks a relevant subset or silently trims old history. Instructions and requirements remain authoritative. The AI can recall omitted records without tapping or restarting the app. An oversized selected record payload requests a smaller AI selection; it does not delete evidence.

Every detected unproductive loop requests AI-directed recovery. Repeated-action facts and fresh masked evidence help the AI reconsider its plan and retrieve earlier discoveries. The AI chooses whether to try a revised approach, explain intentional repetition or finish blocked. It can request recovery itself before the repetition counter signals. CIMT does not select a replacement button or reset the app. Renewed loops request renewed recovery instead of stopping after three recovery episodes. Time, budget, cancellation and independent crash/infrastructure policies still apply.

HTML shows AI-selected working context and AI-directed recovery in the device scenario. Run overview includes token/cache usage and request-purpose details when available. Missing provider details remain unavailable; the accounted cost remains a conservative bound. Filtering, recall and recovery also consume the configured budget. No new command, YAML field, API key or model is needed. These changes require the updated runtime; they have not been qualified in a new live run. See [the detailed flow](ai-context-and-recovery.md).

## AI instruction and context responsibility

CIMT keeps Mobile MCP for device control. Before each AI instruction request, the AI Instruction and Context layer refreshes masked UI information and supplies the current human-interface controls, testing instructions, requirements, setup and AI-selected history. Availability flags describe controls; they do not approve the AI's target. Full masked UI evidence remains available alongside the control catalogue.

The layer does not examine AI replies or choose actions. Execution reads and performs the supported command and records its actual outcome. Repetition facts inform the next instruction after an action; they do not block a chosen command. The existing text-command transport remains. FR-99 queues explicit JSON command objects in received order; unreadable text remains a note with resource feedback. This change does not migrate to Appium or function calling. See [AI Instruction and Context](ai-instruction-context.md).


## Device readiness before testing

CIMT now has a separate Device Adapter layer. Before app setup, it can retry the native helper's known device-server startup failure for a cumulative 90 seconds, capped by the run deadline. It repeats only a read-only readiness probe, with one-second waits. Cancellation remains active. The terminal and HTML activity show retries and any final failure. No extra command or YAML setting is needed.

The helper's internal five-second startup limit remains unchanged. Multiple attempts can recover from a temporary problem; this does not let a single attempt run for 90 seconds. Other device failures are not retried automatically. Install/reset, taps, typing, credentials and AI requests are outside startup recovery. After exhaustion, the existing infrastructure stopping policy applies. See [Device Adapter](device-adapter.md).

## Ordered AI commands

The AI can return several commands in one reply. CIMT saves them in a FIFO queue and executes them in the same order, with the normal checks and observations after each device action. If a command cannot execute, CIMT cancels every remaining command and gives AI the failed command, error and cancelled-command count in the next normal decision request. A successful batch continues testing through the normal next-decision request, without an extra success acknowledgement. Recovery can also require a fresh decision. Run-stop/privacy failures can prevent another AI request; their diagnostics remain in the report. The AI can still return one command when it needs to see the next screen before choosing another.

The HTML device scenario shows an AI command queue with batch, order, state, actual step and reason. Queued, cancelled or not-executed commands are plans; they do not prove that a button was tapped or a requirement passed. Cancellation and limits preserve unperformed work. A done command ends the objective, including any commands following it. The complete redacted reply remains available once per batch.

No new user command, YAML field, model or key is required. Install the matching report host and runtime together. Existing reports are unchanged. Offline verification has passed; this increment has not yet been installed or qualified through a live replay. See [command queue](command-queue.md).

## Wait after installation and launch

CIMT waits 20 seconds after successfully resetting, installing and launching an app, before its first screen/foreground checks and AI request. This applies to both platforms and to physical devices and emulators. The activity log shows Wait 20 seconds after app installation and launch.

The wait is inside CIMT. Mobile MCP and its native helper remain unchanged and are already connected for installation. Cancellation and the run deadline remain active; waiting counts toward the time limit. Failed setup does not wait, and normal AI actions or later app restarts do not gain this extra pause. No configuration change is required. A new replay is needed to evaluate whether the delay helps the observed foreground problem.
