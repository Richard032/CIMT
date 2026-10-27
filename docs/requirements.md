# CIMT requirements

Version: 0.1  
Date: 27 October 2026  
Status: first draft for product-owner review  
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
| FR-03 | Configuration shall use YAML. Precedence shall be default YAML, then per-run YAML, then terminal arguments. Later values override earlier values. Exact merge rules remain an architecture proposal. |
| FR-04 | Application configuration shall define repository URL, branch, solution path, build targets, app identifiers, and custom build commands as needed. Build targets are configurable; Release_Generic and Release_Pride are examples only. |
| FR-05 | Testing instructions and application requirements shall be separate text inputs, supplied through local paths or unauthenticated web links to text content. CIMT shall also support app setup instructions. General web-page extraction is not confirmed. |
| FR-06 | Model selection, AI spending limit, whole-run time limit, report contents, and application setup shall be configurable. Configuration shall support reuse and per-run overrides. |

### Repository and build

| ID | Requirement |
| --- | --- |
| FR-07 | CIMT shall clone a repository from a Git URL. Private repositories shall use Git authentication already configured on the Mac, without interactive login during execution. |
| FR-08 | Clones shall live under one default CIMT working folder. CIMT shall delete its run clone after successful, failed, incomplete, or interrupted execution. Reports and evidence shall survive cleanup. |
| FR-09 | CIMT shall build every configured target and test it on every connected compatible device. A target build failure shall be reported while other build targets continue. |
| FR-10 | The report shall identify the branch and resolved commit used, build target, and tested device so findings can be traced to an execution. |

### Devices and scenarios

| ID | Requirement |
| --- | --- |
| FR-11 | CIMT shall discover supported connected physical Android and iOS devices at startup and use all of them without separate CIMT registration. Both platforms need not be present. Newly connected devices shall not join the active run. |
| FR-12 | At most two devices shall be tested simultaneously. Additional devices shall be queued. Every compatible target/device combination shall be covered unless execution is stopped or limited. |
| FR-13 | No connected devices shall cause CIMT to stop and generate a report. |
| FR-14 | CIMT shall follow exact scenarios when requested and explore creatively when permitted. AI may divide instructions into scenarios unless the input explicitly defines the boundaries. |
| FR-15 | Before each individual scenario, CIMT shall reset application data and repeat setup/login if needed. Setup instructions and test credentials shall be application inputs. |
| FR-16 | CIMT may reinstall/reset the app, delete test data, and change device settings automatically. External Bluetooth, USB, or other equipment shall be prepared manually. |
| FR-17 | Unavailable external equipment shall cause affected scenarios to be skipped with an explanation; remaining scenarios shall continue. |
| FR-18 | CIMT shall never ask runtime clarification questions. It shall record unclear instructions, its interpretation, and continue using that interpretation. |
| FR-19 | Testing instructions shall take precedence over conflicting requirements. The report shall mark the affected requirement overridden, explain the conflict, and judge execution against the instructions. |
| FR-20 | AI shall choose reproduction attempt counts according to complexity, subject to run limits and the fixed crash rule. |
| FR-21 | After a crash, CIMT shall relaunch the app and continue. Three attempts crashing at the same point shall cancel only the affected scenario. Other scenarios shall continue. |
| FR-22 | CIMT shall record performed actions for later replay. Replay may adapt to UI changes; the report shall preserve the actual actions and adaptations. |

### AI, reporting, and results

