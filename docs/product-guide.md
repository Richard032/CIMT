# CIMT product documentation

Version: 0.1  
Date: 27 October 2026  
Status: intended product behaviour and proposed operator workflow  
Product: CIMT — Curtis Intelligent Mobile Test

**CIMT is not implemented yet. Commands, configuration keys, paths, and pipeline examples below are proposed interfaces for review, not executable instructions for an existing release.**

## 1. What CIMT will do

CIMT helps developers test a .NET MAUI app during everyday development. Give it a Git repository, build targets, plain-text testing instructions, and requirements. It will build one selected branch, operate the app on connected physical devices, and produce a local HTML report.

Typical requests include:

- Test seat configuration and investigate whether it crashes.
- Try to reproduce a bug described in a text file.
- Check specified requirements after a change.
- Explore a feature creatively where the instructions permit it.

CIMT complements the existing validation system. AI exploration can miss bugs or misinterpret behaviour, so reports must distinguish observed evidence, interpretations, and uncertainty.

## 2. Where it runs

The initial release runs on Intel Macs. One installation serves multiple application repositories; only one run may be active per Mac.

Developers invoke the terminal command. Jenkins invokes the same command through a pipeline on its Mac execution node. Devices must be connected to the Mac actually executing CIMT, even if Jenkins orchestration is elsewhere.

The mobile apps connect to their normal configured test backend. External equipment is prepared manually. OpenAI processes permitted testing context in the cloud; device execution and report storage remain local.

## 3. What the operator supplies

| Input | Purpose |
| --- | --- |
| Default YAML configuration | Shared working folder, model, budgets, reporting, and common settings. |
| Optional per-run YAML and arguments | Override selected settings for one run. |
| Git URL and branch | Identify what CIMT clones and builds. Existing Mac Git credentials support private repositories. |
| Solution path and build target definitions | Describe each application build, platform, artifact, app identifier, and any custom commands. |
| Testing instruction text | Tell CIMT what to test, how strictly to follow a scenario, where it may explore, and failure rules. |
| Requirements text | Define expected application behaviour. |
| Setup text and credentials | Explain permissions, login, test data, and initial application state. |
| Connected devices | Every supported device present at startup participates; later connections are excluded. |
| Prepared external equipment | Make hardware-dependent scenarios possible. |

Instructions, requirements, and setup are separate inputs. Local text paths and unauthenticated links to text content are supported. Application requirements and instructions may be sent to OpenAI. Secrets must be excluded from the repository and redacted from retained/transmitted evidence.

## 4. Mac preparation plan

The project will provide a reusable setup script and configuration. Automatic installation is required where feasible; manual operations will have step-by-step instructions.

The intended sequence is:

1. Check Intel Mac and macOS compatibility with the supported toolchain manifest.
2. Install or validate Git, application build tools, Android tooling, Apple tooling, the selected device-control adapter, and CIMT runtime.
3. Complete manual Apple authentication/licensing and signing/provisioning tasks.
4. Connect the Android phone and authorize development/USB access.
5. Connect and trust the iPhone; complete development/signing prerequisites for its supported OS.
6. Configure host Git access and the private CIMT YAML configuration.
7. Prepare test accounts, backend access, and external equipment.
8. Validate access under the exact account that will execute CIMT, including the Jenkins account.
9. Run a small acceptance workflow on both devices.

Setup may request administrator privileges. Ordinary tests must not require them. Supported versions and exact commands will be published after adapter/toolchain validation. No assumption is made that every Intel Mac can support every iPhone OS version.

## 5. Proposed configuration example

The following illustrates concepts only. Placeholder versions, commands, limits, and currency are not product defaults. Final keys and schema are pending review.

