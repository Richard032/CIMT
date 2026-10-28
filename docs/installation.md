# CIMT installation and setup guide

Version: 0.2  
Last updated: 28 October 2026  
Status: prerequisite installation and rerun verified on the first Intel Mac; CIMT implementation and end-to-end acceptance pending  
Scope: supported Intel Macs for local command-line and Jenkins execution

## 1. Purpose and current status

This document describes how to prepare another supported Mac, install CIMT, configure an application, and prove that local testing works. Findings from the first Mac are used to improve the repeatable procedure; its particular paths, installed versions, and hardware are examples, not mandatory product defaults.

CIMT's CLI and default application build scripts have not yet been implemented. Prerequisite bootstrap scripts are now available and were executed successfully on the first Intel Mac; section 8 records exact commands, versions, checks, and limitations. Commands beginning with cimt below remain the approved future interface and cannot yet be executed from this repository. The prerequisite helpers are separate from the future YAML-driven cimt setup implementation.

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
| Xcode and iPhone OS | Match Apple support and the selected .NET iOS workload. | Xcode 26.5 retained; matching iOS SDK 26.5.10284 installed in the pilot profile. Device build/install remains unverified. |
| .NET SDK | Support CIMT's implementation and the application's target frameworks/global.json. | Isolated 10.0.300 pilot profile installed alongside existing SDKs; application-specific selection remains to be validated. |
| MAUI Android/iOS workloads | Match the chosen SDK and application. | maui-android and maui-ios installed at workload set 10.0.300.3 in CIMT's separate SDK. |
| JDK and Android SDK/build tools | Match the application's Android targets and selected .NET Android tooling. | JDK 21, Android API 36, build-tools 36.0.0, command-line tools 22.0, and platform-tools 37.0.1 installed. |
| Device adapter | Select after evaluating physical Android/iOS and unattended Intel/Jenkins operation. | Both evaluation candidates installed; no final selection. Mobile MCP startup/tool discovery verified. |
| Supporting runtimes | Provide runtimes needed for adapter evaluation. | Node 22.23.4/npm 10.9.9 installed for both candidates. |
| Git | Noninteractive access under the executing account. | Host trust repaired; private repository authentication still needs user/account setup. |
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

Section 8 records the verified pilot installation command. A different application's SDK/global.json or a different Xcode version may need another validated profile. Do not treat the presence of maui-android as proof that iOS is installed.

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

Both candidates and Node/npm have now been installed for evaluation, as recorded in section 8. Neither candidate has been selected as CIMT's adapter. Installed tooling is not evidence that app control, reset, masking, or unattended real-device execution already works.

### Step 10 — Install CIMT and create configuration

**CIMT CLI implementation pending:** prerequisite bootstrap helpers and an installed-version record are now provided; no CIMT executable/install package is delivered yet. Use section 8 for the verified prerequisite bootstrap. Final packaging and YAML-driven cimt setup remain to be implemented.

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
| 28 October 2026 | Prerequisite helper installation and rerun. | Installed versions verified; final YAML-driven manifest enforcement and app compatibility pending. |
| Pending | CIMT setup/validate command implementation. | Not available. |
| Pending | Physical Android/iPhone build, install, and autonomous testing. | Not executed. |
| Pending | Jenkins and second-Intel-Mac acceptance. | Not executed. |

## 8. Prerequisite installation performed — 28 October 2026

The product owner authorized installing the missing prerequisites. This section supersedes the missing-tool findings in the historical section 5. Existing Xcode and system .NET installations were preserved.

### Verified installation procedure

The pilot installer requires an Intel Mac with selected Xcode 26.5. It uses the existing macOS Bash, curl, tar, unzip, and shasum tools; it does not require Homebrew or Python.

From the CIMT source/documentation directory, execute:

```bash
bash scripts/setup-prerequisites-macos.sh
source /Users/Shared/CIMT/environment.sh
```

The installer defaults to /Users/Shared/CIMT. To use another absolute installation root, set CIMT_INSTALL_ROOT before invoking the script and source that root's environment.sh afterward.

The wrapper performs:

1. Intel/runtime bootstrap through scripts/bootstrap-macos-prerequisites.sh.
2. Version-pinned workloads under the separate SDK:
   dotnet workload install maui-android maui-ios --version 10.0.300.3 --disable-parallel
3. Android and adapter tooling through scripts/install-macos-mobile-tools.sh.

The scripts are preliminary prerequisite helpers, not the completed cimt setup command. They do not yet read setup.yaml/toolchain.manifest. The supplied installed-version YAML is an inventory/profile record; final manifest-driven enforcement remains implementation work.

Activation is explicit so the existing account-wide SDK selection is preserved. Source environment.sh in the developer terminal or Jenkins pipeline before using these tools. No shell startup file was changed.

The profile uses Microsoft's documented .NET 10.0.300 / workload-set 10.0.300.3 combination for Xcode 26.5. A newer workload set requiring another Xcode version was not silently substituted. [Official Xcode 26.5 workload release](https://github.com/dotnet/macios/releases/tag/dotnet-10.0.1xx-xcode26.5-10284).

