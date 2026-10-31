# CIMT installation and setup guide

Version: 0.28
Last updated: 30 October 2026  
Status: prerequisites, CLI, build workers, and initial run engine installed on the first Intel Mac; real application acceptance pending  
Scope: supported Intel Macs for local command-line and Jenkins execution

## 1. Purpose and current status

This document describes how to prepare another supported Mac, install CIMT, configure an application, and prove that local testing works. Findings from the first Mac are used to improve the repeatable procedure; its particular paths, installed versions, and hardware are examples, not mandatory product defaults.

The CLI/configuration foundation, default Android/iOS build workers, and initial single-objective run engine are implemented. cimt validate produces readiness reports; setup and saved-action-history replay remain unimplemented; replay without --scenario reuses retained builds with current testing instructions. Prerequisite bootstrap scripts ran successfully on the first Intel Mac. Section 8 records installed tools; section 10 records earlier increments and source installation commands; section 14 adds the run-engine support runtime and first real-app example. The prerequisite helpers remain separate from the future YAML-driven setup engine.

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
| Git | Noninteractive access to the configured application repository under the executing account. | Supplied Subgit application URL verified successfully with the current Mac Git configuration. GitHub terminal authentication is separate and is not a prerequisite for this application. |
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

Work and report folders share a timestamp. Reports must remain outside the temporary cleanup folder. New runs use one UTC millisecond timestamp for both names; collisions advance that shared timestamp. See [run identity](run-identity.md).

A shared installation such as /Users/Shared/CIMT is an example, not a required location. Private YAML files must remain accessible only to the intended account(s), outside source control.

### Step 3 — Prepare Git and private repository access

1. Check git --version.
2. Configure the host's existing Git authentication for the intended repository URL.
3. For SSH, verify the server fingerprint through the hosting provider's official documentation before establishing host trust.
4. Test noninteractive access with the actual repository and account.

Verified application example (the URL remains configurable for other applications):

```bash
GIT_TERMINAL_PROMPT=0 GCM_INTERACTIVE=never git ls-remote --symref https://subgit.curtis.ch/ECON/ag-econ-mobile.git HEAD
```

Success prints the default-branch reference and HEAD commit. The supplied application URL succeeded noninteractively on this Mac. Its advertised default is main, but CIMT's configured test branch must still be explicit. The current Git credential helper is osxkeychain; no credential values were inspected. This verifies repository read access, not a clone/build or access under another account.

For SSH URLs, host-key failure means verified trust setup is needed; it does not prove credentials are wrong. Do not disable host verification. GitHub connector access and terminal Git access are separate.

