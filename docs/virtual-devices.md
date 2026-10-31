# Physical and virtual execution devices

Date: 31 October 2026
Authority: product-owner request to run the previous test on Android Emulator and iOS Simulator.

## Configuration

The normal `cimt run` and `cimt replay` commands support both device environments. The default remains `physical`. Virtual devices must be created and booted before starting a run. CIMT records the online selection once at startup; it does not boot, shut down or erase other devices.

```yaml
execution:
  device-kind: virtual
  device-ids:
    - CIMT_Android_API36
    - YOUR_IOS_SIMULATOR_UDID
```

`device-ids` is optional. Without it, CIMT uses all supported online devices of the selected kind. With it, every listed ID must be online and match that kind; CIMT stops instead of substituting another device. IDs are mobile-mcp identifiers: an Android AVD name or the iOS Simulator UDID. Select `physical` or omit `device-kind` to use connected phones. Mixing physical and virtual devices in one run is not supported in this increment.

Use the same build target, instructions, requirements, credentials, model and budget. Set explicit properties appropriate to the execution architecture. For an Intel Mac:

```yaml
# Add under the existing target's ios.properties:
RuntimeIdentifier: iossimulator-x64
BuildIpa: false
ArchiveOnBuild: false
# Add under the existing target's android.properties:
RuntimeIdentifier: android-x64
```

Keep the project/SDK signing policy. Simulator apps still need a signature accepted by the selected runtime; do not generically disable code signing. These are explicit example settings, not hidden CIMT defaults. Android projects can omit the RID if their existing APK already supports the emulator ABI. Native libraries must include compatible simulator/emulator binaries. An iPhone IPA cannot be reused on iOS Simulator. CIMT does not edit the tested repository or replace its MSBuild targets.

## Architecture

`DeviceInventory` shares native discovery between validation and execution. `DeviceSelection` handles the environment and optional IDs at the host boundary. The startup descriptor preserves the native `type` (`real`, `emulator` or `simulator`), platform, ID and name. Discovery uses the existing mobile-mcp adapter. Scheduling, the two-device concurrency limit, test scenarios, AI decisions, reset hooks, masking and budget enforcement keep the same workflow.

`DeviceTarget` handles only differences needed by native platform queries. It maps an Android AVD name to its online ADB serial. iOS Simulator readiness uses `simctl`; its running-process query requires a live PID for the exact bundle identifier. Physical iPhones retain their existing `devicectl` lock and process checks. UI actions, installation and screenshot capture continue through mobile-mcp/mobilecli. Third-party tool source is unchanged.

An explicit `iossimulator-*` RID selects `dotnet build` rather than phone-oriented `dotnet publish`. The default worker requires one top-level `.app` bundle and retains it as a ZIP with the bundle at its root, the adapter's simulator install format. The bundle identifier and executable are checked from `Info.plist`, as for an IPA. Android retains its APK workflow. Replay retains the physical/virtual environment and refuses reuse across those environments; it never rebuilds automatically.

The HTML overview records the selected device environment. Startup JSON preserves each native type. A virtual-device result does not establish physical hardware, Bluetooth, camera or equipment compatibility. Unavailable hardware and missing native-library slices must be reported as test limitations or infrastructure/build failures, not invented app crashes.

## Intel Mac preparation

Use the installed CIMT environment, then install the Android emulator and an Intel system image:

```bash
source /Users/Shared/CIMT/environment.sh
sdkmanager --sdk_root="$ANDROID_HOME" 'emulator' 'system-images;android-36;google_apis;x86_64'
printf 'no\n' | avdmanager create avd --name CIMT_Android_API36 --package 'system-images;android-36;google_apis;x86_64' --device pixel_7
"$ANDROID_HOME/emulator/emulator" -avd CIMT_Android_API36 -no-window -no-audio -no-boot-anim -no-snapshot-save -gpu swiftshader_indirect
```

Run the last command in a separate terminal. Verify `adb devices` shows `device`, then check `adb -s emulator-5554 shell getprop sys.boot_completed` returns `1`. The serial may differ if another emulator uses that port. Review any requested SDK licenses yourself. The installed SDK Manager emits a deprecation notice; this document records the working installed tool, not a claim about future package versions.

Install Xcode and a compatible iOS Simulator runtime. List available runtimes and create a dedicated simulator (this Mac already had iOS 18.5):

```bash
xcrun simctl list runtimes
xcrun simctl create CIMT_iPhone com.apple.CoreSimulator.SimDeviceType.iPhone-16 com.apple.CoreSimulator.SimRuntime.iOS-18-5
xcrun simctl boot YOUR_IOS_SIMULATOR_UDID
xcrun simctl bootstatus YOUR_IOS_SIMULATOR_UDID -b
```