```yaml
schema_version: 1

workspace:
  root: "/Users/tester/CIMT/work"
reports:
  root: "/Users/tester/CIMT/reports"
  sections: [summary, requirements, scenarios, findings, interpretations, diagnostics]
  screenshot_each_step: true

repository:
  url: "git@github.com:your-team/your-maui-app.git"
  branch: "feature-to-test"
  solution: "MobileApp.sln"

inputs:
  instructions: "/Users/tester/CIMT/inputs/test-instructions.txt"
  requirements: "https://example.org/mobile-requirements.txt"
  setup: "/Users/tester/CIMT/inputs/app-setup.txt"

build:
  targets:
    - name: "Release_Generic"
      android:
        command: ["./ci/build-android.sh", "Release_Generic"]
        artifact: "artifacts/android/app.apk"
        app_id: "example.mobile.generic"
      ios:
        command: ["./ci/build-ios.sh", "Release_Generic"]
        artifact: "artifacts/ios/device-app"
        app_id: "example.mobile.generic"
    # Add further configurable targets; no target names are built into CIMT.

execution:
  time_limit_minutes: 60
  devices: "all_connected_at_startup"
  max_parallel_devices: 2
  reset_before_each_scenario: true

ai:
  provider: "openai"
  model: "<validated-model>"
  api_key: "<private-key-set-locally>"
  budget:
    amount: 5.00
    currency: "USD"
    enforcement: "strict"

credentials:
  app_username: "<test-account>"
  app_password: "<test-password>"
signing:
  profile: "<application-specific-profile-reference>"
```

The budget/time values are illustrative choices only. The real configuration must use a validated model/pricing combination. Signing details will depend on application packaging and the chosen adapter.

Configuration precedence is default YAML, per-run YAML, then terminal arguments. The architecture proposes merging mappings and replacing complete lists; this detail still needs review.

Store actual secrets only in private configuration outside version control. File access will be restricted. App credentials are entered through device control when required and must not be copied into AI prompts. Do not include real secrets in shared example files.

## 6. Proposed terminal workflow

```text
cimt run --config /path/to/default.yaml --run-config /path/to/run.yaml
cimt run --config /path/to/default.yaml --branch feature-to-test
```

The exact command names and options are proposals. No interactive question will be asked during a run. Missing or unusable mandatory inputs produce a report explaining why execution could not proceed.

A run will clone the repository into the common working folder, build configured targets, and test each target on every compatible startup device. At most two devices run simultaneously; the others wait.

Application data is reset before every scenario. Setup and login are repeated when necessary. The operator authorizes CIMT to reset/reinstall apps, delete test data, and change device settings. Equipment outside the phone remains manually prepared.

## 7. Writing testing instructions

A useful instruction file states the objective, expected result, exact steps where necessary, permitted exploration, equipment dependencies, and any failure rules.

Example text:

```text
Objective: investigate crashes in seat configuration.

Scenario 1 — exact:
Open the seat configuration screen.
Select the available seat options in the order described below.
Save and reopen the configuration.
Expected: the app remains running and the chosen values are retained.

Scenario 2 — exploratory:
Explore other seat configuration combinations.
Try repeated saves and navigating back during editing.
Do not change unrelated user account settings.

Equipment:
The test seat controller must be connected and prepared manually.
Skip dependent scenarios if it is unavailable.

Failure criteria:
An application crash or loss of a successfully saved configuration is a failure.
```

This is an example of input structure, not a mandatory text format. AI may split instructions into scenarios when boundaries are not supplied. It records unclear wording and its interpretation and continues without asking.

When instructions conflict with a requirement, instructions have higher priority. The report marks the requirement overridden and explains what was tested instead.

## 8. Crashes, limits, and interruptions

CIMT relaunches after an app crash. AI decides reproduction effort based on complexity, but three crashing attempts at the same point cancel the affected scenario only.

The whole-run time limit covers execution end to end. The AI spending limit is shared by all workers. Before each AI request, CIMT must reserve the maximum possible charge; if funds are insufficient it stops incomplete, potentially below the configured cap.

A failed build target is recorded while other targets continue. Device disconnection or a blocking AI/infrastructure failure stops the run and generates a partial report. Missing equipment skips dependent scenarios while other scenarios continue. No startup devices means stop and report.