The GitHub-specific procedure below is relevant to source maintenance while CIMT itself remains on GitHub; it is not required for the tested application's HTTPS Subgit URL. For GitHub's manual trust/authentication test, follow its fingerprint verification procedure. [GitHub SSH connection guide](https://docs.github.com/en/authentication/connecting-to-github-with-ssh/testing-your-ssh-connection).

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

Both candidates and Node/npm are installed. Android control probes passed for both candidates. Following Xcode account recovery, Appium iPhone signing and 11 UI/screenshot/navigation checks passed. Mobile MCP's DeviceKit helper is installed and eight guarded iPhone smoke checks passed after unlocking (section 13). Final selection requires the complete gate in the [adapter evaluation](adapter-evaluation.md); reset, masking, and unattended app testing remain unverified.

### Step 10 — Install CIMT and create configuration

The CLI foundation is installed on the first Mac. Follow section 10 to build/install it from source after the prerequisite bootstrap in section 8. Final packaging and YAML-driven cimt setup remain to be implemented; the setup invocation below is the approved future interface.

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

Implemented invocation:

```text
cimt validate --config default.yaml --run-config app.yaml
```

Implemented: local HTML describing configuration, text paths/URLs, Git branch access, tool availability, connected-device inventory, credential presence, and model/budget configuration. It must not build/install/reset or make paid AI calls. Actual app login, signing, and model access remain execution-time checks.

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

### Historical gap list from the initial inspection

Sections 8 and 9 record subsequent installation and application-repository access results.

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

These failures concerned GitHub terminal access, not the subsequently supplied application repository. The application's HTTPS Subgit read check succeeded as recorded in section 9. No GitHub terminal authentication change is required for that application; verify each configured repository under its actual execution account. [GitHub host fingerprints](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/githubs-ssh-key-fingerprints).

### Device state after installation

- adb started successfully and returned no connected Android devices.
- Apple device discovery now shows one connected iPhone running iOS 27.0.1; two other historical paired entries remain unavailable.
- The connected iPhone's install/signing/control compatibility with Xcode 26.5 and the selected adapter is unverified. Device visibility alone is not proof of readiness.
- No application was built, installed, reset, or operated.

### Remaining before CIMT can execute a test

1. Implement the CIMT CLI and final YAML-driven setup; the prerequisite helpers do not provide autonomous testing.
2. The first application URL is now supplied and its Subgit read access verified. Select an explicit test branch and application build configuration before the first run; validate access separately under Jenkins.
3. Connect and authorize an Android device; validate the available iPhone, including signing and its OS/toolchain requirements.
4. Complete both adapters' real-device evaluation before selecting one.
5. Implement and verify application builds, reset/login, element-ID masking, strict OpenAI budget, evidence, and reports. OpenAI credentials/model access were not configured or tested by this prerequisite installation.
6. Repeat the complete procedure under Jenkins and on the second Intel Mac.

No approved product behaviour was changed. The installed profile and helper scripts are an implementation increment; full application compatibility, manifest enforcement, and end-to-end acceptance remain explicitly unverified.

## 9. Application repository and future CIMT migration

The product owner supplied the first application repository:

```text
https://subgit.curtis.ch/ECON/ag-econ-mobile.git
```

A noninteractive Git reference check succeeded on 28 October 2026 using the Mac's existing configuration. It advertised refs/heads/main and a HEAD commit. The configured credential helper is osxkeychain; no passwords, tokens, or private keys were read or changed. Access is verified for the current execution account only.

The existing local ECON-Mobile checkout also points at this application URL. CIMT will still clone from the configured Git URL into its owned temporary folder; the existing checkout was not modified or substituted for that workflow. No application clone, build, or test was performed in this access check.

Repository locations are separate:

| Purpose | Current location | Plan |
| --- | --- | --- |
| Application under test | Subgit URL above. | Use configurable repository URL and explicit test branch. |
| CIMT product code/documentation | https://github.com/Richard032/CIMT | Move to Subgit later, as requested; destination and migration steps are not yet supplied. |

The earlier GitHub terminal-authentication failures are not a blocker for reading this application repository. Future Jenkins/server accounts must establish their own authorized access. No source-repository migration has been performed.

## 10. Three autonomous implementation increments — 28 October 2026

[Reviewed status](implementation-status.md) records each increment and remaining work.

1. Both physical devices were available. Mobile MCP and Appium passed Android control probes. Initial iPhone signing failed; after the Xcode account recovery in sections 11–12, Appium helper signing and 11 iPhone control checks passed. Mobile MCP's separate DeviceKit helper was subsequently installed with a matching wildcard profile (section 13); eight guarded iPhone smoke checks subsequently passed after unlocking. Final adapter selection remains open; its earlier Mobile MCP preference was provisional.
2. The .NET CLI/configuration foundation is built and installed at /Users/Shared/CIMT/bin/cimt, with assemblies under lib/cimt. Source environment.sh to put it on PATH. Fifteen checks passed, and real readiness validation reached Subgit and both connected-device inventories. Only synthetic credential presence was tested; no AI request was made.
3. Default Android/iOS scripts are installed under scripts/build, with worker assemblies under lib/cimt-build. Four simulated build-contract checks passed. Actual builds on main with submodules were attempted: Android stops at the repository's Windows-only pre-build commands, and iOS lacks an available provisioning profile. No successful artifact was produced.

The original application checkout remains untouched. Raw device evidence and build logs remain local; no screenshots, device IDs, signing identities, or credentials are committed. Temporary application clones are deleted after evaluation; retained evidence is outside them.

At this increment only validate was implemented; setup/run/replay returned explicit errors. Section 14 supersedes that run status with the initial execution engine. The complete approved product and its acceptance checks remain unfinished.

Development verification commands:

```bash
source /Users/Shared/CIMT/environment.sh
dotnet build src/Cimt/Cimt.csproj -c Release
dotnet run --project tests/Cimt.Checks/Cimt.Checks.csproj -c Release
dotnet build tools/Cimt.BuildWorker/Cimt.BuildWorker.csproj -c Release
python3 tests/check-build-contract.py
cimt --help
```

See the [build contract](build-script-contract.md) for actual script invocation and the [adapter evaluation](adapter-evaluation.md) for the signing prerequisites. A valid development identity/profile and a macOS-compatible application pre-build path are required before app acceptance can proceed. No signing or source build step was bypassed.


### Install the foundation from source on another prepared Intel Mac

From the CIMT source folder, after completing section 8:

```bash
source /Users/Shared/CIMT/environment.sh
mkdir -p "$CIMT_INSTALL_ROOT/bin" "$CIMT_INSTALL_ROOT/scripts/build"
dotnet publish src/Cimt/Cimt.csproj -c Release -o "$CIMT_INSTALL_ROOT/lib/cimt"
dotnet publish tools/Cimt.BuildWorker/Cimt.BuildWorker.csproj -c Release -o "$CIMT_INSTALL_ROOT/lib/cimt-build"
cp scripts/cimt "$CIMT_INSTALL_ROOT/bin/cimt"
cp scripts/build/android.sh scripts/build/ios.sh "$CIMT_INSTALL_ROOT/scripts/build/"
chmod +x "$CIMT_INSTALL_ROOT/bin/cimt" "$CIMT_INSTALL_ROOT/scripts/build/"*.sh
bash scripts/install-cimt-runtime.sh
cimt --help
```

These commands install the supplied defaults. Keep custom replacements in separate files. Copy examples/default.example.yaml and examples/econ-app.example.yaml to private configuration locations, adjust their relative text paths and values, and restrict secret files to owner read/write before validation. The default example deliberately has an empty API key and a model placeholder. No live key is needed for the synthetic development checks above; real configuration/readiness validation requires configured values but does not authenticate to OpenAI.

This source-install procedure was executed on the first Mac. Repeating it on another Intel Mac, final distribution packaging, and the complete YAML-driven setup command remain acceptance work.


## 11. Connected iPhone recheck — 28 October 2026

### Verified on the first Mac

- The phone is a physical iPhone 14 running iOS 27.0.1. A user-assigned device name may describe a different model; use hardware properties to identify it.
- Wired connection, pairing, Developer Mode, developer disk-image services, and the device tunnel are available.
- Mobile MCP's on-device agent is not installed.
- One valid legacy iPhone Developer identity is available. Matching, unexpired app-specific development profiles also exist. **Correction:** the previous conclusion that no development identity was available was too broad. Legacy iPhone Developer identities must be recognized alongside Apple Development identities.
- The available wildcard profiles for this phone are expired. Existing ECON app-specific profiles do not cover the automation helper.
- A dedicated WebDriverAgent build with automatic provisioning enabled was attempted. It exited 65 because Xcode rejected its saved Apple-account login and could not obtain the helper's development profile. No successful helper build, installation, or iPhone UI-control result was produced.

Raw device/signing details and the build log remain in the private evaluation folder. Device identifiers, account email, certificate fingerprints, and provisioning files are not included in this repository.

### Manual Apple-account recovery

1. Open Xcode → Settings → Accounts on the Mac under the user account that will run CIMT.
2. Select the existing Apple account for the development team and sign in again. Complete Apple's authentication prompts locally; never put the Apple password in CIMT input files or chat.
3. Confirm the required team is available. If account access or profile creation is restricted, have the team's authorized Apple administrator prepare a development profile for the helper instead.
4. Check signing identities with security find-identity -v -p codesigning. Confirm a valid identity and its private key match a certificate included in the chosen profile; a certificate file alone is insufficient.
5. Supply an unexpired iOS development profile that includes the test phone and permits the automation helper's bundle identifier. A suitable team wildcard profile can cover Mobile MCP's helper; an unrelated app-specific profile cannot. Do not rename the helper to an existing application identifier.

The product owner subsequently restored Xcode sign-in. Retrying the dedicated build succeeded, produced a valid development profile including the connected phone, and passed signature verification. See section 12 for the launch/control follow-up.

### Retry the Appium helper provisioning check

The first-Mac check used the installed WebDriverAgent project. Substitute the actual team, phone UDID, and a new private evidence folder. Keep this helper identifier separate from tested applications.

```bash
source /Users/Shared/CIMT/environment.sh
xcodebuild \
  -project "$APPIUM_HOME/node_modules/appium-xcuitest-driver/node_modules/appium-webdriveragent/WebDriverAgent.xcodeproj" \
  -scheme WebDriverAgentRunner -configuration Debug \
  -destination "id=<phone-udid>" \
  -derivedDataPath "<private-evidence-folder>/wda-build" \
  -allowProvisioningUpdates -allowProvisioningDeviceRegistration \
  CODE_SIGN_STYLE=Automatic DEVELOPMENT_TEAM="<team-id>" \
  CODE_SIGN_IDENTITY="iPhone Developer" \
  PRODUCT_BUNDLE_IDENTIFIER=ch.curtis.cimt.WebDriverAgentRunner \
  build-for-testing
```

Use Apple Development instead if that is the valid identity on the new Mac. This prepares a separate candidate helper; it does not install Mobile MCP's agent or establish the final adapter decision. A successful build must be followed by an actual session, UI, screenshot, and navigation check.

### Install Mobile MCP's helper with a valid profile

After account/profile recovery, the installed native CLI exposes this procedure:

```bash
source /Users/Shared/CIMT/environment.sh
CIMT_MOBILECLI="$(node -e 'const {Mobilecli}=require(process.env.CIMT_INSTALL_ROOT+"/tools/node-packages/lib/node_modules/@mobilenext/mobile-mcp/lib/mobilecli.js"); process.stdout.write(Mobilecli.getMobilecliPath())')"
"$CIMT_MOBILECLI" agent install \
  --device "<phone-udid>" \
  --provisioning-profile "<absolute-path-to-valid-helper.mobileprovision>"
"$CIMT_MOBILECLI" agent status --device "<phone-udid>"
```

The command syntax is confirmed by the installed CLI help. Successful agent installation is pending the valid profile. Then run the engineering probe from the CIMT source folder:

```bash
python3 scripts/evaluate-mobile-mcp.py --output "<new-private-evidence-folder>"
```

The probe checks up to two connected physical devices, opens Settings, reads UI elements, captures a screenshot, swipes, and returns Home. These smoke checks do not reset application data or prove MAUI application acceptance. Raw results stay private. Stop the native daemon before switching Android ownership to Appium.

References: [Mobile CLI real-device setup](https://github.com/mobile-next/mobilecli#ios-real-devices), [Appium real-device preparation](https://appium.github.io/appium-xcuitest-driver/latest/getting-started/device-setup/).


## 12. Helper build after Xcode account recovery — 28 October 2026

The product owner restored Xcode account access. The same dedicated WebDriverAgent build then completed successfully (exit 0). Its embedded development profile includes the connected phone and expires on 28 October 2027. Strict signature verification passed. This confirms this helper build on the inspected Mac; it is not a general guarantee for every iOS/Xcode version.

### Which helper is used here

WebDriverAgentRunner (WDA) is the on-device automation helper supplied with Appium's XCUITest driver. It uses Apple's XCTest/XCUITest services to let the Mac inspect UI, take screenshots, and send user actions. The Mac runs Appium; the signed test runner runs on the physical iPhone.

This check uses the separate ch.curtis.cimt.WebDriverAgentRunner identifier (runner suffix .xctrunner). It builds the helper from the installed Appium dependency and does not change the MAUI application's source or identity. It does not run an AI model. Creating the helper profile and building it does not prove successful device installation or control.

Mobile MCP uses a different helper, DeviceKit. It was subsequently installed using a matching wildcard profile; section 13 records the results and remaining control check. WDA is being evaluated as the other adapter candidate; its successful build does not select the final CIMT adapter.

### Reuse the signed helper for the control check

Start the local Appium server and keep the iPhone unlocked. After the build in section 11, invoke the engineering probe from the CIMT source folder:

```bash
source /Users/Shared/CIMT/environment.sh
appium --address 127.0.0.1 --port 4727 --log "<private-log-path>"
```

In a second activated terminal:

```bash
python3 scripts/evaluate-appium.py \
  --output "<private-evidence-folder>" --platform ios \
  --team "<team-id>" --signing-id "iPhone Developer" \
  --wda-bundle-id ch.curtis.cimt.WebDriverAgentRunner \
  --derived-data "<private-evidence-folder>/wda-build" \
  --use-prebuilt-wda
```

The engineering probe currently reads devices-private.json from the evidence folder; it is a private list of objects with platform and id values captured during discovery. It is not a user-facing CIMT run command. --signing-id may instead be Apple Development on another Mac.

The check opens Settings, reads the UI tree, captures a screenshot, verifies the foreground application, presses Home, verifies SpringBoard, reopens Settings, verifies its return, and closes the test session. Save evidence locally and stop the temporary server after the check.

A locked phone can allow the build to finish but prevent the test runner from launching. Xcode explicitly reported that the phone must be unlocked during the first control attempt. Keep it unlocked for initial installation and launch; do not put its passcode in CIMT configuration or attempt to bypass the lock screen. Unattended device-readiness handling still requires implementation and acceptance testing.


### Recorded result and remaining scope

The Appium session installed/launched the signed WDA helper on the physical iPhone. UI source and Settings screenshots passed. The first immediate foreground query after Home still reported Settings; that result remains in private evidence. A bounded eight-second wait for the expected foreground application was added without changing the assertion. On retry, all 11 checks passed, including SpringBoard verification, a Home screenshot, Settings reactivation, and session closure. The Home transition was observed after approximately 1.2 seconds.

Settings and Home screenshots were visually checked locally. No screenshots, UI trees, real device identifiers, or signing secrets were added to the repository. Session closure succeeded; the temporary local Appium server and its owned test process were stopped. WDA remains installed for future checks.

This completes basic Appium iPhone control on this Mac. Mobile MCP uses a separate helper/profile, subsequently installed in section 13; its guarded iPhone Settings/UI/screenshot/navigation check subsequently passed after unlocking. Input entry, real MAUI install/reset/login/crash flows, simultaneous two-device testing, Jenkins operation, and final adapter acceptance remain open.


## 13. Mobile MCP DeviceKit installation — 28 October 2026

### Signing and installation verified

After the Xcode account/profile refresh, the profile inventory includes an unexpired team wildcard development profile that includes the physical iPhone and references available signing identities. Both legacy iPhone Developer and Apple Development identities are now present. The wildcard profile was checked for expiry, development entitlement, device inclusion, and certificate/private-key identity matching before use.

The stock native Mobile CLI agent install command from section 11 succeeded with that profile and reported DeviceKit 0.0.35 installed. Its bundle identifier is com.mobilenext.devicekit-iosUITests.xctrunner. No helper source changes, bundle renaming, or signing bypass was required. DeviceKit is separate from the previously installed Appium WebDriverAgent helper.

The installation command is verified on this Mac. On another Mac, supply a profile that matches that Mac's actual available identity and test phone; copying a profile without its matching private key is insufficient. Keep profile files, certificate/private-key material, and raw installation diagnostics outside source control.

### Lock-state readiness finding

The first Mobile MCP probe returned UI data and screenshots, but the phone had locked again. The captured screen was the passcode screen; launching Settings timed out. Those results are retained as failed application-readiness evidence. Successful screenshot or button commands alone do not prove an application workflow passed.

The engineering probe now checks the supported devicectl JSON lock-state output before iPhone application actions:

```bash
xcrun devicectl device info lockState \
  --device "<phone-udid>" --timeout 15 \
  --json-output "<private-evidence-folder>/lock-state.json"
```

The result.passcodeRequired field must be false. A locked or unknown state stops that phone's probe before launch, screenshot, swipe, or Home actions. The user unlocks the phone locally; CIMT must not collect its passcode or bypass the screen lock. This guard is implemented in the engineering probe; equivalent readiness handling in the full run engine remains implementation work.

### Run the iPhone-only probe

After unlocking the phone, keep it unlocked while checking:

```bash
source /Users/Shared/CIMT/environment.sh
python3 scripts/evaluate-mobile-mcp.py \
  --output "<new-private-evidence-folder>" --platform ios
```

--platform ios limits this engineering check to connected iPhones. Without a platform filter it checks up to two available physical devices. The probe records lock readiness, Settings launch, UI inspection, screenshots, swipe, and Home UI/screenshot results. Device identifiers, raw UI, and images stay in the private evidence folder. Use a fresh folder to preserve each attempt.


### Successful guarded check after unlocking

After the product owner unlocked the phone, a new iPhone-only probe completed with all eight checks passed: unlocked readiness, Settings launch, UI elements, Settings screenshot, swipe command, Home command, Home UI elements, and Home screenshot. The Settings and Home images were inspected locally and show the expected screens. This result supersedes the temporary phone-lock blocker above; the previous failed attempts remain preserved.

Evidence is in a fresh private evaluation folder. Raw screenshots, UI text, identifiers, and signing details were not committed. The MCP client exited, the temporary native daemon was stopped, and DeviceKit remains installed for reuse.

Both Mobile MCP and Appium now have basic physical Android/iPhone control evidence on this Mac. This does not finish the selection gate: text input, simultaneous-device operation, real MAUI build/install/reset/login/crash flows, Jenkins, and the complete acceptance criteria remain unverified. The next application-build validation must account for the refreshed signing profiles rather than assume the earlier provisioning failure still applies.

## 14. Initial run engine and application example — 28 October 2026

### Install the support runtime

The public run command now delegates screen processing and bounded action selection to a local Python worker. The prerequisite helper also calls scripts/install-cimt-runtime.sh. It creates an isolated environment under the selected installation root and installs Pillow 13.0.0 and truststore 0.10.5. It does not replace the Mac's global Python.

Python 3.11 or newer must already be available. The helper searches PATH and conventional python.org locations. If absent, install a compatible Intel Python from the [official macOS downloads](https://www.python.org/downloads/macos/), then rerun. A selected executable can be supplied as CIMT_PYTHON_BOOTSTRAP. On the first Mac, the existing Python 3.14.8 was reused; no new global Python installation was needed. This remains a documented manual prerequisite until final setup automation.

From the CIMT source folder, after the prerequisite environment is prepared:

```bash
source /Users/Shared/CIMT/environment.sh
bash scripts/install-cimt-runtime.sh
dotnet publish src/Cimt/Cimt.csproj -c Release -o "$CIMT_INSTALL_ROOT/lib/cimt"
cp scripts/cimt "$CIMT_INSTALL_ROOT/bin/cimt"
chmod +x "$CIMT_INSTALL_ROOT/bin/cimt"
```

Keep the installed default build workers from section 10. The worker uses the Mac trust store for OpenAI HTTPS; TLS verification is enabled. Install dependencies through the helper rather than into a system Python. See [run-engine notes](run-engine.md) for architecture, policy checks, and remaining implementation limits.

### Prepare the user-facing example

All app-specific configuration and support files are in [examples/econ-button-crash](../examples/econ-button-crash/README.md). The example selects main, both Release_Generic/Release_Pride targets, and Android/iOS. It supplies a macOS adapter preserving the existing tagger through Mono and MSBuild Copy. Mono is an application-specific prerequisite: the first Mac already had Mono 6.12.0.206 at /Library/Frameworks/Mono.framework/Versions/Current/Commands/mono. Ensure mono is available on PATH when using this example. Real tagger/build compatibility is still unverified; the import passed an MSBuild fixture only.

Copy default.example.yaml to default.private.yaml inside the example and restrict permissions to owner read/write. Enter the existing OpenAI API key locally in ai-model.api-key. Named login credentials, if needed, also belong in private YAML. The prepared local development copy has no key yet. Never commit private configuration or paste its secret values into chat.

```bash
source /Users/Shared/CIMT/environment.sh
cimt validate --config examples/econ-button-crash/default.private.yaml --run-config examples/econ-button-crash/application.example.yaml
cimt run --config examples/econ-button-crash/default.private.yaml --run-config examples/econ-button-crash/application.example.yaml
```

Jenkins uses the same run command. Its execution account still needs Git credentials, signing, device trust, an unlocked usable signing keychain, and access to the phones. Keep the test phones unlocked; CIMT does not enter device passcodes. No Jenkins acceptance run has been performed.

The example allows 60 minutes and USD 5 across the entire run. Its explicit model is gpt-5.4-mini-2026-03-17. The initial runtime rejects models/currencies without a validated pricing bound. Review these settings before use. The runtime checks model-read access before builds and uses Responses for action selection; validation alone checks configured credential presence rather than provider access.

### Review of this step

Done: installed support runtime, public run integration, example files, macOS target adapter, and local report/cleanup paths. Eighteen CLI/lifecycle checks, 13 runtime-policy checks, four simulated build-contract checks, and one MSBuild adapter fixture passed. These are development checks, not real app tests.

Blocked: the example's private key field is empty. Running the installed public validate command produced exit 3 and a timestamped HTML error report under the example's reports folder. No OpenAI inference, real application build through the new adapter, reset/install, or button exploration occurred in this step. The user selected an existing key; its usable local source is still pending.

Remaining: validate with that key, run the example through the public command, inspect signed APK/IPA and physical-device evidence, and resolve any failures in the example integration. iOS reinstall verifies container reset; Keychain or backend reset needs app-specific hooks. Final adapter choice, supported manifest, setup/replay, full scenarios, Jenkins, and second-Mac acceptance remain open.


## 15. Maintain the refactored source installation

The refactor keeps the installed commands and runtime requirements. It adds source modules and unit-test projects. From the source folder, verify a prepared Mac with:

```bash
bash scripts/check-development.sh
```

After the review fixes, the first Mac passed 126 unit tests (62 .NET and 64 Python) and 23 regression/contract checks: 149 checks in total. These use simulated tools, API responses, and phones; they do not run the real MAUI application. See the [development guide](development.md).

After successful checks, update both .NET components and all Python support modules:

```bash
source /Users/Shared/CIMT/environment.sh
dotnet publish src/Cimt/Cimt.csproj -c Release -o "$CIMT_INSTALL_ROOT/lib/cimt"
dotnet publish tools/Cimt.BuildWorker/Cimt.BuildWorker.csproj -c Release -o "$CIMT_INSTALL_ROOT/lib/cimt-build"
bash scripts/install-cimt-runtime.sh
cp scripts/cimt "$CIMT_INSTALL_ROOT/bin/cimt"
chmod +x "$CIMT_INSTALL_ROOT/bin/cimt"
```

The runtime installer copies every supplied Python module. Copying only agent.py, mobile.py, and run_ui.py is no longer sufficient. Existing private configuration and application examples remain valid. The same phone helpers are used; real-device acceptance remains pending.

## 16. Review-fix installation check

The review fixes use the same installation commands in section 15. No new dependency, phone helper, YAML field, or command is required. Republish the host and build worker, then run the support runtime installer so check_results.py and device_scheduler.py are included. Preserve private configuration files.

The offline suite verifies functional findings, a result returned as a time limit expires, unresolved-check resolution, sensitive-screen transitions, preserved crash evidence, native command errors, custom-script YAML fallbacks, and clone cleanup after helper failure. These are source checks for a prepared Mac. A signed application build and physical-device exploration still need their separate acceptance run. The iPhone is unavailable at this review; no iPhone operation was attempted.

First-Mac result: both .NET components were republished successfully, support dependencies were already installed, and all Python modules were copied. The public cimt --help command returned successfully. Installed host and Python module files match the corrected source build.

## 17. Install the requirement-mapping increment

Use the same republish and runtime-install steps in section 15. No additional dependency, YAML field, API key, or phone helper is introduced. Update both the host and all Python support modules together: the runtime request and check-response contracts now include requirement IDs and current results.

New reports retain requirements.json with the complete catalogue and redacted source fingerprint. result.json and HTML include every item and applicable target/device result, even when builds or device execution did not start. Existing private YAML and text-input paths continue to work.

To check the report on any prepared development Mac without devices or API access, run the [offline mapping demonstration](../examples/requirement-mapping/README.md). Its five synthetic statuses produce expected exit 1 with incomplete completion. Run the full development suite before installing source changes. This check is separate from signed real-app/device qualification.

First-Mac mapping installation verified: republished the host, copied all Python support modules, checked public help, and compared installed files with the source build. Private configuration was preserved.

## 18. Install the shared run-identity increment

Use the host republish and all-module runtime install commands in section 15. No new dependency, YAML field, credential, or device helper is needed. Existing retained report folders are preserved. The ownership reader still supports earlier records so their abandoned work can be checked and removed normally.

New work_<date-time> and report_<date-time> folders use the exact same UTC millisecond timestamp. There is no random work-folder suffix or separate report counter. run-identity.json records the pair and survives clone cleanup. Keep it with the report when archiving. Reports below owned work paths, including aliases, are rejected so cleanup cannot remove them. Validation/early-error reports allocate an identity without creating clone work.

Verified on this Mac with 230 offline development checks. The public-command regression verifies the work name before deletion against the retained report/runtime metadata. The [identity documentation](run-identity.md) covers the completed format/timezone/collision choices and tests. Actual Jenkins/second-Mac execution and full interruption-history acceptance remain open.

First-Mac identity installation verified: republished the host, copied all Python modules, checked public help, and confirmed installed files match the source build. The offline demo retained matching folder, result, and HTML identity metadata. Private configuration and existing reports were preserved.

## 19. Document-heading correction — 28 October 2026

This correction needs no new dependency or configuration setting. Update the host and its action prompt together from the CIMT source folder:

```bash
source /Users/Shared/CIMT/environment.sh
dotnet publish src/Cimt/Cimt.csproj -c Release -o "$CIMT_INSTALL_ROOT/lib/cimt"
cp runtime/action_prompt.py "$CIMT_INSTALL_ROOT/lib/cimt-runtime/action_prompt.py"
cimt --help
```

The first Mac was updated this way after all 254 offline checks passed. Installed host/prompt files were compared with the tested source. The mapping example retains one heading as context and five requirement results. Private configuration was not read or changed. See [mapping rules](requirement-mapping.md); this does not establish real-device acceptance.

## 20. Redaction correction — 28 October 2026

Update the host, build worker, and all Python modules together. The worker now includes record_redaction.py; copying only redaction.py is insufficient. No additional dependency, YAML field, or private configuration change is needed.

```bash
source /Users/Shared/CIMT/environment.sh
dotnet publish src/Cimt/Cimt.csproj -c Release -o "$CIMT_INSTALL_ROOT/lib/cimt"
dotnet publish tools/Cimt.BuildWorker/Cimt.BuildWorker.csproj -c Release -o "$CIMT_INSTALL_ROOT/lib/cimt-build"
cp runtime/*.py "$CIMT_INSTALL_ROOT/lib/cimt-runtime/"
cimt --help
```

First-Mac verification: all 301 offline checks passed. Both installed assemblies and all Python modules match the tested source; public help works. A synthetic result passed through the real Python recorder/journal and .NET writer retains failed and exit 1 for the original status/credential collision. Pixel tests cover Unicode and escaped-character secrets. No private configuration was read or changed, and no phone or API was used. Historical reports are preserved. See [redaction behavior and limits](redaction.md).

## 21. Screenshot-masking correction — 28 October 2026

This update changes Python support modules only. Keep the existing native helper and publish of the host/build worker. Copy all Python files together, including screenshot_image.py, mask_geometry.py, and capture_guard.py:

```bash
source /Users/Shared/CIMT/environment.sh
cp runtime/*.py "$CIMT_INSTALL_ROOT/lib/cimt-runtime/"
cimt --help
```

No new dependency, YAML field, or screen-region configuration is needed. The adapter now requests lossless PNG bytes from the native helper. JPEG is rejected at the masking boundary. Mask geometry, capture-size checks, clean image export, and container UI text handling use the separate services described in [screenshot masking](screenshot-masking.md).

First-Mac verification: 343 offline checks passed. All installed Python files match source, the new modules import, and public help works. A connected Android phone was locked; its probe stopped before capture. The product owner requested skipping physical-device checks for now. No live masking pass is claimed, and Android/iOS acceptance remains open. Private configuration and retained reports were not changed.

## 22. Connected-device masking check — 29 October 2026

The product owner connected Android and iPhone, allowing the paused read-only checks to resume. Both devices were online and unlocked. Android passed the production capture/masking check with a 1080 × 2340 PNG. The iPhone initially failed to read UI because DeviceKit was absent. After installing the helper with a suitable existing signing profile, it passed with an 828 × 1792 PNG. Both checks verified black mask pixels, hidden UI text, and an RGB PNG with no image metadata. See the [masking evidence and limits](screenshot-masking.md).

Use these checks when preparing another Mac or connecting another phone:

1. Check available disk space before starting the adapter. This Mac initially returned `No space left on device`. Four cached CIMT installer archives were removed only after verifying their extracted tools were installed. Do not remove active tools, application repositories, signing material, or retained reports to make space. No fixed minimum free-space requirement is established by this observation.
2. Confirm Android is authorized for USB debugging and the iPhone is paired and connected. Keep both phones unlocked. Connection alone does not prove the helper is installed or the screen is ready.
3. Check the iPhone helper with the section 11 `agent status` command. On this connected phone, both the native helper status and Apple's installed-app query confirmed DeviceKit was absent. Do not infer installation from a previous phone's result.
4. If the helper is missing, follow sections 11 and 13. The development profile must be unexpired, include this phone, permit DeviceKit's bundle identifier, and include a certificate whose signing identity and private key are available on this Mac. A profile covering the phone alone is insufficient. Here, two profiles covered the phone, but only one also matched an available valid signing identity. Installation with that matching profile succeeded.
5. Verify capture through CIMT's production Mobile.snapshot path. Select a visible identified text element from the current UI and apply its element-ID masking rule. Check black pixels at the mapped mask, hidden returned UI text, image format, and metadata. Keep raw images and UI responses in memory and retain only aggregate outcomes for this read-only check. This is distinct from the older section 11 navigation probe, which saves private screen evidence.
6. Stop the probe's own MCP client and native daemon. Keep DeviceKit installed for later runs. Check that all installed runtime modules match the source used for verification.

First-Mac outcome: both physical-platform smoke checks passed sequentially; all 28 installed Python modules matched source. No product code, private YAML, application data, API key, or retained report was changed. No model call or MAUI application build was needed. The temporary aggregate results remain local under `/private/tmp/cimt-screenshot-masking-live-20261029`. Credential-entry, rotation, simultaneous device execution, real MAUI scenarios, Jenkins, and second-Mac acceptance remain open.

## 23. Inputs only; CIMT creates output — 29 October 2026

Installed CIMT runs independently of the launch directory and source checkout. The user supplies configuration, referenced test texts, and optional custom scripts. Do not create output folders and do not configure workspace.root or reports.root. CIMT creates the entire output tree automatically below the input folder.

The input folder is the folder containing --run-config, or --config when no run override is supplied. Shared default settings may live elsewhere. Input and custom-script paths still resolve relative to their declaring YAML file. A branch override does not change the selected input folder.

The first Mac's prepared inputs are in /Users/sumkar/Development/testing/FirstRun:

```text
FirstRun/
  default.private.yaml
  application.yaml
  inputs/
  build/                         # application-specific integration only
  CIMT output/                   # created by CIMT, not by the user
    work/work_<date-time>/        # temporary, when execution needs it
    reports/report_<date-time>/   # retained HTML, builds, logs, and evidence
```

The inputs retain the supplied Subgit repository, main branch, Release_Generic/Release_Pride targets, and Android/iOS settings. Build adapters call the installed default workers. They do not need the source checkout at execution time. Existing private settings remain owner-readable/writable only and were not read or changed during this correction. Legacy output-root values still load but are ignored with a terminal notice and a retained output-layout.json policy record. reports.sections remains supported.

Start from FirstRun:

```bash
cd /Users/sumkar/Development/testing/FirstRun
source /Users/Shared/CIMT/environment.sh
cimt validate --config ./default.private.yaml --run-config ./application.yaml
cimt run --config ./default.private.yaml --run-config ./application.yaml
```

From another launch directory, point to those same files:

```bash
source /Users/Shared/CIMT/environment.sh
cimt validate \
  --config /Users/sumkar/Development/testing/FirstRun/default.private.yaml \
  --run-config /Users/sumkar/Development/testing/FirstRun/application.yaml
```

Both invocations keep output under FirstRun/CIMT output. Each invocation allocates a fresh report identity; execution creates paired temporary work when needed. Old reports remain. Temporary work cleanup does not remove reports or input files. The machine-wide lock and ownership registry remain with the CIMT installation.

Missing or invalid YAML retains its error report with the selected input folder when writable. If output is blocked, unsafe, or unwritable, CIMT reports the failure in the terminal and does not create an output tree elsewhere. With invalid command syntax and no selected input, the launch folder is used. Existing links cannot redirect output outside its designated parent.

Install the corrected host from the source checkout:

```bash
source /Users/Shared/CIMT/environment.sh
dotnet publish src/Cimt/Cimt.csproj -c Release -o "$CIMT_INSTALL_ROOT/lib/cimt"
```

No new dependency, phone helper, API key, or runtime module is needed for this correction. The full offline checks plus the additional blocked-output unit case passed: 181 .NET tests, 155 Python tests, and 28 public-command/build/example checks, 364 total. The installed launcher also passed all five output-layout checks from two launch folders, including spaces, shared defaults elsewhere, retained earlier reports, legacy roots, and missing/invalid YAML. These use fake readiness tools and synthetic credentials; no API request, real build, or device action was performed.

FirstRun now contains inputs only. Its previously prepared empty work/reports folders were removed; its CIMT output folder will be created by the first actual invocation. See the [runnable output-layout demonstration](../examples/input-folder/README.md). Real application, model access, and Jenkins/second-Mac acceptance remain open.

## 24. Long native socket address — 29 October 2026

The user-started FirstRun report_2026-10-29_12-37-16-923 passed model/runtime preflight, then stopped at physical-device discovery with exit 3. No repository clone, application build, installation, or test action was reached. The report also recorded failure to stop the owned native helper. This is a CIMT integration defect, not evidence of invalid API credentials or a disconnected phone.

Diagnosis used the retained result.json, the generated work-folder name, and the installed helper's read-only daemon status command. The original address ended with work_<date-time>/mobilecli/daemon.sock and was 110 bytes long. Mobile CLI explicitly limits macOS addresses to 103 bytes; the installed binary rejected the calculated address with that same limit. A separate local socket check also rejected it. No device command or real CIMT rerun was needed to identify the path problem. See [upstream path validation](https://github.com/mobile-next/mobilecli/blob/main/daemon/paths.go).

The corrected host automatically creates a short owned link under /tmp/cimt-native-<installation-and-user-hash>, pointing to the run's mobilecli directory. MOBILECLI_HOME and the Python runtime use this address. The actual socket, PID, and log files stay inside FirstRun/CIMT output/work/work_<date-time>/mobilecli. The temporary link is internal coordination metadata. Users do not create it, change their input directory, or configure a new setting. Normal and next-start owned-work cleanup remove only a link with the expected target; unrelated files/links are preserved.

Discovery and helper-stop errors now retain redacted diagnostic details. Before temporary work is removed, available helper output is copied, with credential redaction, to reports/report_<date-time>/logs/native-daemon.log. Cleanup does not stop a global helper if this run never selected an owned helper address.

Install from the source checkout using the host publish command in section 23. No new dependency, key, Python runtime update, or phone helper installation is needed. Keep the existing private YAML and use the same public run command yourself.

Verification: 196 .NET tests, 155 Python tests, and 28 CLI/build/example checks passed, 379 total. The existing unit-test project binds a real local socket through the short link into a deeply nested folder. Small cases cover occupied links/files, target verification, missing targets, ownership, shared host/worker address, redacted diagnostics, log retention, and cleanup. A dangling-link regression initially failed; changing link removal to unlink the link itself corrected it, and the complete offline suite then passed. These checks use no real API, MAUI application build, or physical-device action.

The corrected host was installed and compared with the tested assembly. Existing run reports were preserved and private configuration was not read or changed. No actual CIMT run was started during diagnosis or installation. The next physical discovery/build/application result must come from the user's retry; it has not yet been verified.

## 25. Generic interactive run checkpoints

The user-started FirstRun report_2026-10-29_13-18-24-585 stopped at model/runtime preflight with a transport error. A separate no-key/no-inference HTTPS check resolved api.openai.com but failed certificate-chain verification: the macOS trust store reported -25318 (a required issuer certificate could not be found), and standard verified TLS reported unable to get local issuer certificate. No HTTP authentication response was received; this does not establish an invalid key. Keep certificate verification enabled. Different service-access needs on this Mac motivated optional operational pauses. The product owner subsequently required generic messages rather than environment-specific network instructions.

Update the installed host using the section 15 publish procedure. No new dependency, API key, phone helper, Python module, or build-worker update is required for interactive checkpoints. Add execution.interactive-pauses: true to the public per-run YAML; FirstRun/application.yaml and the tracked ECON example now include it. Keep private key configuration unchanged.

When the user starts run, CIMT describes OpenAI model access, repository access/builds, and AI testing after a successful build, waiting for Enter at each checkpoint. The messages do not prescribe any network or environment preparation. Complete any necessary preparation before acknowledging. The key is read from YAML at startup, but authenticated requests wait for acknowledgement. No installable builds means no third pause. Waiting counts toward the configured whole-run time limit. Deadline/closed-input failure still triggers owned cleanup and a retained local report. Omitted/false preserves unattended operation; Jenkins must use that value. Enabled pauses reject redirected input. validate is unchanged. The product guide contains the full [walkthrough](product-guide.md#interactive-pauses).

A separate application build blocker remains: report_2026-10-29_13-03-36-993 passed preflight, discovery, clone, and submodule initialization, but Release_Generic/Release_Pride on Android/iOS all failed in CuRMiTagger.exe under Mono. RuntimePolicyHelper calls RuntimeEnvironment.GetRuntimeInterfaceAsObject, which throws NotSupportedException there. The earlier macOS-adapter fixture established invocation only. Do not silently skip the required tagger or claim these builds succeeded. Network switching does not resolve that compatibility issue. No installable app or app interaction was produced by that run.

The previous network-specific increment passed 214 .NET unit tests, 18 existing CLI/lifecycle checks, one macOS build-adapter fixture, and five public output-layout checks (238 checks). Eighteen unit cases cover checkpoint behavior, input privacy, validation, and deadline handling. These are offline checks with synthetic input and fake external services. The host publish completed, its installed assembly matches the tested build, and public help succeeds. Private YAML and existing reports were preserved. No real FirstRun, authenticated OpenAI call, app build, or device action was started. Real interactive operation on this Mac and Jenkins remain acceptance work for the user-started run.

The generic correction replaces execution.network-switch-pauses with execution.interactive-pauses in code and public configuration. Internal classes and recorded stages now use execution-checkpoint names. Separate copied configurations must use the new field; the previous network-specific field is no longer accepted. FirstRun/application.yaml and the supplied examples have been migrated without reading or changing private YAML. Generic-correction verification: all 214 existing .NET unit tests and 18 CLI/lifecycle checks passed (232 checks), including assertions that every checkpoint message contains no network instructions. The host was republished, its installed assembly matches the tested build, and public help succeeds. No real FirstRun, authenticated OpenAI request, MAUI build, or device action was started. Actual interactive execution remains for the user.

## 26. User-started build follow-up — 29 October 2026

FirstRun report_2026-10-29_14-03-22-908 confirms the generic interactive checkpoints: both OpenAI preflight and repository/build phases recorded waiting and continued. Model-access preflight passed without inference, device discovery completed, and main commit b1c95ef314311f1fc3c8d090c5d64bdb727903bd and its recorded submodules were checked out. The targets were labelled Debug_Generic and Debug_Pride on Android/iOS, but effective-config.json specifies Release_Generic and Release_Pride as their actual configurations.

All four builds exited 1 in the required CuRMiTagger.exe pre-build tool, launched by FirstRun/build/prebuild.targets through Mono. RuntimePolicyHelper calls System.Runtime.InteropServices.RuntimeEnvironment.GetRuntimeInterfaceAsObject, which throws NotSupportedException. The labels did not select Debug configurations; both this run and the later branch run used Release configurations. Android also reports XA0033 while parsing the installed Java version; that warning is separate from the fatal tagger exception.

The run correctly retained exit 3, inconclusive verdict, and incomplete completion. No installable artifact or application interaction was produced. The third checkpoint was skipped because no build succeeded. Next: establish a Mac-compatible way to run the required tagging step before retrying the application build; do not silently skip it. Diagnosis read only retained report/log files and the public build adapter. No private configuration was read, source or build behavior changed, or run restarted.

## 27. Branch verification and obsolete local build override

The user-started report_2026-10-29_14-22-07-934 records branch testing/curmitAndNugets and commit 8b50dd12f65e0f3ffd9f8df68013d56601473f45. An independent temporary shallow clone of that named branch returned the same commit, with message Remove Curmit tagger from pre-build execution. Its application PreBuild target contains the Windows resource-copy command, with no tagger call. The inspection initialized no submodules, built nothing, and removed its temporary clone. The developer checkout was not changed.

The failing command came from FirstRun/build/prebuild.targets, injected by the earlier local adapter through CustomAfterMicrosoftCommonTargets. Thus the old CuRMiTagger call was reintroduced outside the selected project, despite correct checkout. The earlier diagnosis of a required tagger on this branch was incorrect. The Mono exception is real for the injected executable, but does not establish incompatibility of the selected branch's intended project-configured CuRMiT integration.

Correction: replace the separate input folder's build/build.sh with the updated example script and remove the obsolete build/macos.targets and build/prebuild.targets files. FirstRun has been updated. The adapter now changes only the exact known Windows resource-copy command in the temporary cloned project, then calls the installed default Android/iOS worker. It does not inject a tagger, Mono, global imports, or properties. Other project-configured tools and Visual Studio/MSBuild integration remain in place. No installed host, worker, dependency, private YAML, application branch, or user build configuration needs changing for this fix. The recorded targets retain the user's Release configuration values despite their Debug labels.

Verification: four example MSBuild fixture tests and four default-worker contract checks passed. They cover copying with no tagger, preservation of project-defined tools and configured properties, unrelated pre-build steps, unchanged requests, target conditions, and both platform delegates. Shell syntax and FirstRun/source script equality checks passed. These are synthetic checks, not real MAUI builds. The assistant did not rerun CIMT; signing, compilation, installation, and actual application testing remain for the user's next run. Reports and private configuration were preserved.

## 28. Retain work, preserve build properties, and replay built apps

The product owner replaced deletion after execution with retention until the next clone for the same inputs. Install updated host and build-worker assemblies using section 15's publish commands. No new dependency, API key, private YAML change, phone helper, or Python module is required. Retained ownership records migrate from the earlier single-object format without losing ownership proof. New records preserve work across different input folders.

Finalization keeps checkout/publish/intermediate files, stops the owned helper, saves/redacts its log, and releases a successfully stopped helper's short link. A failed stop leaves the verified link for next-run recovery. Before a later normal Git clone, only earlier verified work for those inputs is removed. Preflight failures, validation, and replay do not clear it. Reports/artifacts remain. Existing work already deleted by an older CIMT cannot be recovered by this change.

The default worker no longer injects AndroidPackageFormats, RuntimeIdentifier, BuildIpa, or ArchiveOnBuild. It preserves explicit YAML values and project/SDK defaults; no FirstRun properties were rewritten. Installable APK/IPA output remains necessary for device testing. Missing output is explained rather than followed by an implicit property change/rebuild.

A completed build stage with successful apps creates per-input retained-builds.json with original run/repository/branch/commit/profile, relative report artifacts, and digests. cimt replay --config ./default.private.yaml --run-config ./application.yaml reuses those apps with current text inputs and credentials, verifies paths/profile/integrity, and creates a new report. There is no Git/restore/build stage, no deletion of prior work, and no automatic rebuild on cache failure. Saved action-history replay remains explicitly unfinished. See the [workflow](work-retention-and-replay.md).

Verified: 237 .NET unit tests, 155 Python checks, 20 CLI/lifecycle checks, four build-contract checks, four example-adapter checks, and five public output-layout checks passed: 425 checks total. The complete suite passed before the final helper-stop recovery case; the updated .NET and CLI suites passed again after that change. The replay fixture disables Git/build commands and verifies identical app bytes and retained work. These checks use synthetic inputs and existing test projects; they do not establish a real MAUI build or device replay.

Installed both updated Release assemblies on this Mac and verified byte equality with their tested local build outputs. Installed cimt.dll SHA-256: 95ddeaf75e96bf06db53c353fd1b30485ed043460be5cbb29ac28d6596a9f97f. Installed cimt-build.dll SHA-256: 98f3e8d52793a477d5df76827d710419fedee107ee0b36c6ecbab62cc04dd141. Public cimt --help succeeded. No Python modules or dependencies changed. No private configuration was read, and the assistant started no real application run; the user controls the next run.

## 29. First retained-work run: missing generated application resource

The user-started report_2026-10-29_15-35-06-045 used testing/curmitAndNugets at 8b50dd12f65e0f3ffd9f8df68013d56601473f45. Model/runtime preflight, startup-device discovery, cloning, and submodule initialization completed. All four Android/iOS build attempts stopped at EconMobile.Common.csproj line 714 with MSB3030: Platforms/Android/Resources/values/template/strings.xml was missing. No installable app or device test was produced.

The work folder and all four build-job folders remain under FirstRun/CIMT output/work/work_2026-10-29_15-35-06-045, confirming retention after this failed real build. The cloned project differs from HEAD only in the disclosed Windows-copy-to-MSBuild-Copy replacement. No tagger call was injected. Later platform attempts find the already adapted copy task and leave it unchanged.

The selected revision tracks template/strings.template.xml, whose values include unresolved build/version placeholders. It ignores strings.xml, and CuRMiT-project.xml lists the missing template/strings.xml among FilesToPatch. The remaining project PreBuild copy expects that generated file on both Android and iOS. This establishes a missing generated input in the clean-clone build path; it does not establish which replacement generation process the application owner intends after removing the tagger invocation. Do not copy/rename the unresolved template, fabricate version metadata, skip the copy target, or reintroduce the old tagger automatically. Establish the intended application build preparation first, then express it in the application project or an explicitly agreed application-specific script.

Android also reports Java version-format warning XA0033, and iOS reports a Mono.Android reference warning; neither is the MSB3030 stopping error in this report. Other compilation/signing/package issues may appear after the missing generated input is resolved. The earlier adapter fixtures supplied strings.xml and therefore did not qualify clean-clone resource generation.

This investigation only read the retained clone and redacted report/logs. No private YAML was read, no source/project/script was changed, and no new application build, API request, or device action was started. Resource-generation resolution and successful build/device/replay acceptance remain pending.

Follow-up: the user-started report_2026-10-29_15-52-42-705 correctly picked up the new branch commit 3183659592c49aa0b2559da23ffa792f00cc5f52 (strings). The input configuration now explicitly selects Debug_Generic/Debug_Pride, matching the target labels. The new commit tracks Platforms/Android/Resources/values/strings.xml, which is the destination of the remaining PreBuild copy. Its expected source, values/template/strings.xml, remains absent. All four builds therefore still stop on MSB3030. Both the original Windows command and the portable replacement use the same source/destination; no path redirection was introduced. If the committed destination is now authoritative, remove the obsolete copy operation from the application project; if generation is still intended, provide the actual expected source through that build process. Do not reverse the copy or fabricate a generated file in generic CIMT. No application/project/script was edited during this investigation, and no new run was started.

Read-only follow-up checks found the newly committed destination resource to be valid XML with 12 entries and no unresolved $NAME$ placeholders. Other outputs named by the tagging configuration (Platforms/iOS/Info.plist, Platforms/Android/AndroidManifest.xml, and Version.properties) are also absent in this clone. Review their intended generation or committed-input policy before assuming a clean-clone build is ready. Their absence is an observation, not a separately reproduced build failure; the current build stops at the copy task first.

## 30. Detailed diagnostic reports and worker failures

The user-started run report_2026-10-29_15-58-46-808 produced all four Debug Android/iOS apps from 07a777740e956d9d6ebb648df3a22701bd6b383b. Its subsequent replay report_2026-10-29_16-34-22-941 reused those apps. Both stopped at Android screenshot-mask stability validation before any AI inference request; the iPhone worker was then cancelled by the shared stop policy. The exact worker error was in ui-results.json, while the former host summary ended with an empty exit-3 message. This was an observable diagnostic-reporting defect, not evidence of a confirmed app crash.

The update adds mandatory run overview, chronological activity, and failures/stopping reasons to new run/replay HTML reports. Host/device events append to activity.jsonl; result.json includes ordered activity, duration, and stopping reasons. Per-device errors now reach the host summary even when stderr is empty. Structured lifecycle messages stream to the terminal, and redacted worker output is retained under logs/execution-worker.log. The screenshot guard now describes changed regions/counts/coordinates without UI values. Its rejection and the existing shared stop policy are preserved.

Install the updated host using section 15's publish command. Copy the updated runtime modules as well:

```bash
cp runtime/*.py /Users/Shared/CIMT/lib/cimt-runtime/
```

This increment adds only standard-library Python code, with no new dependency, private configuration field, API key, helper, or build-worker change. Fresh-Mac installation still uses the documented runtime installation helper, which copies these modules. Existing inputs and cimt run/cimt replay invocations remain valid; no verbosity flag is needed. Existing reports are not rewritten, and their missing historical timestamps cannot be reconstructed.

Verified on the first Mac: 246 .NET unit tests, 13 runtime-policy checks, 150 Python unit tests, 20 public CLI/lifecycle checks, four build-contract checks, four example-adapter checks, and five output-layout checks passed: 442 checks total. All use synthetic inputs/fake services. The existing offline requirement demo generated a synthetic failed/incomplete report with the new sections/activity; its expected exit is 1. Static HTML structure, section, and result checks passed. Visual browser inspection was unavailable because the browser tool blocks local-file URLs; no workaround was attempted.

Installed the tested Release host and all 29 Python modules, checked byte equality against source/build output, and verified public help. Installed cimt.dll SHA-256: c416f3cc25f07192775b7342e58f3ff5b5bb31f1bcc7452e0a12b98663622bb9. No private YAML was read, no new real app build/run/replay or OpenAI request was issued, and no phone was operated. Real application acceptance of the improved diagnostics remains for a user-started run. The underlying capture-stability issue is still open. See [diagnostic reporting](diagnostic-reporting.md).

## 31. Remaining work after an interrupted scenario

The 30 October replay exposed a reporting defect: the AI returned pending tasks, but the final scenario list stayed empty after iPhone relaunch failed. ScenarioRunner now saves each returned plan before check recording and limit handling, and finalizes pending work after preparation/execution errors. It includes known unresolved requirement/control counts and an unfinished-objective fallback. Completed scenarios clear earlier plans. No device-control or launch policy changed.

For an existing installation, stop active CIMT runs, then copy runtime/scenario.py to the installed lib/cimt-runtime/scenario.py. The normal fresh-Mac runtime installation helper already copies this file. No host rebuild, dependency, configuration change, or API key setup is needed for this fix.

Verified: 247 .NET unit tests, 158 Python unit tests, 13 runtime-policy checks, and 20 public CLI/lifecycle checks passed (438 checks). The regression tests use fake relaunch/capture failures and check the saved pending list, latest-plan replacement, completion, coverage counts, redaction, and HTML stopping/scenario sections. The initial sandboxed .NET attempt could not open its process pipe; verification succeeded with the required local process permissions.

Installed only scenario.py and checked byte equality against source. Installed SHA-256: 3ae9b06e184ff4610abe679082ad22c61fd321986c039616e447b88e1ca3c2ea. No private YAML or historical report was read or changed, no real run/replay or API request was started, and no phone was operated. New run/replay reports use the correction; the iPhone launch problem remains open.

## 32. Build wrappers no longer rewrite the application project

The product owner requested removal of the Windows resource-copy workaround. The example, FirstRun, and TestRun_SingleDevice_SingleTarget build/build.sh files now only delegate to the installed default platform build script. The selected project/configuration owns resource copying and all other build steps. This supersedes the older adapter descriptions in this guide. No installed host/runtime or private configuration update is needed.

For another existing input folder, replace its copied build/build.sh with examples/econ-button-crash/build/build.sh. Keep its configured platform entry scripts. The wrappers no longer read the build request or write application project files. An original unsupported build step must be fixed in the application project or an explicitly user-supplied build script.

This changes future normal builds. Replay still uses retained apps and will not rebuild them. Existing retained work, apps, reports, private configuration, and the application repository were not changed. No real app build, API request, or device test was started for this correction.

Verification for section 32: all four existing example-build checks passed, including visible failure of the unchanged Windows command. Shell syntax checks passed, and the source wrapper matches both local copies byte-for-byte. These fixture checks do not establish real app build or startup success.

## 33. Permission-dialog screenshot transitions

The user-started report_2026-10-30_12-36-25-944 reached the ECON login screen. The first UI read found password controls; the second read found the OS Bluetooth permission alert. The capture guard rejected the unstable image, stopping execution before any AI request or saved step screenshot. This was an infrastructure/evidence stop, with no confirmed app crash. The report could not display an image that had not passed masking verification.

Update the host and runtime together for bounded fresh-frame capture retries and explicit HTML missing-evidence text. Use the existing host publish procedure and copy runtime/errors.py, runtime/capture_guard.py, runtime/screen_capture.py, runtime/mobile.py, and runtime/action_prompt.py to lib/cimt-runtime in the installation. Fresh-Mac setup already copies these modules. No new dependency, YAML setting, API key, build script, helper, or application change is required.

Each capture gets at most three fresh attempts after valid geometry changes, with 250 ms waits counted toward the run deadline. Rejected images remain in memory and are discarded, while invalid data/device/tool errors still stop immediately. Accepted screenshots appear in new HTML reports; historical screenshots cannot be recovered. This correction is verified offline; the next user-started run/replay must confirm physical-device permission handling.

Verification for section 33: 249 .NET unit tests, 167 Python unit tests, 13 runtime-policy checks, and 20 public CLI/lifecycle checks passed (449 checks). Six new capture cases, two HTML cases, two permission-prompt contract cases, and one blocked-permission outcome case cover this correction. No live model/device acceptance is claimed from these fixtures.

Installed the published host and all five changed runtime modules after checking that no run was active; byte comparisons and installed public help passed. Installed cimt.dll SHA-256: 3ba63065404c21431d7d755c48bca01bd072bf1b8f29145fd2f78ce36e74e0d8. The local TestRun_SingleDevice_SingleTarget instruction file alone authorizes Allow/equivalent permission choices for ECON-M; no global automatic approval action was added. Private YAML and historical reports are unchanged, and no real run/replay, paid request, or phone action was started.

## 34. AI response correction update — 30 October 2026

Install the updated host and Python modules together so the HTML report understands rejectedResponses. The source installation procedure in section 14 still applies; there is no new package, API credential, YAML field, or device helper. This update adds runtime/decision_recovery.py and changes action_prompt.py, agent.py, check_results.py, requirement_results.py, errors.py, scenario.py, and record_redaction.py. Publish the host to a staging folder, run the existing offline checks, then copy the published host and runtime modules to the installed CIMT paths. Keep a backup of replaced installed files until verification passes.

The behavior is automatic for run and replay: at most three AI responses per decision, fresh masked evidence before corrections, shared budget/deadline enforcement, and mandatory unaccepted-response diagnostics. The command-line help check and byte comparison can verify installation without starting a real app test. Live API schema acceptance and physical-device execution remain separate acceptance checks and are not implied by offline verification.

Verification for this increment: 467 relevant offline checks passed (250 .NET unit tests, 184 Python unit tests, 13 runtime-policy checks, and 20 public CLI/lifecycle checks). The final host was published successfully. The installed host and eight changed/new runtime modules match the tested files byte-for-byte, and installed public help passed. Installed cimt.dll SHA-256: df3f2d9d51693a5011b74954531d3d183eb7d7fe8fd8af3bfb5888d778ee0bc2. Backup: /private/tmp/cimt-before-decision-correction.e8hvj7ht. No real app run/replay, paid API request, or phone action was started.

## 35. Exploration memory, interruption, and interim reports — 30 October 2026

Update the host and Python runtime together using the existing source installation procedure. New modules are exploration_memory.py and run_signals.py; changes also affect action_prompt.py, agent.py, actions.py, coverage_tracker.py, decision_recovery.py, device_runner.py, errors.py, run_control.py, run_ui.py, and scenario.py. There is no new package, helper, private input, API key, or YAML option. Keep a backup before replacing installed files and compare copied bytes afterward.

The update adds whole-scenario exploration memory and bounded no-progress replanning. Terminal interruption requests controlled finalization, and the UI worker has a five-second exit grace before process-tree termination. Partial reports use the existing output folder and are refreshed about every two seconds during device testing, with atomic replacement and an explicit partial marker. Stage-boundary snapshots also cover preparation/build progress. Actual signals and forced termination are verified using temporary fake-runtime processes in the existing CLI checks, without contacting OpenAI or operating physical devices. Physical-device/API acceptance remains a user-started run/replay.

Verification for this increment: 503 relevant offline checks passed (261 .NET unit tests, 207 Python unit tests, 13 runtime-policy checks, and 22 public CLI/lifecycle checks). These include actual SIGINT delivery to a temporary fake-runtime CIMT child, forced termination of a separate child after an interim report was saved, checkpoint cancellation, and a closed-pipe interruption race. The final host published successfully; installed host and all 12 changed/new runtime modules match the tested files byte-for-byte, and installed public help passed. Installed cimt.dll SHA-256: 97d66b943637304fef2bfef6f3a5fbf49ae7579480a8fa4318cec33ea44cf990. Original installation backup: /private/tmp/cimt-before-exploration-stop.7pl43htt. No real app run/replay, paid API request, device action, private configuration edit, or historical-report rewrite was performed for this increment.

## 36. Compact AI history input — 30 October 2026

This runtime-only update replaces lib/cimt-runtime/action_prompt.py with the tested source version. No host rebuild, package, helper, private configuration, model selection, or API key change is required. Use the existing runtime source installation procedure, or back up and copy that one module after verifying that no CIMT run is active. Compare its installed bytes with runtime/action_prompt.py afterward.

The update preserves 24 recent navigation facts plus critical findings while avoiding duplicated full checks and old plans in AI input. Full saved history and reports remain available. Five new tests exercise projection content, immutability, bounded history, critical findings, aliases/coordinates, and prompt guidance in the existing unittest suite. Live latency improvement is not established by these offline checks; compare a later user-started run against the timing baseline in performance.md.

Installation verification: the installed action_prompt.py matches the tested source byte-for-byte (SHA-256 c0e27c0ae6eceeb55166ae064ac2d353e427ab203935574bb16aaf725fcc35ee). The previous module is backed up at /private/tmp/cimt-before-compact-history.pzjfq7_7/action_prompt.py. No run was active during replacement. The host is unchanged; no real test run or API request was started.

## 37. Configured model and Luna pricing support — 30 October 2026

Update lib/cimt-runtime/budget.py, agent.py, and run_ui.py together after confirming that no CIMT run is active. Back up replaced files and compare installed bytes afterward. No host rebuild, package, helper, API key, administrator key, or YAML schema change is required. The configured supported model is checked before builds and used for inference. No private configuration is changed automatically.

To select Luna, set ai-model.name to gpt-5.6-luna in the existing local configuration; keep its key and USD spending limit. The existing Mini snapshot remains supported. Unknown models/currencies stop before inference. Luna accounts for default cache-write charges and the long-context tier, reserving USD 0.5286864 per request. See the [model selection procedure](product-guide.md#select-the-ai-model) and architecture section 27. Automatic price retrieval and provider cost queries are deferred. Real account/model access and physical-device comparison remain user-started acceptance checks.

Verification for Luna support: 217 Python unit tests, 22 runtime-policy checks, and 22 existing public CLI/lifecycle checks passed (261 relevant offline checks). Fourteen new cases cover model selection and the additional pricing rules. The CLI fixtures use temporary simulated runtimes, without API or physical-device access. The installed budget.py, agent.py, and run_ui.py match the tested source byte-for-byte after checking /Users/Shared/CIMT/state/run.lock for active holders. Backup: /private/tmp/cimt-before-luna.dvwn2h8p. Installed SHA-256 values: budget.py 3505d8e685c158ad3fdc90dc7840fbd622b48ca85c3628ac30de2bf04f6b8b9f; agent.py d22efb9203517d9e80bf1e65f7e8ab75e9089fad2eeaa15b3cdc58dd01763760; run_ui.py 8cd657cf79544aecf4289e3ffff2a43afa79f43134757065d5dc740d498d3655. Host and private configuration are unchanged. No real app test, paid API request, or phone action was started.

## 38. Per-execution report correction — 30 October 2026

The product owner reaffirmed the existing contract: every run and replay has its own report_<timestamp>/index.html. Remove the briefly added shared-latest publisher and install the corrected .NET command host using the existing publish/backup procedure. Confirm no CIMT command holds the run lock before replacing the host and compare installed bytes afterward. Python runtime, build worker/scripts, credentials and YAML do not change.

Remove only the generated reports/index.html entry introduced by the previous update from the existing FirstRun, TestRun_SingleDevice_SingleTarget and TestRun_ios_android_SingleTarget inputs. Keep every report_<timestamp> folder and its HTML, JSON, logs and screenshots unchanged. User README instructions must point to the timestamped Report path printed by the execution rather than a shared latest page.

Both full runs and replays continue to allocate distinct dated folders. This correction adds clearer command/identity labels and regression coverage for isolated replay output, without starting a real application test or changing previously saved results.

Verification for the corrected per-execution contract: 266 xUnit cases and 22 existing public CLI/lifecycle checks passed (288 relevant offline checks). The replay fixture verifies its own dated HTML command/identity and absence of a shared entry or HTML base. The corrected host published successfully; all six installed files match the tested publication, and installed public help passed. Installed cimt.dll SHA-256: 15c5fb853c15f7a81a556b92a76bab910d3a24e88cbc3c5e449f2725a68ba924. Backup: /private/tmp/cimt-per-run-install.UbVTdZ/previous-host.

Removed only the three shared reports/index.html files introduced by the previous update, from FirstRun, TestRun_SingleDevice_SingleTarget and TestRun_ios_android_SingleTarget. Verified timestamped report HTML hashes were unchanged. Python runtime, build worker/scripts, private settings, application source, and saved results remain unchanged. No real run/replay, model request or device action was started.

## 39. Approved report usability update — 30 October 2026

Publish the host with the existing section 15 procedure and replace runtime/decision_recovery.py with the matching source version. The host embeds its report stylesheet and script; no browser server, package, key, YAML field, application change or device helper is added. Preserve private configuration and existing timestamped reports. Later user-started runs/replays produce the new five-section layout; opening an old report does not regenerate it.

The worker update supplies current device/target scope to prevent remaining plans from describing other workers. It makes no extra model call and does not change budget, action, permission or crash recovery policy. Back up host/runtime files and hold the installation run lock while replacing them.

Verification: 286 xUnit tests, 218 Python unit tests, 22 runtime-policy checks and 22 existing public CLI/lifecycle checks passed (548 relevant offline checks). The public fixtures include replay isolation, failed builds, controlled interruption and forced-stop partial reporting, using simulated dependencies. The report script passed syntax checking. The extended offline requirement-mapping demo produced Android/iOS results and four valid opaque synthetic PNGs, with all anchors/evidence/download links checked after folder relocation. Fourteen specified text/background color pairs met 4.5:1 in static calculations. These are not completed browser, screen-reader, 200% enlargement or user-timing acceptance tests.

Installed the final six-file host publication and scoped worker module under the Mac-wide lock; all installed bytes match the tested publication/source. Public installed help passed. Host SHA-256: f5b369d6f49fdb5d1dac1b8735d3b63370dbfac5c287543275ca579e9ec8bc45. Original backup: /private/tmp/cimt-report-design.BoxIlJ/previous-host and previous-runtime. Build worker/scripts, model/pricing modules, private YAML, application source and historical test reports were preserved. No real application run/replay, paid API request or physical-device action was started.

## 40. Virtual-device execution

The product owner approved Android Emulator and iOS Simulator execution on 31 October 2026. See [the configuration, device abstraction, build differences and Mac preparation](virtual-devices.md). Physical devices remain the default. Use explicit compatible build properties; do not change tested application source. Offline validation and real-run qualification are separate.

### Findings from 31 October 2026

- Installed the Android emulator and API 36 Google APIs x86_64 image with the existing SDK Manager. Its command completed successfully. The manager emitted its deprecation warning and `avdmanager` emitted a missing `devices.xml` warning; the named AVD was created and booted successfully despite that warning.
- Created dedicated `CIMT_Android_API36` and `CIMT_iPhone` devices. The iPhone uses the already installed iOS 18.5 runtime. Left the existing online iPad simulator unchanged.
- Verified Android boot completion and unlocked state, iOS Simulator UDID/readiness and live launchctl process format. Installed the standard DeviceKit helper, version 0.0.35, on the dedicated iPhone Simulator. No third-party tool source changes were made.
- Installed CIMT's host, build worker and five affected runtime modules, preserving a backup at `/private/tmp/cimt-virtual-backup`. Verified installed file bytes. Host SHA256: `b56b0ee062c42a15d94245efba8a97e08a0077f35d9ef2f29faf777e89328f84`.
- Offline validation passed: 295 .NET unit tests, 226 Python unit tests, 22 runtime-policy checks and 22 public CLI checks. The copied private YAML, input texts and build wrappers are byte-identical to the previous run. Real application build and exploration are separate qualification steps.
- The first real run command was rejected before process startup by automatic approval review, which requested explicit approval to send masked private-app screenshots and UI text to OpenAI. The product owner subsequently requested running again. The rejected command itself performed no app testing or paid inference.
- A separate configuration-validation attempt in the restricted shell could not acquire installation-state access and returned `UnauthorizedAccessException`; its report is not evidence of an emulator or application defect. Normal CIMT execution requires access to its installed state directory.

### Simulator capture tolerance correction

The subsequent approved run built and installed both apps, but stopped before AI inference on an iOS one-pixel capture mismatch. The product owner requested a tolerance correction, push, installation and replay. See [real-run qualification](virtual-devices.md#real-run-qualification-findings--31-october-2026) and [the capture correction](screenshot-masking.md#generic-mapping-tolerance-correction--31-october-2026). The final generic ±5% correction changes one Python runtime module; the host and build worker do not require rebuilding. Unit verification passed: 234 Python tests plus 22 runtime-policy checks. Keep the existing private configuration, model, budget, virtual-device IDs and retained artifacts for replay. Installation and replay results are recorded after execution.

The generic tolerance module was pushed in commit `23bef7c331ff112508803eddb5fc17861142a656`, installed under the machine lock and verified byte-for-byte. Installed module SHA256: `bac94c809f322795e11ee6ec8f4959f20bc40b634e459c6a7e38bbc5ffd6258a`. Original module backup: `/private/tmp/cimt-tolerance-install-backup/mask_geometry.py`. Host/build assemblies were unchanged by this Python-only correction. Both virtual devices were ready before the requested public-command replay, which reused the retained builds and skipped Git/build. Screenshot validation passed on both platforms. See the [separate simulator signing limitation](virtual-devices.md#signing-limitation-found-during-replay); a successful capture does not establish a successful app startup or completed test.

The requested replay was subsequently cancelled by the product owner and finalized correctly with HTML, JSON, both device summaries and 48 PNGs. Screenshot tolerance passed on both platforms. The retained unsigned iOS app was rejected at startup; Android continued until cancellation without a recorded crash. The report preserves incomplete coverage and existing failure precedence. See [the replay outcome and remaining reporting/exploration limits](virtual-devices.md#replay-completion-and-reporting-limits). No signing repair, new build or further replay was performed as part of this cancelled run.
