# CIMT installation and setup guide

Version: 0.1  
Last updated: 28 October 2026  
Status: living installation guide; initial Mac inspection complete, installation and end-to-end verification pending  
Scope: supported Intel Macs for local command-line and Jenkins execution

## 1. Purpose and current status

This document describes how to prepare another supported Mac, install CIMT, configure an application, and prove that local testing works. Findings from the first Mac are used to improve the repeatable procedure; its particular paths, installed versions, and hardware are examples, not mandatory product defaults.

CIMT's CLI, installer, default build scripts, and pinned toolchain manifest have not yet been implemented. Commands beginning with cimt below are the approved product interface and cannot yet be executed from this repository. Prerequisite inspection commands were exercised where recorded; installation commands and package versions will be filled in as they are implemented and verified.

The agreed initial host scope is **Intel Macs**. This guide does not claim support for every macOS release, Apple Silicon, or every possible Xcode/device combination. The eventual compatibility manifest will define supported combinations. Supporting additional hardware requires a reviewed scope change.

Related documents: [requirements](requirements.md), [architecture](architecture.md), [product guide and approved YAML](product-guide.md).

## 2. Installation success criteria

A Mac is ready when:

- The host, Xcode, .NET SDK/workloads, Java/Android SDK, device OS versions, and device adapter match a tested compatibility manifest.
- CIMT and its default scripts are installed; normal test execution needs no administrator privileges.
- The actual execution account can read private configuration, reach the Git repository and branch without prompting, and access the required signing material.
- Connected test devices are available and authorized; paired but unavailable devices do not establish readiness.
- validate succeeds for a real application without building/installing/resetting or making paid AI requests.
- A real single-branch run builds, installs, executes, and produces a portable local report; cleanup removes only the run clone.
- On a Jenkins Mac, the same command works under the Jenkins execution account.

The first release additionally requires the second-Intel-Mac acceptance demonstration in the requirements. One successful inspection is not an installation acceptance test.

## 3. Select compatible versions before installation

Do not turn this Mac's observed versions into a supported baseline without testing.

| Component | Selection rule | Current state |
| --- | --- | --- |
| Intel Mac/macOS | Must run the selected developer tools. | Intel scope confirmed; supported macOS range not selected. |
| Xcode and iPhone OS | Match Apple support and the selected .NET iOS workload. | Installed Xcode inspected; build/install compatibility unverified. |
| .NET SDK | Support CIMT's implementation and the application's target frameworks/global.json. | Several SDKs found; product SDK pin not selected. |
| MAUI Android/iOS workloads | Match the chosen SDK and application. | Android workload found; iOS workload absent from reported installed list. |
| JDK and Android SDK/build tools | Match the application's Android targets and selected .NET Android tooling. | Not detected in checked locations. |
| Device adapter | Select after evaluating physical Android/iOS and unattended Intel/Jenkins operation. | Mobile MCP/Appium evaluation pending. |
| Supporting runtimes | Install only those required by the selected adapter. | Node/npm not detected; requirement depends on adapter selection. |
| Git | Noninteractive access under the executing account. | Git found; inspected SSH route needs host-trust setup. |
| OpenAI model/pricing | Use a model with a provable maximum request cost. | Not configured/validated in this inspection. |