After execution, the clone is deleted, including after failure, incompletion, or interruption. Reports remain. Immediate deletion cannot occur while the Mac is powered off or the process is forcibly killed; the architecture proposes recovery cleanup at next startup.

## 9. Reading the report

One run folder will contain an HTML report with evidence subfolders. The proposed name includes date, time, timezone offset, and a unique suffix.

The report will show:

- Repository branch and resolved commit; configuration with secrets removed.
- Build results and device details, grouped by target/device/scenario.
- Planned, executed, skipped, cancelled, and unfinished work.
- Observed versus expected behaviour, reproductions, and crashes.
- Each requirement's status and evidence.
- Ambiguous instructions, CIMT's interpretation, and instruction overrides.
- Screenshots for every test step and saved actions.
- Time/budget usage and reasons for stopping.
- Errors or missing evidence, and clone cleanup status.

| Requirement status | Meaning |
| --- | --- |
| Passed | Observed evidence supports the expected behaviour. |
| Failed | Observed evidence contradicts the effective expectation. |
| Not tested | The requirement was not evaluated; report explains why. |
| Inconclusive | A check was attempted but evidence cannot establish pass/fail. |
| Overridden | A conflicting instruction took priority; report explains it. |

Testing instructions define test failure rules. Without them, confirmed requirement failures or app crashes mean failed; unfinished or inconclusive testing means incomplete; otherwise passed. Reporting mixed failures and incomplete coverage, and exact terminal exit codes, still require architecture review.

Keep the complete folder when copying or archiving a run. Reports remain until manually deleted. CIMT does not automatically publish them.

## 10. Saved actions and replay

CIMT saves performed actions for later replay. Replay may adapt to a changed UI while retaining the scenario's intent. The report records adaptations and actual observations; replay is not a promise of identical coordinates or identical AI decisions.

Replay invocation and cross-device portability remain design decisions. The initial release must demonstrate saved actions and adaptive replay.

## 11. Jenkins usage proposal

A pipeline executes the same CLI on an Intel Mac node and archives the local run folder. Example pseudocode:

```groovy
pipeline {
  agent { label 'cimt-intel-mac' }
  stages {
    stage('CIMT') {
      steps {
        sh 'cimt run --config /private/path/cimt.yaml --run-config /private/path/nightly.yaml'
      }
    }
  }
  post {
    always {
      // Configure artifact collection for the actual CIMT report root.
      // Preserve the complete run folder, including evidence.
    }
  }
}
```

This is not a ready-to-run pipeline: labels, installation paths, artifact collection, and exit-code handling must match the eventual implementation. Use the same service account tested during provisioning. Disable or reject overlapping runs on the Mac; CIMT's own host lock enforces the same rule.

## 12. Troubleshooting expectations

| Symptom | Expected operator action / CIMT behaviour |
| --- | --- |
| No devices detected | Read report, connect/trust/authorize supported devices, start a new run. |
| Private clone fails | Verify host Git credentials under the executing account. |
| iOS build/install fails | Review signing, provisioning, Xcode/device compatibility, and build configuration. |
| A target fails to build | Review its diagnostics; other targets continue. |
| Device disconnects | Restore connection, review partial report, rerun. |
| AI limit reached | Review incomplete report; adjust limit or scope for a new run. |
| App crashes repeatedly | Review screenshots/logs; affected scenario cancels after three same-point crashing attempts. |
| Required equipment missing | Prepare equipment and rerun skipped scenarios. |
| Another run is active | Wait for completion; do not bypass the host lock. |

## 13. Release readiness and review

The first release must be demonstrated on a second Intel Mac with two build targets on a physical Android phone and iPhone. [Requirements acceptance criteria](requirements.md#7-first-release-acceptance-criteria) also cover concurrency, reset, crash recovery, privacy, strict budget, reports, cleanup, and Jenkins.

Before implementation, review the [architecture decisions](architecture.md#11-decisions-and-release-gates). Device-control technology, supported versions, CLI/YAML details, outcome precedence, and strict budget implementation remain open. Two-branch comparison will follow the single-branch initial release.
