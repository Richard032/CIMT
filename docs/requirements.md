# CIMT requirements

Version: 0.4  
Date: 28 October 2026  
Status: requirements, reviewed architecture policies, and reviewed command/YAML contracts confirmed; implementation validation pending  
Product: CIMT — Curtis Intelligent Mobile Test

## 1. Source and authority

This document records decisions from the product-owner interview. Requirements using “shall” are confirmed product expectations, not claims of implemented functionality. Architecture proposals do not become product requirements without review.

Later answers refine earlier answers. In particular: build failures continue other targets; app crashes follow scenario recovery rules; the first release tests one branch; the host is an Intel Mac.

The project repository is [Richard032/CIMT](https://github.com/Richard032/CIMT). Documentation, setup scripts, and product source code belong there.

## 2. Problem and objective

Developers already have a complicated automated validation system, but lack a fast tool for everyday testing. CIMT shall complement that system by accepting requests such as “test seat configuration for crashes,” investigating a bug description, and checking application behaviour against requirements after changes.

Users are developers testing during daily work and Jenkins pipelines executing nightly tests. CIMT shall operate without runtime questions and produce evidence of observed behaviour.

## 3. Scope

The initial release covers any .NET MAUI application configured for Android and iOS, single-branch testing, local execution on Intel Macs, and connected physical devices.

App independence means application details are supplied through configuration and text inputs rather than hardcoded product logic. It does not mean every possible hardware-dependent behaviour can be automated without preparation.

Two-branch before/after comparison is a later requirement. Apple Silicon hosts, simulator/emulator support, cloud device hosting, a graphical interface, authenticated web input retrieval, automatic equipment preparation, and video recording are not committed initial-release requirements.

## 4. Functional requirements

### Invocation and configuration

| ID | Requirement |
| --- | --- |
| FR-01 | CIMT shall expose a terminal command. Jenkins pipelines shall execute that same command on the Mac build server. |
| FR-02 | CIMT shall install once per Mac and support multiple application repositories. Only one CIMT run may be active per Mac. |
| FR-03 | Configuration shall use YAML. Precedence shall be default YAML, then per-run YAML, then terminal arguments. Later values override earlier values. Nested mappings shall merge, lists shall be replaced completely, and relative file paths shall resolve from their declaring YAML file. Unknown keys and invalid values shall be rejected before building or testing. |
| FR-04 | Application configuration shall define repository URL, branch, solution path, build targets, app identifiers, and custom build commands as needed. Build targets are configurable; Release_Generic and Release_Pride are examples only. |
| FR-05 | Testing instructions, application requirements, and setup shall be separate text inputs accepting local paths or unauthenticated web links to text content. Instructions are required; requirements and setup are optional. General web-page extraction is not confirmed. |
| FR-06 | Model selection, AI spending limit, whole-run time limit, report contents, and application setup shall be configurable. Configuration shall support reuse and per-run overrides. An explicit model, whole-run time limit, and AI budget are mandatory in the effective configuration; missing or invalid values shall stop execution before testing and generate an error report. |

### Repository and build

| ID | Requirement |
| --- | --- |
| FR-07 | CIMT shall clone a repository from a Git URL. Private repositories shall use Git authentication already configured on the Mac, without interactive login during execution. |
| FR-08 | Clones shall live under the configured common working root in a temporary work_<date-time> folder. CIMT shall delete its run clone after successful, failed, incomplete, or interrupted execution. Reports and evidence shall survive cleanup. |
| FR-09 | CIMT shall build every configured target and test it on every connected compatible device. A target build failure shall be reported while other build targets continue. |
| FR-10 | The report shall identify the branch and resolved commit used, build target, and tested device so findings can be traced to an execution. |

### Devices and scenarios

| ID | Requirement |
| --- | --- |
| FR-11 | CIMT shall discover supported connected physical Android and iOS devices at startup and use all of them without separate CIMT registration. Both platforms need not be present. Newly connected devices shall not join the active run. |
| FR-12 | At most two devices shall be tested simultaneously. Additional devices shall be queued. Every compatible target/device combination shall be covered unless execution is stopped or limited. |
| FR-13 | No connected devices shall cause CIMT to stop and generate a report. |
| FR-14 | CIMT shall follow exact scenarios when requested and explore creatively when permitted. AI may divide instructions into scenarios unless the input explicitly defines the boundaries. |
| FR-15 | Before each individual scenario, CIMT shall reset application data and repeat setup/login if needed. Setup instructions and test credentials shall be application inputs. CIMT shall use platform reset capabilities and support application-specific reset commands for additional state, verify reset completion, and stop the run with a report if reset fails. |
| FR-16 | CIMT may reinstall/reset the app, delete test data, and change device settings automatically. External Bluetooth, USB, or other equipment shall be prepared manually. |
| FR-17 | Unavailable external equipment shall cause affected scenarios to be skipped with an explanation; remaining scenarios shall continue. |
| FR-18 | CIMT shall never ask runtime clarification questions. It shall record unclear instructions, its interpretation, and continue using that interpretation. |
| FR-19 | Testing instructions shall take precedence over conflicting requirements. The report shall mark the affected requirement overridden, explain the conflict, and judge execution against the instructions. |
| FR-20 | AI shall choose reproduction attempt counts according to complexity, subject to run limits and the fixed crash rule. |
| FR-21 | After a crash, CIMT shall relaunch the app and continue. Three consecutive matching crashing attempts shall cancel only the affected scenario. Matching shall use the same scenario and action or screen, with a matching crash signature when available. A successful retry shall reset the consecutive-crash counter. Other scenarios shall continue. |
| FR-22 | CIMT shall record performed actions for later replay. Replay shall preserve the original objective and expected results while adapting navigation and element selection to UI changes. The report shall preserve actual actions and every deviation; a replay that cannot preserve the test's meaning shall be inconclusive. |

### AI, reporting, and results

| ID | Requirement |
| --- | --- |
| FR-23 | CIMT shall use OpenAI. Screenshots, UI text, requirements, and relevant source code may be processed by the cloud AI service, with credential redaction as required below. |
| FR-24 | A strict AI spending limit shall apply across the entire run, including concurrent device workers. CIMT shall reserve the maximum possible cost before each request and shall not issue a request the remaining budget cannot cover. Conservative early stopping is accepted. |
| FR-25 | A configurable time limit shall apply to the entire run. CIMT shall also support completion based on coverage of all testing instructions. Exhausting time or budget with work outstanding shall stop testing and produce an incomplete result. |
| FR-26 | CIMT shall generate one local HTML report, grouped by build target, device, and scenario, with observed behaviour and evidence. |
| FR-27 | Every supplied requirement shall have a result and supporting evidence or an explanation of why evidence is unavailable. Results shall include passed, failed, not tested, inconclusive, and overridden. Explicit Markdown document headings shall be retained as source context with their text and line numbers; they shall not receive requirement IDs or test statuses and shall not block completion. |
| FR-28 | A test step shall be a meaningful device action or check, with its result and a screenshot captured afterward. Credentials shall be masked. Internal AI reasoning and build operations shall be logged separately from test steps. Evidence collection failures shall be disclosed rather than silently omitted. |
| FR-29 | Reports shall include unclear instructions and interpretations, reproduction attempts, crashes, skipped/cancelled work, and relevant diagnostics. Report contents shall be configurable; disabling optional sections shall not misrepresent coverage or hide the final outcome. |
| FR-30 | Each run shall have a retained report_<date-time> folder using the same timestamp as its temporary work_<date-time> folder, outside the temporary cleanup folder. Screenshots and recorded actions shall remain in subfolders beside the report. The folder shall be portable and archivable. Reports shall remain until manually deleted. |
| FR-31 | Testing instructions shall define failure criteria. In their absence, confirmed requirement failures or app crashes mean failed; unfinished or inconclusive testing means incomplete; otherwise passed. |
| FR-32 | Blocking infrastructure failures, including device disconnection or AI service unavailability, shall stop the run and generate a report. This rule has explicit exceptions for failed build targets, recoverable app crashes, unclear instructions, and unavailable external equipment. |

### Mac provisioning and credentials

| ID | Requirement |
| --- | --- |
| FR-33 | The project shall deliver a reusable setup script plus configuration sufficient to prepare supported Intel Macs for local CIMT execution. |
| FR-34 | Setup shall use a tested compatibility manifest with pinned tool versions, reuse compatible installations, and automatically replace incompatible CIMT-required tool versions without confirmation. It shall install missing dependencies where possible, support reruns after interruption, report installed/replaced components and validation results, and provide step-by-step manual instructions where automation is unavailable. It may request administrator privileges; ordinary test runs shall operate without them. |
| FR-35 | Secrets, including the OpenAI key, app credentials, and signing-related configuration, shall be supplied through YAML configuration. Private Git authentication remains host-managed under FR-07. |
| FR-36 | CIMT shall restrict access to secret configuration and redact credentials from logs, reports, and AI requests. Login credentials shall remain in private YAML and shall be entered directly through device controls without sending their values to AI. CIMT shall mask secrets in screenshots and UI text before saving or sending them, support application-specific YAML masking rules using element IDs only (no screen regions), and stop with a report if required masking cannot be applied reliably. |

### Approved implementation and recovery policies

| ID | Requirement |
| --- | --- |
| FR-37 | CIMT shall be a local .NET command-line application with a shell setup script and interchangeable device-control adapter. Host code shall enforce concurrency, time/spending limits, crash recovery, and cleanup; OpenAI shall interpret inputs and choose testing actions. Reports shall be generated locally even when AI is unavailable. |
| FR-38 | CIMT shall track ownership of temporary clones. After hard termination or host power loss, its next launch shall detect interrupted runs, remove their abandoned clones, preserve evidence/reports, and record the interruption. Only CIMT-owned temporary folders may be deleted. |

### Approved command, configuration, and build contracts

| ID | Requirement |
| --- | --- |
| FR-39 | CIMT shall expose setup, validate, run, and replay commands with the reviewed options documented in the product guide. Setup prepares the Mac, run builds/tests, and replay executes a saved scenario. |
| FR-40 | Configuration shall use setup.yaml for installation/toolchain settings, default.yaml for shared settings, and app.yaml as a reusable application/per-run override. ai-model and ai-budget shall be separate sections. The reviewed fields are specified in the product guide. |
| FR-41 | CIMT shall provide default Android and iOS build scripts in its installation. These scripts shall be created and validated during the first real test runs. The tested repository shall require no modifications. Users may customize scripts or configure replacement script paths. Updates replace supplied defaults while preserving separate user copies. |
| FR-42 | Build targets shall define name, configuration, application project, per-platform target framework, additional build properties including signing, and optional replacement script. Default scripts shall locate and return the installable artifact and app identifier. |
| FR-43 | CIMT shall supply a build-result file path to scripts. A successful script shall write JSON containing artifact and app-id, or the user shall provide those fields in platform YAML. Script-returned values take precedence; YAML supplies missing fields. |
| FR-44 | Project paths and YAML artifact paths shall resolve from the cloned repository root. Local input paths, replacement/reset script paths, and other relative configuration file paths shall resolve from the declaring YAML file's folder. Default scripts shall resolve from the CIMT installation. Absolute paths shall be supported where applicable. |
| FR-45 | Optional reset.command and reset.verify-command shall augment platform reset. CIMT shall supply target, device, and app identifier through environment variables. Exit code 0 means success; any other code stops the run and generates a report. |
| FR-46 | Credentials shall be named entries with username/password in private YAML. Setup text may reference a credential name. CIMT shall resolve values locally; recorded actions shall retain credential references rather than secret values. |
| FR-47 | Validate shall check YAML, required values, paths/text accessibility, Git access and branch, tool/device readiness, credential presence, and model/budget configuration without building, installing, resetting apps, or paid AI calls. It shall generate local HTML. Actual login, signing, and model access are verified during execution. |
| FR-48 | Replay shall use the current repository/branch/build configuration plus a saved scenario's objective, expected results, and history. It shall reset/setup/login, use current credentials, apply normal device/time/budget/crash rules, produce a new report, and leave the original unchanged. |
| FR-49 | Reports shall always include summary, outcome, coverage, and stopping reasons. reports.sections shall select detailed sections; screenshot and saved-action collection remain mandatory. Device discovery policy, maximum two-device concurrency, and per-scenario reset are fixed behaviour rather than optional execution switches. |
| FR-50 | setup.yaml shall support installation.root, toolchain.manifest, and optional validation.config/run-config for an application-readiness check without building/testing. |
| FR-51 | Every command, supplied/replacement build script, reset command, and reset verification shall have documented examples and runnable demonstrations explaining configuration, invocation, expected output, and failure behaviour. Demos shall use a user-supplied application repository with secret placeholders; CIMT shall not include a demo MAUI application. |

## 5. Outcomes and exceptional conditions

These rules distinguish a test finding from an inability to execute. Instructions may customize test failure criteria, but cannot turn unexecuted work into a verified pass.

| Condition | Required behaviour |
| --- | --- |
| Ambiguous instruction | Record interpretation and continue; do not ask questions. |
| Requirement overridden by instruction | Mark overridden and assess the instruction. |
| App crash | Capture evidence, relaunch, continue; cancel affected scenario after three consecutive matching same-point crashing attempts; a successful retry resets the counter. |
| Build target fails | Record failure and continue other targets. |
| Equipment unavailable | Skip dependent scenarios, explain, and continue. |
| No devices at startup | Stop and report. |
| Device disconnect / blocking AI or infrastructure failure | Stop run and report partial execution. |
| Time or AI budget exhausted | Stop and report incomplete execution. |
| User interruption | Stop execution, preserve/report observations where possible, and delete run clone. |

Run results shall contain separate test verdict (passed, failed, inconclusive), completion (complete, incomplete), and execution-error fields. For example, a confirmed failure followed by timeout is failed + incomplete.

| Terminal exit code | Meaning |
| --- | --- |
| 0 | Complete and passed. |
| 1 | Confirmed test failure, without an execution error taking precedence. |
| 2 | Incomplete or inconclusive testing without a confirmed failure or execution error. |
| 3 | Configuration or infrastructure error; a failed build target also produces this code after other targets have run. |

Exit-code precedence is **3 → 1 → 2 → 0**. All findings and completion details remain visible in the report.

## 6. Nonfunctional expectations

- Execution shall require no human input after invocation.
- A device's actions and observations shall remain isolated from other device workers.
- A run shall retain enough traceability to review findings after its clone is deleted.
- Setup shall diagnose unsupported host/toolchain combinations rather than claim success.
- Cleanup shall delete CIMT-owned run clones only, not unrelated repositories.
- Secrets shall not appear in retained configuration snapshots, saved screenshots/UI text, or AI inputs. Masking must be validated; required masking failure stops the run.
- The first release shall not claim complete bug discovery or deterministic AI judgment.
- Supported macOS, Xcode, .NET, device OS, and device-control versions require validation and a published compatibility matrix.

## 7. First-release acceptance criteria

| ID | Demonstration |
| --- | --- |
| AC-01 | Install/configure CIMT on a second supported Intel Mac using the delivered script, configuration, and manual instructions. Run ordinary tests without administrator privileges. |
| AC-02 | Clone a private MAUI repository using existing host Git credentials and test one branch with two configured build targets on a physical Android phone and iPhone. Verify all four compatible target/device combinations. |
| AC-03 | Demonstrate two devices executing concurrently and a third connected device queued. A device connected after startup is excluded. |
| AC-04 | Execute an exact scenario and an exploratory request from text files without runtime questions. Record an ambiguous instruction and its interpretation. |
| AC-05 | Reset data and perform necessary setup before each scenario; verify state does not leak between scenarios. |
| AC-06 | Reproduce a same-point crash three times, cancel only that scenario, and continue another scenario. |
| AC-07 | Fail one build target while continuing another. Separately demonstrate an infrastructure failure stopping the run and producing a partial report. |
| AC-08 | Demonstrate whole-run timeout and strict shared budget reservation, including two workers competing for the final available budget. No unfunded request is sent. |
| AC-09 | Produce all five requirement statuses, including a documented instruction/requirement conflict and an inconclusive check. |
| AC-10 | Verify screenshots for each executed step, persisted actions, and an adaptive replay that records deviations. |
| AC-11 | Copy a run folder to another location and open its report and evidence without the cloned repository. Confirm credentials are absent. |
| AC-12 | Verify clone cleanup after success, failure, timeout, and graceful interruption; retain reports. Verify a second CIMT invocation cannot start while one owns the Mac. |
| AC-13 | Invoke the same CIMT command from a Jenkins pipeline under the server account and verify exit codes 0/1/2/3 and precedence 3 → 1 → 2 → 0, including build failure continuation. |
| AC-14 | Verify nested mapping merge, list replacement, relative paths, and rejection of unknown keys, invalid values, or missing explicit model/time/budget before testing. |
| AC-15 | Verify reset failure stops the run, required masking failure stops the run, and a successful crash retry resets the consecutive-crash counter. |
| AC-16 | Simulate an abandoned run; verify next-launch cleanup only removes CIMT-owned clones, preserves evidence, and records interruption. |
| AC-17 | Verify compatible tools are reused, incompatible required tools are replaced without confirmation and recorded, and interrupted setup can resume. |
| AC-18 | Replay a saved scenario with UI changes; verify current configuration/credential use, recorded adaptations, a new report preserving the original, and inconclusive output when meaning cannot be preserved. |
| AC-19 | Demonstrate setup/validate/run/replay and script/reset examples against a user-supplied MAUI repository, with no bundled demo app. |
| AC-20 | Verify validate creates HTML without build/install/reset or paid AI requests, while checking Git branch, inputs, dependencies, and startup-device readiness. |
| AC-21 | Verify installed default build scripts require no tested-repository changes, custom copies survive a CIMT update, and script-result JSON overrides YAML artifact/app-id fallbacks per field. |
| AC-22 | Verify work_<date-time> and report_<date-time> share a timestamp, report placement survives cleanup, and approved path resolution works for local and Jenkins configuration. |
| AC-23 | Verify element-ID-only masking rules, named credential references, and failure on a required mask that cannot be applied reliably. |
| AC-24 | Supply Markdown headings and a testable requirement. Verify headings remain visible as context, the requirement retains its source lines and section meaning, and a passed requirement can complete without evaluating headings. Verify a heading-only document creates no requirement results. |

## 8. Later release: branch comparison

CIMT shall compare two Git branches, run the same instructions on both unless text inputs specify otherwise, reset application data between branch executions, and report new, resolved, and unchanged observations. This capability is intentionally outside initial-release acceptance.

## 9. Remaining review and validation

Reviewed command syntax and YAML fields are recorded in the product guide. Remaining details include unreviewed options, full schema constraints, build/reset environment variable names, build-result handoff mechanics, manifest schema, supported version matrix, supported currencies/pricing validation, report implementation, cross-device replay portability, packaging, and installer dependency management. Explicit effective model/time/budget values are required; no unlimited fallback is permitted. Merge semantics, exit codes and precedence, .NET implementation, reset/masking failure policy, crash matching policy, adaptive replay, recovery cleanup, and tool replacement are approved. Their implementation still requires validation. No performance target or fixed bug-discovery guarantee has been agreed.

## Review record — version 0.2

The product owner confirmed the reviewed requirements and architecture policies on 27 October 2026. This revision records those approvals; it does not claim implementation or approve the illustrative CLI/YAML interfaces. No tools were installed or replaced as part of this documentation update.

## Review record — version 0.3

The product owner approved the command/configuration review, default and replacement build scripts, script result precedence, named credentials, element-ID-only masking, validate/replay scope, setup fields, timestamped work/report folders, and examples/demos using a user-supplied app. This records the design; no executable implementation or demo application is delivered in this revision.

## Review record — version 0.4

On 28 October 2026, the product owner requested the document-heading correction identified in the design review. FR-27 and AC-24 now distinguish explicit Markdown headings from test expectations. The five evaluation statuses remain unchanged. Plain prose, table classification, and platform applicability are not resolved by this clarification. See [mapping rules](requirement-mapping.md) for supported heading forms.