Use mobilecli's standard `agent install --device YOUR_IOS_SIMULATOR_UDID` if its helper is missing. Do not install a phone provisioning profile for a simulator. Keep the run's normal API/network checkpoints, private YAML permissions and budget. Allow space for system images, device data, build output and host swap; this Mac dropped from about 18 GB to about 5 GB free during preparation.

## Example and test status

The local example is `Testing/TestRun_ios_android_Emulator`, copied from `TestRun_ios_android_SingleTarget`. It preserves Debug_Pride, `testing/curmitAndNugets`, input text, model and the USD 2 budget. The execution environment, selected virtual IDs and explicit compatible build properties are the changes. Private configuration and generated outputs are not committed to CIMT.

Offline checks cover default physical selection, virtual filtering, missing devices, descriptor types, simulator build/ZIP output, replay environment rejection, ADB name resolution, simulator readiness and exact process matching. Real build and UI test results are recorded separately in the run report and installation findings.

References: [mobile-mcp](https://github.com/mobile-next/mobile-mcp), [MAUI iOS command-line build](https://learn.microsoft.com/en-us/dotnet/maui/ios/cli), [runtime identifiers](https://learn.microsoft.com/en-us/dotnet/core/rid-catalog).

## Real-run qualification findings — 31 October 2026

The first run built both configured apps successfully (Android about 6 minutes 23 seconds, iOS about 1 minute 42 seconds), retained a native x86_64 APK and an executable x86_64 iPhoneSimulator app ZIP, then installed both and issued launch commands. iOS capture failed before AI inference: helper PNG width 1178 versus the 1179 pixels implied by 393 points at scale 3; height 2556 matched. Android's first masked capture passed, then the existing whole-run blocking policy stopped it. The result was incomplete/inconclusive, exit 3, with zero AI inference requests. This did not establish an app crash.

The approved generic tolerance correction accepts a horizontal/vertical scale ratio of 0.95–1.05 and expands secret masks for accepted mapping uncertainty; see [screenshot masking](screenshot-masking.md). Replay uses these retained virtual apps without Git or compilation. Its outcome must be recorded separately from this failed initial run.

On this 16 GB Intel Mac, stopping only the dedicated CIMT virtual devices during compilation reduced memory/swap pressure; they were restarted and verified ready before continuing the AI-testing checkpoint. Existing unrelated simulators were left running. This was an operator preparation step, not automatic CIMT device lifecycle behavior.

### Signing limitation found during replay

The retained test profile used `EnableCodeSigning: false`. After the tolerance correction, iOS screenshots passed, but the app was terminated at startup three times. Read-only host crash metadata reported `SIGKILL (Code Signature Invalid)`, namespace `CODESIGNING`, indicator `Invalid Page`. The built bundle failed `codesign --verify --deep --strict` with “code object is not signed at all”; the executable in its retained ZIP matched the original build byte-for-byte. The generic example above therefore no longer recommends disabling signing. The local retained test configuration/artifacts were left unchanged for this requested replay. Repairing that build requires a separate signing-policy correction and a new build, not silent modification of a retained replay artifact.

### Replay completion and reporting limits

The product owner cancelled replay `2026-10-31_06-48-22-356` with one Ctrl+C. CIMT finalized HTML/JSON with exit 1, verdict failed, completion incomplete: earlier iOS startup failures retained precedence while Android recorded user interruption. Both device summaries and 48 PNG files were present; static inspection found no duplicate HTML IDs or missing/escaping local evidence links. No browser accessibility conformance is claimed.

Android retained 44 records (30 taps, one swipe, one text action plus preparation/check records), with no recorded Android crash. Its ledger recorded 33 AI requests and USD 0.09831945 accounted upper cost against USD 2.00. iOS retained four screenshot records and three suspected startup terminations; read-only host diagnostics identified the separate signing rejection described above.

The action history also exposed remaining CIMT issues: OS status-bar clock/signal changes were counted as app UI changes; generic WebView views were missing from normal control classification; repeated actions were therefore not stopped promptly. Whole-screen state keys inflated outstanding control/state entries and repeated labels. Cancellation closed the adapter pipe while a capture was active, producing failed activity rows before the final user-interruption classification. These findings are not fixes included in the tolerance correction. Android screenshot validation averaged about 15.1 seconds and AI action requests about 3.85 seconds, so device-side evidence work dominated much of the delay.

## Follow-up scope after the cancelled replay

The product owner cancelled item 1 (additional startup diagnostics). No new diagnostic collector or evaluation is included. Item 4 corrects user-interruption activity/step classification and publishes partial observations even when adapter closure fails. Earlier failures retain precedence and genuine non-interrupted adapter errors remain failures. Item 3 (coverage counting) is unchanged. Items 2 (repeated actions) and 5 (capture speed) are reviewed proposals only; see the [focused follow-up review](reviews/2026-10-31-cancelled-replay-follow-up.md). No further mobile test was started for this correction.
