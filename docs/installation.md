# CIMT installation and setup guide

Version: 0.4  
Last updated: 28 October 2026  
Status: prerequisites, CLI foundation, and default build workers installed on the first Intel Mac; full execution and acceptance pending  
Scope: supported Intel Macs for local command-line and Jenkins execution

## 1. Purpose and current status

This document describes how to prepare another supported Mac, install CIMT, configure an application, and prove that local testing works. Findings from the first Mac are used to improve the repeatable procedure; its particular paths, installed versions, and hardware are examples, not mandatory product defaults.

The CLI/configuration foundation and default Android/iOS build workers are implemented. cimt validate produces readiness reports; setup/run/replay execution remains unimplemented and returns an explicit error. Prerequisite bootstrap scripts ran successfully on the first Intel Mac. Section 8 records installed tools; section 10 records the three reviewed increments and source installation commands. The prerequisite helpers remain separate from the future YAML-driven setup engine.

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

Work and report folders share a timestamp. Reports must remain outside the temporary cleanup folder. Exact timezone/collision handling remains to be implemented.

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

Both candidates and Node/npm are installed. Android control probes passed for both candidates. Following Xcode account recovery, Appium iPhone signing and 11 UI/screenshot/navigation checks passed. Mobile MCP's DeviceKit helper is installed; its application-control probe is blocked by the locked phone. Final selection requires the complete gate in the [adapter evaluation](adapter-evaluation.md); reset, masking, and unattended app testing remain unverified.

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

1. Both physical devices were available. Mobile MCP and Appium passed Android control probes. Initial iPhone signing failed; after the Xcode account recovery in sections 11–12, Appium helper signing and 11 iPhone control checks passed. Mobile MCP's separate DeviceKit helper was subsequently installed with a matching wildcard profile (section 13); application control still awaits an unlocked phone. Final adapter selection remains open; its earlier Mobile MCP preference was provisional.
2. The .NET CLI/configuration foundation is built and installed at /Users/Shared/CIMT/bin/cimt, with assemblies under lib/cimt. Source environment.sh to put it on PATH. Fifteen checks passed, and real readiness validation reached Subgit and both connected-device inventories. Only synthetic credential presence was tested; no AI request was made.
3. Default Android/iOS scripts are installed under scripts/build, with worker assemblies under lib/cimt-build. Four simulated build-contract checks passed. Actual builds on main with submodules were attempted: Android stops at the repository's Windows-only pre-build commands, and iOS lacks an available provisioning profile. No successful artifact was produced.

The original application checkout remains untouched. Raw device evidence and build logs remain local; no screenshots, device IDs, signing identities, or credentials are committed. Temporary application clones are deleted after evaluation; retained evidence is outside them.

The CLI recognizes all four approved command names, but only validate is implemented. setup/run/replay return explicit errors; the final setup engine, autonomous testing engine, per-step app reports, and complete cleanup/scheduling orchestration remain to be built. These partial capabilities supersede earlier historical statements that no CLI/build workers exist.

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

This completes basic Appium iPhone control on this Mac. Mobile MCP uses a separate helper/profile, subsequently installed in section 13; its iPhone application workflow remains unverified while the phone is locked. Input entry, real MAUI install/reset/login/crash flows, simultaneous two-device testing, Jenkins operation, and final adapter acceptance remain open.


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