| ID | Requirement |
| --- | --- |
| FR-23 | CIMT shall use OpenAI. Screenshots, UI text, requirements, and relevant source code may be processed by the cloud AI service, with credential redaction as required below. |
| FR-24 | A strict AI spending limit shall apply across the entire run, including concurrent device workers. CIMT shall reserve the maximum possible cost before each request and shall not issue a request the remaining budget cannot cover. Conservative early stopping is accepted. |
| FR-25 | A configurable time limit shall apply to the entire run. CIMT shall also support completion based on coverage of all testing instructions. Exhausting time or budget with work outstanding shall stop testing and produce an incomplete result. |
| FR-26 | CIMT shall generate one local HTML report, grouped by build target, device, and scenario, with observed behaviour and evidence. |
| FR-27 | Every supplied requirement shall have a result and supporting evidence or an explanation of why evidence is unavailable. Results shall include passed, failed, not tested, inconclusive, and overridden. |
| FR-28 | A screenshot shall be captured for every test step. Evidence collection failures shall be disclosed rather than silently omitted. |
| FR-29 | Reports shall include unclear instructions and interpretations, reproduction attempts, crashes, skipped/cancelled work, and relevant diagnostics. Report contents shall be configurable; disabling optional sections shall not misrepresent coverage or hide the final outcome. |
| FR-30 | Each run shall have a local folder named using its date and time. Screenshots and recorded actions shall remain in subfolders beside the report. The folder shall be portable and archivable. Reports shall remain until manually deleted. |
| FR-31 | Testing instructions shall define failure criteria. In their absence, confirmed requirement failures or app crashes mean failed; unfinished or inconclusive testing means incomplete; otherwise passed. |
| FR-32 | Blocking infrastructure failures, including device disconnection or AI service unavailability, shall stop the run and generate a report. This rule has explicit exceptions for failed build targets, recoverable app crashes, unclear instructions, and unavailable external equipment. |

### Mac provisioning and credentials

| ID | Requirement |
| --- | --- |
| FR-33 | The project shall deliver a reusable setup script plus configuration sufficient to prepare supported Intel Macs for local CIMT execution. |
| FR-34 | Setup shall install missing dependencies where possible and provide step-by-step documentation for manual tasks. It may request administrator privileges; ordinary test runs shall operate without them. |
| FR-35 | Secrets, including the OpenAI key, app credentials, and signing-related configuration, shall be supplied through YAML configuration. Private Git authentication remains host-managed under FR-07. |
| FR-36 | CIMT shall restrict access to secret configuration and redact credentials from logs, reports, and AI requests. Credentials required for login shall still be entered into the app through device actions. |

## 5. Outcomes and exceptional conditions

These rules distinguish a test finding from an inability to execute. Instructions may customize test failure criteria, but cannot turn unexecuted work into a verified pass.

| Condition | Required behaviour |
| --- | --- |
| Ambiguous instruction | Record interpretation and continue; do not ask questions. |
| Requirement overridden by instruction | Mark overridden and assess the instruction. |
| App crash | Capture evidence, relaunch, continue; cancel affected scenario after three same-point crashing attempts. |
| Build target fails | Record failure and continue other targets. |
| Equipment unavailable | Skip dependent scenarios, explain, and continue. |
| No devices at startup | Stop and report. |
| Device disconnect / blocking AI or infrastructure failure | Stop run and report partial execution. |
| Time or AI budget exhausted | Stop and report incomplete execution. |
| User interruption | Stop execution, preserve/report observations where possible, and delete run clone. |

Run-level outcome precedence when failures coexist with incomplete execution has not been explicitly agreed. The architecture proposes storing outcome and completion separately and reporting both. Exact terminal exit codes remain proposed.

## 6. Nonfunctional expectations

- Execution shall require no human input after invocation.
- A device's actions and observations shall remain isolated from other device workers.
- A run shall retain enough traceability to review findings after its clone is deleted.
- Setup shall diagnose unsupported host/toolchain combinations rather than claim success.
- Cleanup shall delete CIMT-owned run clones only, not unrelated repositories.
- Secrets shall not appear in retained configuration snapshots or screenshots transmitted to AI; feasibility of masking must be validated.
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
| AC-13 | Invoke the same CIMT command from a Jenkins pipeline under the server account and obtain the local report and meaningful process result. |

## 8. Later release: branch comparison

CIMT shall compare two Git branches, run the same instructions on both unless text inputs specify otherwise, reset application data between branch executions, and report new, resolved, and unchanged observations. This capability is intentionally outside initial-release acceptance.

## 9. Items not yet agreed

Exact CLI syntax, YAML schema/merge semantics, exit codes, supported version matrix, default limits and currency, model/pricing validation, report implementation, error precedence, screenshot masking, crash-point matching, replay portability, and installer technology remain technical proposals or open review items. No performance target or fixed bug-discovery guarantee has been agreed.
