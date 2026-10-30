# CIMT requirements

Version: 0.14  
Date: 30 October 2026  
Status: requirements, reviewed architecture policies, and reviewed command/YAML contracts confirmed; implementation validation pending  
Product: CIMT — Curtis Intelligent Mobile Test

## 1. Source and authority

This document records decisions from the product-owner interview. Requirements using “shall” are confirmed product expectations, not claims of implemented functionality. Architecture proposals do not become product requirements without review.

Later answers refine earlier answers. In particular: build failures continue other targets; app crashes follow scenario recovery rules; the first release tests one branch; the host is an Intel Mac.

The project repository is [Richard032/CIMT](https://github.com/Richard032/CIMT). Documentation, setup scripts, and product source code belong there.

## 2. Problem and objective

Developers already have a complicated automated validation system, but lack a fast tool for everyday testing. CIMT shall complement that system by accepting requests such as “test seat configuration for crashes,” investigating a bug description, and checking application behaviour against requirements after changes.

Users are developers testing during daily work and Jenkins pipelines executing nightly tests. CIMT shall interpret testing instructions without runtime clarification questions and produce evidence of observed behaviour. Optional, explicitly configured execution-stage acknowledgements are allowed for local runs; unattended runs shall not require them.

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
| FR-08 | CIMT shall create work automatically under <input-folder>/CIMT output/work/work_<date-time>. Work content remaining after successful, failed, incomplete, or interrupted execution shall be retained. Earlier verified owned work for the same input folder shall be deleted only immediately before a new repository clone. Configuration/preflight failure, validation, and replay shall not trigger that deletion. Reports, artifacts retained in reports, other input folders, and unrelated files shall survive. |
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
| FR-18 | CIMT shall never ask runtime clarification questions about testing instructions. It shall record unclear instructions, its interpretation, and continue using that interpretation. Explicitly configured operational pauses under FR-56 are permitted; they shall not ask the user to interpret a test. |
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
| FR-30 | CIMT shall create each retained report automatically under <input-folder>/CIMT output/reports/report_<date-time>, using the same timestamp as its work_<date-time> folder. Reports shall sit outside work replaced before a later clone. Run-owned builds, diagnostics, screenshots, and actions shall remain under CIMT output. The report folder shall be portable and archivable. Reports shall remain until manually deleted. |
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
| FR-38 | CIMT shall track ownership of retained work across input folders. After forced termination or host failure, a later run may stop/release the verified owned helper and record recovery without deleting prior work. Only immediately before a new clone shall earlier verified owned work for that same input folder be removed. Unknown ownership, changed tokens, unrelated folders, other inputs, and retained reports shall be protected. |

### Approved command, configuration, and build contracts

| ID | Requirement |
| --- | --- |
| FR-39 | CIMT shall expose setup, validate, run, and replay commands with the reviewed options documented in the product guide. Setup prepares the Mac, run builds/tests, and replay reuses retained built apps. The current increment reruns current text inputs; saved-scenario history/adaptation remains required by FR-22. |
| FR-40 | Configuration shall use setup.yaml for installation/toolchain settings, default.yaml for shared settings, and app.yaml as a reusable application/per-run override. ai-model and ai-budget shall be separate sections. The reviewed fields are specified in the product guide. |
| FR-41 | CIMT shall provide default Android and iOS build scripts in its installation. These scripts shall be created and validated during the first real test runs. The tested repository shall require no modifications. Users may customize scripts or configure replacement script paths. Updates replace supplied defaults while preserving separate user copies. |
| FR-42 | Build targets shall define name, configuration, application project, per-platform target framework, additional build properties including signing, and optional replacement script. Default scripts shall locate and return the installable artifact and app identifier. |
| FR-43 | CIMT shall supply a build-result file path to scripts. A successful script shall write JSON containing artifact and app-id, or the user shall provide those fields in platform YAML. Script-returned values take precedence; YAML supplies missing fields. |
| FR-44 | Project paths and YAML artifact paths shall resolve from the cloned repository root. Local input paths, replacement/reset script paths, and other relative configuration file paths shall resolve from the declaring YAML file's folder. Default scripts shall resolve from the CIMT installation. Absolute paths shall be supported where applicable. |
| FR-45 | Optional reset.command and reset.verify-command shall augment platform reset. CIMT shall supply target, device, and app identifier through environment variables. Exit code 0 means success; any other code stops the run and generates a report. |
| FR-46 | Credentials shall be named entries with username/password in private YAML. Setup text may reference a credential name. CIMT shall resolve values locally; recorded actions shall retain credential references rather than secret values. |
| FR-47 | Validate shall check YAML, required values, paths/text accessibility, Git access and branch, tool/device readiness, credential presence, and model/budget configuration without building, installing, resetting apps, or paid AI calls. It shall generate local HTML. Actual login, signing, and model access are verified during execution. |
| FR-48 | Replay shall reuse retained installable app artifacts without repository clone, submodule update, package restore, or application build. It shall preserve work, reset/setup/login with current credentials, apply normal device/time/budget/masking/crash rules, and create a new report identifying the original app build and source commit without changing the original report. Saved scenario objectives/history and adaptive navigation remain the capability required by FR-22; the current retained-build increment executes current input instructions and explicitly rejects unsupported saved-history input. |
| FR-49 | Reports shall always include summary, outcome, coverage, and stopping reasons. reports.sections shall select detailed sections; screenshot and saved-action collection remain mandatory. Device discovery policy, maximum two-device concurrency, and per-scenario reset are fixed behaviour rather than optional execution switches. |
| FR-50 | setup.yaml shall support installation.root, toolchain.manifest, and optional validation.config/run-config for an application-readiness check without building/testing. |
| FR-51 | Every command, supplied/replacement build script, reset command, and reset verification shall have documented examples and runnable demonstrations explaining configuration, invocation, expected output, and failure behaviour. Demos shall use a user-supplied application repository with secret placeholders; CIMT shall not include a demo MAUI application. |
| FR-52 | Installed CIMT shall run independently of the current working directory and source checkout. The input folder shall be the folder containing --run-config when supplied, otherwise --config. The user shall supply only configuration, referenced test inputs, and optional application-specific scripts; CIMT shall create all necessary run-output folders beneath that input folder's CIMT output subfolder. Existing installation tools and Mac-wide coordination state remain with the installation. CIMT may create an owned short transport link in the Mac temporary directory to address helper sockets; actual helper files shall remain under CIMT output, and only a link targeting the verified owned run may be removed. |
| FR-53 | Missing/invalid configuration and execution errors shall retain reports under the selected input folder when it is writable. If no input configuration can be selected because command syntax is invalid, use CIMT output under the launch folder. An absent, unsafe, or unwritable input/output location shall stop with an explicit terminal error; CIMT shall not redirect output to the installation or another folder. Links shall not redirect output outside its designated parent. Legacy workspace.root/reports.root settings may load for compatibility but shall not relocate output; CIMT shall disclose that they were ignored. |
| FR-54 | CIMT shall display live Git output, build output, and debug/diagnostic output in the terminal during normal execution, including Jenkins console execution. This includes clone/fetch/submodule progress, default and replacement build-script output, compiler/build warnings and errors, CIMT/runtime/adapter diagnostics, and application/device debug output collected during testing. Both stdout and stderr shall be displayed as they become available, without waiting for the command or run to finish. A separate verbose option shall not be required. |
| FR-55 | Live terminal output shall identify its stage and relevant build target, platform, or device so concurrent activity can be understood. Credentials shall be redacted before terminal display as required by FR-36, including secrets split across received output chunks. Private configuration and secret-bearing runtime payloads shall not be dumped to the terminal. Live display shall supplement retained run diagnostics, preserve command exit/error handling, and remain available when optional HTML detail sections are disabled. |
| FR-56 | execution.interactive-pauses shall be an optional boolean, false when omitted. When true for run or replay, CIMT shall display generic information about the upcoming operation and wait for terminal Enter before authenticated OpenAI model preflight and before OpenAI-driven testing. A normal run shall also pause before repository access/builds; replay has no repository/build checkpoint. Messages shall describe credential use without revealing values and disclose possible AI charges for testing. They shall not name or prescribe private, work, or other environment-specific networks or actions. The testing checkpoint is skipped when no installable build exists. Configuration and local secret loading at startup are unchanged; checkpoints precede network use of credentials. |
| FR-57 | Interactive waiting shall count toward the configured whole-run time limit and retain the Mac-wide run lock. The deadline shall stop a pending wait and produce an incomplete report with normal outcome precedence and owned cleanup. Closed terminal input shall stop with an infrastructure error; redirected input with pauses enabled shall fail explicitly rather than continue or hang. Jenkins shall use false or omit the setting. Checkpoint phase and waiting/continued status shall appear in retained run stages, without recording terminal response text. With pauses disabled, CIMT shall not read terminal input. validate shall not use these run checkpoints and shall retain its existing readiness contract. |
| FR-58 | The selected repository branch and project/build configuration shall determine application build steps and tool integrations, including imported targets. CIMT and supplied application adapters shall not introduce a tool call because it existed in another branch, replace unrelated targets, or overwrite configured build properties. CIMT and its supplied ECON build wrappers shall build the selected project unchanged, without rewriting application project files or replacing build tasks in the working clone. Platform compatibility belongs to the application project. User-supplied replacement build scripts remain configurable. |
| FR-59 | Default build workers shall forward explicitly configured build properties unchanged and leave omitted properties to the selected project/SDK. They shall not force packaging/runtime/archive values. If no supported installable artifact is produced, fail clearly without silently changing properties or retrying another build profile. |
| FR-60 | CIMT shall publish per-input retained-build metadata after a completed build stage containing successful app artifacts, including original run/source identity, target/project/configuration/framework, relative artifact paths, and integrity digests without credential/signing values. Replay shall use the latest published set for those inputs, verify branch/profile/path/integrity compatibility, and stop explicitly when retained apps are unavailable or incompatible. A build stage with no successes shall not replace a prior valid set. |
| FR-61 | Every run/replay execution report shall show a mandatory readable overview: command, paired run identity, source branch/commit, UTC start/finish, elapsed duration, requested target labels with their actual build configurations, startup devices, successful app builds available, and recorded AI inference request count. Missing counts shall be described as unavailable rather than assumed zero. |
| FR-62 | CIMT shall record host stages and device operations incrementally in a timestamped activity journal and show a mandatory chronological HTML timeline. Entries shall identify operation, status, target/platform/device where applicable, available duration, and outcome/error. Preparation, installation/reset/launch requests, screenshot validation, AI requests, actions, recovery checks, worker cancellation, and finalization shall be distinguishable. Overlapping workers shall retain their own context. Interrupted records shall not discard earlier activity and shall be disclosed as incomplete; older reports shall not receive invented timing. |
| FR-63 | Failures shall be readable without opening raw JSON or enabling optional detail sections. Reports shall identify failing device/target/operation, available underlying error, exception type/location, and safe links to related diagnostic logs. Empty worker stderr shall not suppress errors already recorded by device workers. Infrastructure/masking errors shall not be reported as confirmed application crashes. Diagnostic text shall be redacted before storage/display and HTML-escaped; raw prompts, private requests, UI values, credentials, and unmasked screenshots shall not be added to activity logs. Mask geometry diagnostics may include redacted identifiers/counts/coordinates without changing capture rejection rules. |
| FR-64 | Reports shall explain why execution finished or stopped and distinguish application-test failures, infrastructure failures, shared-worker cancellation, limit/device stops, and incomplete coverage or remaining work. A secondary cancellation shall retain its own reason rather than replace the original failure. Each started scenario shall retain the latest redacted AI unfinished-work list even when an error or limit prevents a final AI response. Incomplete scenarios shall also list unresolved requirement and observed-control counts where known; when no specific pending work is known, state that the objective has not finished and coverage is unconfirmed. Later plans replace earlier plans, and confirmed completion clears obsolete pending work. These explanations and the activity/overview sections shall remain visible when optional report details are disabled. Existing exit-code precedence, verdict/completion calculation, limits, reset, crash, and masking policies shall remain unchanged. |

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
| User interruption | Stop execution and preserve/report observations and work where possible. Do not clear work at finalization. |

Run results shall contain separate test verdict (passed, failed, inconclusive), completion (complete, incomplete), and execution-error fields. For example, a confirmed failure followed by timeout is failed + incomplete.

| Terminal exit code | Meaning |
| --- | --- |
| 0 | Complete and passed. |
| 1 | Confirmed test failure, without an execution error taking precedence. |
| 2 | Incomplete or inconclusive testing without a confirmed failure or execution error. |
| 3 | Configuration or infrastructure error; a failed build target also produces this code after other targets have run. |

Exit-code precedence is **3 → 1 → 2 → 0**. All findings and completion details remain visible in the report.

## 6. Nonfunctional expectations

- Unattended execution shall require no human input; explicitly enabled operational acknowledgements are permitted.
- A device's actions and observations shall remain isolated from other device workers.
- A run shall retain enough traceability to review findings after its clone is deleted.
- Setup shall diagnose unsupported host/toolchain combinations rather than claim success.
- Work replacement shall delete only verified owned work for those inputs, immediately before cloning; finalization shall preserve work.
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
| AC-12 | Verify work and publish intermediates survive success, failure, timeout, and graceful interruption. Verify earlier verified owned work is removed only immediately before the next clone for those inputs, with reports and other input folders preserved. Verify a second CIMT invocation cannot start while one owns the Mac. |
| AC-13 | Invoke the same CIMT command from a Jenkins pipeline under the server account and verify exit codes 0/1/2/3 and precedence 3 → 1 → 2 → 0, including build failure continuation. |
| AC-14 | Verify nested mapping merge, list replacement, relative paths, and rejection of unknown keys, invalid values, or missing explicit model/time/budget before testing. |
| AC-15 | Verify reset failure stops the run, required masking failure stops the run, and a successful crash retry resets the consecutive-crash counter. |
| AC-16 | Simulate an abandoned helper/work folder. Verify next-run recovery stops/releases only the verified owned helper and preserves work until a new clone, retaining reports and recovery evidence. Verify changed ownership or unrelated links cannot be adopted or deleted. |
| AC-17 | Verify compatible tools are reused, incompatible required tools are replaced without confirmation and recorded, and interrupted setup can resume. |
| AC-18 | Replay a saved scenario with UI changes; verify current configuration/credential use, recorded adaptations, a new report preserving the original, and inconclusive output when meaning cannot be preserved. |
| AC-19 | Demonstrate setup/validate/run/replay and script/reset examples against a user-supplied MAUI repository, with no bundled demo app. |
| AC-20 | Verify validate creates HTML without build/install/reset or paid AI requests, while checking Git branch, inputs, dependencies, and startup-device readiness. |
| AC-21 | Verify installed default build scripts require no tested-repository changes, custom copies survive a CIMT update, and script-result JSON overrides YAML artifact/app-id fallbacks per field. |
| AC-22 | Verify work_<date-time> and report_<date-time> share a timestamp, report placement survives cleanup, and approved path resolution works for local and Jenkins configuration. |
| AC-23 | Verify element-ID-only masking rules, named credential references, and failure on a required mask that cannot be applied reliably. |
| AC-24 | Supply Markdown headings and a testable requirement. Verify headings remain visible as context, the requirement retains its source lines and section meaning, and a passed requirement can complete without evaluating headings. Verify a heading-only document creates no requirement results. |
| AC-25 | Supply only input configuration/texts/scripts in a fresh folder. Invoke installed CIMT from that folder and another launch folder, including deep paths/spaces/shared settings. Verify automatic CIMT output creation, input-relative paths, unchanged output placement, retained reports/work after finalization, shared work/report identity, verified link release, and work replacement only at the next clone boundary. Verify the helper socket binds through its short link while actual files stay inside work. |
| AC-26 | Verify invalid/missing YAML produces an error report below the selected input folder. Verify legacy output roots cannot move output, a branch override cannot change the input folder, and unsafe links/unwritable output cause an explicit failure without writing elsewhere. |
| AC-27 | Run delayed Git, build, and diagnostic-output fixtures through the existing command path. Verify stdout, stderr, and progress appear in the terminal before each producing process finishes, without a verbose option, including a noninteractive Jenkins-style console. Verify concurrent output identifies its target/platform/device and existing exit-code and timeout behavior is preserved. |
| AC-28 | Include synthetic credentials in stdout/stderr, including a credential split across output chunks. Verify secrets never appear in terminal or retained diagnostics, private runtime/configuration payloads are not printed, and disabling optional HTML details does not disable live terminal output. |
| AC-29 | Enable interactive pauses in the per-run YAML. Verify the three generic operation messages contain no environment-specific network instructions and that OpenAI preflight, repository access/builds, and AI testing cannot start before their respective acknowledgements. Verify testing is not offered when every build failed, and waiting/continued stages are retained without secret or response text. |
| AC-30 | Verify omitted/false pauses do not read input or change unattended execution. Verify invalid values fail configuration validation, redirected/closed input cannot continue the protected stage, deadline expiry during a wait produces incomplete output and normal cleanup/reporting, and a late acknowledgement cannot start work after the deadline. |
| AC-31 | Run the supplied application adapter against fixtures with a copy-only pre-build, a separately configured tool, other pre-build steps, and a disabled target. Verify that project files and build-request payloads remain unchanged, configured portable copy/tool steps and conditions are preserved, and an unsupported Windows command fails visibly instead of being rewritten or hidden. Verify the adapter delegates to the installed default workers on Android/iOS. |
| AC-32 | Verify preparation/preflight, validation, replay, failed helper stop, and failed/limited runs preserve old work. Verify helper recovery keeps work; the clone boundary removes only earlier verified work for the current inputs. Verify completed publish folders remain. |
| AC-33 | Exercise public replay with Git/build fixture commands disabled. Verify reused artifact bytes/digests, original build provenance, a new report/current inputs, unchanged prior work/metadata, and no clone/build stages. Verify missing/changed/unsafe/mismatched retained apps stop before execution, without fallback rebuilding. |
| AC-34 | Verify publish and metadata commands preserve explicit Android/iOS properties and inject no packaging/runtime/archive values when omitted. Verify unsupported/missing installable output produces a clear error. |
| AC-35 | Verify run/replay overviews show actual configuration separately from labels, source/run identity, UTC times/duration, devices, successful builds, and the recorded AI count. Verify unavailable counts are not displayed as zero. |
| AC-36 | Use fake overlapping device operations and host/build stages. Verify timestamp ordering, context, duration/status, incremental journal records, redacted messages, and preservation of earlier events after a truncated journal line. Verify existing reports without a journal explicitly state that timing is unavailable. |
| AC-37 | Reproduce a fake Android capture failure with empty worker stderr and an iPhone cancellation. Verify terminal/final JSON/HTML expose the actual worker failure and separate cancellation, with no claimed application crash. Verify escaped/redacted error details, working in-report log links, rejected escaping links, and geometry diagnostics containing no UI values. |
| AC-38 | Disable optional report details. Verify overview, chronological activity, failures/stopping reasons, and unresolved-work explanations remain visible. Interrupt a scenario during reset, capture, relaunch, or after an AI response reaches a limit: verify its latest redacted pending work and known coverage gaps survive, with an explicit unfinished-objective fallback when needed. Verify later plans replace earlier plans and completed scenarios clear obsolete pending work. Exercise the existing public run/replay fixtures and preserve their exit, retention, masking, and coverage semantics. |

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

## Review record — version 0.5

On 29 October 2026, the product owner required execution independent of the launch folder and source checkout, with user-supplied inputs only. All generated run folders shall be created by CIMT under the input folder's CIMT output subfolder, for example FirstRun/CIMT output. FR-08/FR-30 and FR-52/FR-53 replace the earlier shared/configurable output-root policy. The paired timestamp, retained evidence, and safe clone-cleanup rules remain in force. AC-25/AC-26 define the new checks.

## Engineering clarification — version 0.6

The first user-started run passed model/runtime preflight but failed at device discovery. Its native socket address was 110 bytes; the installed helper rejects macOS addresses above 103 bytes. A short owned temporary link is therefore permitted as transport metadata. Actual socket/log files and run output remain below the selected inputs. The user does not shorten paths or prepare extra folders. The source of the limit is [Mobile CLI's path validation](https://github.com/mobile-next/mobilecli/blob/main/daemon/paths.go). FR-52 and AC-25 record this engineering detail; test failure policies and output data placement are unchanged.

## Review record — version 0.7

On 29 October 2026, the product owner required build output, debug output, and Git output to be displayed in the terminal. FR-54/FR-55 make incremental stdout/stderr/progress visible during normal local and Jenkins execution while preserving credential redaction, context, retained diagnostics, and existing process outcomes. AC-27/AC-28 define the verification. This revision records the requirement; complete live-output streaming is not yet implemented or verified. It does not change an already active run.

## Review record — version 0.8

On 29 October 2026, the product owner requested terminal pauses to switch between a private network for OpenAI and the work network for repository/build access. FR-56/FR-57 and AC-29/AC-30 define opt-in operational acknowledgements, including the return to OpenAI after builds. FR-18 is narrowed to test clarification questions. The whole-run deadline, secret redaction, TLS checks, failure precedence, and unattended default remain in force.

## Review record — version 0.9

On 29 October 2026, the product owner corrected the previous increment: the implementation must give generic information and wait for user input. This supersedes the network-specific messages and option in version 0.8. FR-56/FR-57 now use execution.interactive-pauses. Checkpoints describe the upcoming operation and ask for Enter without directing network changes. The same three checkpoint positions, unattended default, input privacy, deadline, cleanup, and outcome policies remain in force. Public examples and FirstRun are migrated to the generic field.

## Engineering correction — version 0.10

The product owner clarified that CuRMiT integration belongs to Visual Studio/project configuration. Investigation confirmed that branch testing/curmitAndNugets removed the legacy tagger command, but the supplied local adapter reintroduced it. FR-58/AC-31 explicitly require preserving the chosen branch's project build steps. The correction removes the obsolete target override and limits the ECON adapter to the known Windows resource-copy command. This is an adapter defect correction; branch selection and the generic default build-worker contract remain unchanged.

## Review record — version 0.11

On 29 October 2026, the product owner required build-property preservation, retention of work until the next clone, and replay using the already built app. FR-08/FR-30/FR-38/FR-48 replace deletion-after-execution/startup policies. FR-59/FR-60 and AC-32–AC-34 define property forwarding, retained artifacts, and replay without Git/build. Paired identities, ownership protections, secrets, reports, and run limits remain in force. Current-instruction replay is implemented; saved-action-history adaptation remains unfinished rather than being silently approximated. See [work retention and replay](work-retention-and-replay.md).

## Review record — version 0.12

On 30 October 2026, the product owner requested implementation of readable failures, chronological activity, run overview, and stopping reasons in the HTML report. FR-61–FR-64 and AC-35–AC-38 specify this increment. Timestamped lifecycle diagnostics also appear in the terminal. This does not relax masking/stability checks or other execution policies, and does not claim completion of the separately tracked full Git/build stdout/stderr streaming requirement. See [diagnostic reporting](diagnostic-reporting.md).

On 30 October 2026, the product owner requested removal of the Windows resource-copy replacement. FR-58/AC-31 now require the supplied ECON wrappers to delegate without editing the application project. This supersedes the earlier compatibility-rewrite allowance; users may still supply their own build scripts.