### Installed and verified versions

| Component | Version / result |
| --- | --- |
| Node.js | 22.23.4, Intel archive. |
| npm | 10.9.9 bundled with Node. |
| Microsoft OpenJDK | 21.0.13.0.2, build 21.0.13.0.2+1-LTS. |
| Isolated .NET SDK | 10.0.300. |
| Workload set | 10.0.300.3. |
| MAUI workloads | maui-android and maui-ios, MAUI SDK 10.0.20. |
| .NET iOS SDK | 26.5.10284. |
| .NET Android SDK | 36.1.53 in the selected workload set. |
| Android command-line tools | 22.0, Intel archive build 15859902. |
| Android platform-tools | 37.0.1; adb 1.0.41. |
| Android platform | API 36, revision 2. |
| Android build-tools | 36.0.0. |
| Appium | 3.9.0. |
| Appium UiAutomator2 driver | 8.7.2. |
| Appium XCUITest driver | 12.22.1. |
| Mobile MCP | 1.0.14; executable mcp-server-mobile. |
| Mobile MCP native Intel helper | mobilecli 1.0.21. |

Download integrity was checked before extraction: Node/JDK/Android archives against official SHA-256 values, .NET against official SHA-512 release metadata. npm verifies package integrity during installation.

Direct package versions are pinned in the helpers. The Android SDK manager resolves platform-tools to its available revision; 37.0.1 was observed here. Fully enforcing every dependency revision from YAML, including package-manager/transitive dependencies, remains part of final setup implementation.

### Verification actually completed

- Bootstrap runtime versions matched the pinned values.
- Both MAUI workloads installed successfully; dotnet workload list reports set 10.0.300.3.
- Android tooling versions and API/build-tools files were checked.
- Both Appium drivers report installed at the selected versions.
- Mobile MCP initialized over local standard input/output and listed 33 tools, including physical-device discovery. This sent no AI requests and did not operate an app.
- The Mobile MCP Intel native helper starts and reports version 1.0.21.
- The complete prerequisite wrapper was run again successfully; existing runtime installations and matching drivers were reused.
- All three helper scripts passed Bash syntax checks.

Install logs remain locally under /Users/Shared/CIMT/logs. About 7.5 GiB of tools were installed; approximately 9.9 GiB remained free at verification. No unrelated files or developer SDKs were removed.

### Driver diagnostics and physical-device scope

XCUITest's doctor reports zero required fixes. It also reports optional simulator/video/Remote-XPC components absent; these features were not enabled.

UiAutomator2's generic doctor reports one required fix because its check assumes an Android emulator executable. CIMT's initial requirement is physical devices, and adb/platform-tools are installed. The emulator warning is recorded, not reported as an all-green diagnostic and not used to expand CIMT's device scope. Actual Android control still requires a connected phone and application test.

Video/streaming utilities, Android emulator/images, and simulator-specific helpers were not installed as CIMT physical-device prerequisites.

Some optional XCUITest Remote-XPC/tunnel features mention administrator privileges. Ordinary CIMT runs must remain unprivileged; the adapter evaluation must prove a compliant real-device path before selection. Installing a candidate is not approval of a privileged runtime design.

### Git trust and remaining authentication

GitHub's ED25519 key was retrieved from its official HTTPS metadata, matched to its published fingerprint, and added to the current account's known_hosts. Host verification now succeeds.

The SSH repository check subsequently failed with Permission denied (publickey). The noninteractive HTTPS check also found no credentials. No private key, token, or GitHub account credential was generated or exposed.

Complete Git authentication under the intended executing account and rerun the section 4 Git check before private cloning. [GitHub host fingerprints](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/githubs-ssh-key-fingerprints).

### Device state after installation

- adb started successfully and returned no connected Android devices.
- Apple device discovery now shows one connected iPhone running iOS 27.0.1; two other historical paired entries remain unavailable.
- The connected iPhone's install/signing/control compatibility with Xcode 26.5 and the selected adapter is unverified. Device visibility alone is not proof of readiness.
- No application was built, installed, reset, or operated.

### Remaining before CIMT can execute a test

1. Implement the CIMT CLI and final YAML-driven setup; the prerequisite helpers do not provide autonomous testing.
2. Configure noninteractive Git authentication and supply the first real application's repository/branch.
3. Connect and authorize an Android device; validate the available iPhone, including signing and its OS/toolchain requirements.
4. Complete both adapters' real-device evaluation before selecting one.
5. Implement and verify application builds, reset/login, element-ID masking, strict OpenAI budget, evidence, and reports. OpenAI credentials/model access were not configured or tested by this prerequisite installation.
6. Repeat the complete procedure under Jenkins and on the second Intel Mac.

No approved product behaviour was changed. The installed profile and helper scripts are an implementation increment; full application compatibility, manifest enforcement, and end-to-end acceptance remain explicitly unverified.