Microsoft requires an Xcode version compatible with the selected MAUI release; Apple publishes Xcode host/device support separately. Review both when creating the manifest. [Microsoft installation guidance](https://learn.microsoft.com/dotnet/maui/get-started/installation), [Apple Xcode requirements](https://developer.apple.com/xcode/system-requirements).

## 4. Repeatable Mac preparation

### Step 1 — Inspect the host and available storage

Run in the account that will execute CIMT:

```bash
sw_vers
uname -m
sysctl -n machdep.cpu.brand_string
sysctl -n hw.memsize
sysctl -n hw.model
df -h /
```

Expected for the initial supported scope: x86_64 on an Intel Mac. Check free space against the selected toolchain downloads, builds, temporary clone, and retained step screenshots before installing. No fixed minimum storage or RAM requirement has been approved yet.

Record actual versions and capacity. A permission-denied inspection is an unknown result, not evidence that hardware or tools are absent.

### Step 2 — Choose the execution account and folders

Use the intended developer or Jenkins execution account. Confirm read/write access to installation, work, and report locations. Installation may need administrator privileges; routine tests must not.

Approved folder pattern:

```text
<installation-root>/             # CIMT and supplied default scripts
<working-root>/work_<date-time>/ # temporary repository clone
<report-root>/report_<date-time>/# retained report and evidence
```

Work and report folders share a timestamp. Reports must remain outside the temporary cleanup folder. Exact timezone/collision handling remains to be implemented.

A shared installation such as /Users/Shared/CIMT is an example, not a required location. Private YAML files must remain accessible only to the intended account(s), outside source control.

### Step 3 — Prepare Git and private repository access

1. Check git --version.
2. Configure the host's existing Git authentication for the intended repository URL.
3. For SSH, verify the server fingerprint through the hosting provider's official documentation before establishing host trust.
4. Test noninteractive access with the actual repository and account.

Example inspection, using a repository for which access is authorized:

```bash
GIT_TERMINAL_PROMPT=0 GIT_SSH_COMMAND='ssh -o BatchMode=yes -o StrictHostKeyChecking=yes -o ConnectTimeout=10' git ls-remote git@github.com:YOUR-TEAM/YOUR-APP.git HEAD
```

Success prints the remote commit and HEAD reference. Host-key failure means trust setup must be completed; it does not prove the user's repository credentials are wrong. Do not disable host verification as a workaround. GitHub connector access does not establish terminal Git access.

For GitHub's manual trust/authentication test, follow its fingerprint verification procedure. [GitHub SSH connection guide](https://docs.github.com/en/authentication/connecting-to-github-with-ssh/testing-your-ssh-connection).

### Step 4 — Prepare Xcode

1. Select the compatible Xcode version from the tested manifest.
2. Install it using Apple's distribution channel and complete any required sign-in/license/first-launch steps.
3. Select its developer directory if multiple Xcode versions are installed.
4. Verify the selected tools:

```bash
xcode-select -p
xcodebuild -version
xcodebuild -checkFirstLaunchStatus
xcrun --sdk iphoneos --show-sdk-version
```

Expected: the selected full Xcode developer directory, matching version/SDK, and successful first-launch-status check. This does not prove signing, device trust, or MAUI compatibility; those require later checks.

Use the MAUI-compatible Xcode version rather than automatically selecting whichever version is newest. [Microsoft Apple environment setup](https://learn.microsoft.com/dotnet/maui/get-started/installation).

### Step 5 — Prepare .NET and MAUI workloads

1. Inspect dotnet --list-sdks and dotnet --list-runtimes.
2. Install/select the manifest's Intel/x64 SDK, accounting for the application's global.json and target frameworks.
3. Install the matching Android and iOS MAUI workloads. The .NET SDK alone does not provide all platform dependencies.
4. Check dotnet workload list under the selected SDK.
5. Record exact SDK/workload versions and verify through the first application's builds.

The exact pinned installation commands will be added when the SDK/workload manifest is selected. Do not treat the presence of maui-android as proof that iOS is installed.

### Step 6 — Prepare Java and Android SDK tools

1. Select the compatible JDK and Android SDK components for the application/toolchain.
2. Install the JDK and Android SDK command-line components, platform-tools, target platform, and build-tools.
3. Configure JAVA_HOME and ANDROID_HOME for the executing account, plus the necessary executable paths.
4. Verify:

```bash
java -version
javac -version
adb version
```

Microsoft documents a project-aware InstallAndroidDependencies build target that can obtain required SDK/JDK components. Its use and exact paths/versions will be validated during CIMT build-script development; it was not run during inspection. Android Studio and emulator images are not requirements for CIMT's initial physical-device scope. [Microsoft Android dependency installation](https://learn.microsoft.com/dotnet/android/getting-started/installation/dependencies).

### Step 7 — Connect and authorize physical devices

Android:

1. Enable Developer options and USB debugging on the phone.
2. Connect a data-capable USB cable.
3. Accept the phone's authorization prompt for this Mac.
4. Run adb devices -l. The phone must be available as device, not unauthorized or offline.

These are manual device steps before unattended testing. [Microsoft Android device setup](https://learn.microsoft.com/en-us/dotnet/maui/android/device/setup).

iPhone:

1. Connect and unlock the phone.
2. Establish trust/pairing with the Mac through Xcode as required.
3. Enable Developer Mode where required, restart, and confirm on the device.
4. Verify availability with xcrun devicectl list devices.
5. Later verify install/launch with the selected adapter and signed application.

Developer Mode may appear after pairing; Apple's instructions describe the on-device confirmation. [Apple Developer Mode instructions](https://developer.apple.com/documentation/xcode/enabling-developer-mode-on-a-device).

Historical paired entries marked unavailable do not count as connected test-ready devices. CIMT uses all supported devices available at run startup, with at most two active workers.

### Step 8 — Prepare signing and external equipment

Configure the signing identity/profile required by the application's iOS build and make it usable under the actual execution account. Existing provisioning-profile files alone do not prove certificate/private-key access, correct app/device entitlement, or successful signing.

Prepare any required Bluetooth, USB, seat-controller, backend, or other external equipment manually. Put setup/login and equipment dependencies in the application inputs. The signing and hardware procedure will be verified with the selected first application.

### Step 9 — Install the selected device-control adapter

Evaluate Mobile MCP and Appium against the approved physical-device requirements before selecting one. Record required supporting runtime versions, installation commands, signing/device-agent setup where applicable, and unattended operation here after validation.

Node/npm are currently not detected; do not install an adapter or supporting runtime during a read-only inspection. Adapter selection remains open, not an implementation deviation.

### Step 10 — Install CIMT and create configuration

**Pending implementation:** no CIMT executable/install package or toolchain manifest is currently delivered. Once packaging/bootstrap is defined, add the exact download/install command, package version verification, and setup invocation here.

Approved setup invocation:

```text
cimt setup --config setup.yaml
```

Approved setup configuration:

```yaml
installation:
  root: "/Users/Shared/CIMT"
toolchain:
  manifest: "./toolchain.yaml"
validation:
  config: "./default.yaml"
  run-config: "./app.yaml"
```

The validation section is optional. Manifest contents, package checksums, and bootstrap steps remain engineering work.

Create default.yaml and app.yaml using the [product-guide examples](product-guide.md). Required effective values include explicit model, whole-run time limit, and AI budget. Use separate ai-model and ai-budget sections. Named application credentials remain in private YAML. Protect configuration access; do not add real secrets to Git.

CIMT setup may replace incompatible required tools without confirmation, recording changes. It must reuse compatible installations and be rerunnable after interruption. No replacements were made during this inspection.

### Step 11 — Validate without operating the app

Approved invocation, once implemented:

```text
cimt validate --config default.yaml --run-config app.yaml
```

Expected: local HTML describing configuration, text paths/URLs, Git branch access, tooling, device readiness, credential presence, and model/budget configuration. It must not build/install/reset or make paid AI calls. Actual app login, signing, and model access remain execution-time checks.

### Step 12 — Execute the first real test

Use a user-supplied .NET MAUI application; CIMT will not include a demo app. Supply its Git URL, branch, solution/project, targets, instructions, and optional requirements/setup.

Approved invocation:

```text
cimt run --config default.yaml --run-config app.yaml
```

Create and validate CIMT's installed default Android/iOS build scripts during this work. Check reset/login, credential masking, step screenshots, crash recovery, strict AI budget, HTML output, and clone cleanup. Record actual versions, exact commands, outputs, and any manual steps in this guide.

A replay demo will then use:

```text
cimt replay --config default.yaml --run-config app.yaml --scenario <saved-scenario-path>
```

All command/script examples require runnable demonstrations against the user-supplied app. They are not delivered by this initial inspection.

### Step 13 — Repeat under Jenkins and on another Mac

Run the same validate/run commands from the Jenkins execution account with access to physically connected devices. Verify paths, signing access, Git authentication, configuration permissions, and report retention under that account; an interactive developer account's readiness does not establish Jenkins readiness.

Finally, follow this guide on a second supported Intel Mac and complete acceptance testing. Add missing details until the process can be repeated without relying on knowledge of the first machine.

## 5. First-Mac inspection — 28 October 2026

Inspection only: no dependency installations, tool replacements, credential changes, app builds, or device actions were performed. Temporary diagnostic output was used; device identifiers and credential values are not included here.

| Item | Observed result | Readiness implication |
| --- | --- | --- |
| Host | iMac20,1; Intel Core i9-10910 at 3.60 GHz; x86_64; 16 GB RAM. | Matches initial Intel architecture scope; not a minimum hardware specification. |
| macOS | 26.7.1, build 25G241. | Observed, not yet a validated CIMT support baseline. |
| Storage | Approximately 17 GiB available on the inspected volume. | Assess package/build/evidence space before installation; no automatic deletion authorized in this inspection. |
| Git | Apple Git 2.50.1. | Executable present. |
| Terminal Git route | Noninteractive SSH access to CIMT failed because GitHub's ED25519 host key is not trusted in the inspected account. | Complete verified host-trust setup, then retest credentials/repository access. No known-hosts changes made. HTTPS and the target app repository were not tested. |
| Local documentation folder | Existing CIMT folder has no .git checkout. | Files are local documentation copies; not proof of terminal Git authentication. GitHub connector access works separately. |
| Xcode | 26.5, build 17F42; selected /Applications/Xcode.app/Contents/Developer. | Tools present; version still needs matching to app/.NET workload. |
| Xcode first-launch check | Successful exit outside the restricted inspection context. | Basic setup check passes; not a signing/install test. |
| iPhoneOS SDK | 26.5. | Observed; actual target-device compatibility needs validation. |
| .NET SDKs | 3.1.413, 3.1.420, 5.0.401, 5.0.408, 9.0.302, 10.0.401. | Reuse only a validated selection; no SDK removed or changed. |
| .NET 10 runtime | Microsoft.NETCore.App and Microsoft.AspNetCore.App 10.0.12. | Present; app execution not tested. |
| MAUI workloads | maui-android and maui-tizen, manifest 10.0.110/10.0.100; installed list reports workload version 10.0.401.1. | Android workload present; reported installed list lacks maui-ios. Tizen is not a CIMT target. |
| Java/JDK | Java launcher exists, but java_home reports no Java runtime; no JDK found in checked standard locations. | Prepare/validate a compatible JDK. A launcher stub is not an installed JDK. |
| Android tools | adb, sdkmanager, emulator absent from PATH; SDK absent from checked conventional locations. ANDROID_HOME/ANDROID_SDK_ROOT unset. | Physical Android readiness not testable yet. Custom uninspected install paths are not ruled out. Emulator is not required. |
| Node/npm | Not found in PATH or checked conventional/version-manager locations. | Supporting runtime to evaluate after adapter selection. |
| Homebrew | 4.4.1 at /usr/local/Homebrew/bin/brew; brew not on inspected PATH. | Installation exists; discovery/PATH must not assume absence. Homebrew is not yet a selected product dependency. |
| Paired Apple devices | Three paired entries: iPadOS/iOS 18.3, 18.6.2, and 27.0.1; all unavailable. | No usable connected Apple device established. Pairing history is not availability. Validate OS/toolchain compatibility after reconnecting. |
| Provisioning profiles | 37 files in the current user's Xcode profile location. | Presence only; identities, private keys, validity, app/device coverage not checked. |
| Jenkins | No Jenkins entries found in checked conventional launch-service/home/package locations. | Not proof of absence elsewhere. Server execution account and readiness not validated. |
| CIMT/adapter | No cimt or appium executable found on PATH; adapter unselected. | Product implementation and adapter evaluation pending. |
| OpenAI/configuration | No private keys/configuration inspected; no API requests sent. | No claim of model access, pricing validation, or strict-budget readiness. |

### Inspection-context limitations

Restricted process checks initially blocked hardware properties and Apple's device service, and produced a workload-verification warning. Hardware, workload listing, Xcode first-launch status, and Apple-device discovery were rechecked outside that restricted context. Workload listing succeeded there without the warning. The restricted xctrace device listing also failed; the successful devicectl check is the basis for the availability finding.

These inspection restrictions are not established Mac defects. Normal CIMT execution must be validated directly under its intended account.

### Gap list for the next implementation steps

1. Select and verify the application/toolchain compatibility matrix before installing or replacing versions.
2. Resolve GitHub SSH host trust and retest noninteractive Git access.
3. Plan sufficient free storage for pinned packages, builds, and reports.
4. Prepare/validate JDK, Android SDK/platform-tools, and matching iOS MAUI workload.
5. Connect/authorize an Android device and make a paired iPhone available.
6. Evaluate/install the selected adapter and its supporting runtime.
7. Implement CIMT bootstrap/setup and validate/run/replay; then verify signing, reset, masking, budgeting, and reports against the real app.
8. Repeat under Jenkins and on the second Intel Mac.

No implementation-versus-definition deviation has been introduced. The findings identify missing prerequisites and unvalidated compatibility; they do not change approved scope.

## 6. Updating this guide during implementation

For each completed installation or test step, record:

- Exact pinned versions, download source/package integrity method, and compatible host/device versions.
- Commands/configuration actually used and expected verification output.
- Automatic changes and remaining manual actions.
- Execution account, permissions, rerun/recovery behaviour, and failure diagnosis.
- Evidence that the step works on the first and second Intel Macs.

Keep untested instructions labelled pending until verified. If implementation needs to differ from the approved definition, explain the difference and agree the change before revising the baseline.

## 7. Verification record

| Date | Activity | Result |
| --- | --- | --- |
| 28 October 2026 | Read-only first-Mac prerequisite inspection. | Completed; findings above. |
| Pending | Dependency installation and version manifest validation. | Not executed. |
| Pending | CIMT setup/validate command implementation. | Not available. |
| Pending | Physical Android/iPhone build, install, and autonomous testing. | Not executed. |
| Pending | Jenkins and second-Intel-Mac acceptance. | Not executed. |
