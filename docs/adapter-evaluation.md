# Physical-device adapter evaluation

Date: 28 October 2026  
Status: Android checks completed; final cross-platform selection blocked

## Decision

Mobile MCP is the preferred candidate for initial integration behind CIMT's interchangeable adapter boundary. **Final adapter selection is not approved by this evaluation:** the agreed gate requires a working physical Android/iPhone workflow, including a real MAUI application, reset, and unattended operation.

Both candidates have demonstrated Android control. Neither has demonstrated iPhone UI control with this Mac's present signing setup. The approved gate is preserved.

## Environment and method

Intel Mac, Xcode 26.5, Mobile MCP 1.0.14/native helper 1.0.21, Appium 3.9.0, UiAutomator2 8.7.2, XCUITest 12.22.1. Both physical devices were available: a Samsung Android phone and an iPhone running iOS 27.0.1.

Probes ran under the normal user account without sudo. They opened Settings, read accessibility/UI information, captured local screenshots, and exercised navigation. No passwords were entered, application data reset, or production application replaced.

Evidence and raw diagnostics remain under the private /Users/Shared/CIMT/evaluation/adapter-2026-10-28 folder; screenshots, device identifiers, profile details, and raw UI text were not committed.

## Observed results

| Check | Mobile MCP | Appium |
| --- | --- | --- |
| Physical Android discovery | Passed. | Device selectable by identifier. |
| Android Settings launch/session | Tool returned success. | Physical session created successfully. |
| Android UI inspection | Returned elements with refs, identifiers, and bounds. | Returned page source. |
| Android screenshot | Captured locally. | Captured locally. |
| Android navigation | Swipe and Home commands returned success. | Back command and session cleanup succeeded. |
| iPhone discovery | Passed. | Device selected for session attempt. |
| iPhone control | Blocked: DeviceKit agent not installed and requires a signing profile. | Blocked: WebDriverAgent provisioning failed; xcodebuild exited 65. |
| Successful simultaneous Android+iOS control | Not demonstrated. | Not demonstrated. |
| MAUI install/reset/login/crash workflow | Not demonstrated. | Not demonstrated. |
| Jenkins account operation | Not demonstrated. | Not demonstrated. |

A returned command is not proof of every expected visual transition. These are control smoke checks, not app requirement test results.

## Android ownership finding

Appium's first Android session failed with UiAutomation not connected while Mobile MCP's daemon still owned automation state. After stopping the native daemon, Appium created its session and completed UI/screenshot/navigation checks.

CIMT must give one adapter exclusive ownership of each device and clean up its sessions/helpers. The maximum two-device policy means two different devices, not two competing adapters on one phone.

## iPhone signing findings

The Keychain reports one valid signing identity, with no valid development identity. Existing profiles include device matches, but the matching wildcard development profiles are expired. Profile-file presence does not establish a usable certificate/private-key/profile combination.

Mobile MCP requests agent installation with a provisioning profile. Appium's session reported no usable development profile for WebDriverAgent, plus device-install diagnostics. No signing checks were disabled and no new account credentials or certificates were created.

Prepare a valid development identity/profile for the chosen helper, then rerun both iPhone candidates. The connected phone's newer OS/toolchain combination still requires a successful install and control test.

## Why Mobile MCP is preferred, provisionally

Its structured tool vocabulary and accessibility refs fit the intended autonomous action loop; the Android result includes identifiers/bounds needed for later element-ID masking. Appium also provides working Android control and remains an alternative. This preference is an engineering inference, not a claim of proved iOS or MAUI compatibility.

Credential input/logging and element masking still require CIMT-side controls; direct adapter logging must not leak secrets.

## Reproduction

With the prerequisite environment active:

- scripts/evaluate-mobile-mcp.py --output <private-evidence-folder>
- Start Appium on 127.0.0.1:4727 with a private log.
- Stop Mobile MCP's native daemon before switching adapters on Android.
- scripts/evaluate-appium.py --output <same-private-evidence-folder> --platform android
- iPhone session evaluation additionally needs the appropriate Apple team/signing setup.

These are engineering probes, not CIMT's eventual user-facing test commands. Close sessions and stop the temporary Appium server afterward.

## Remaining gate

1. Valid iPhone helper signing and verified UI/screenshot/input control.
2. A real application build and install on both platforms.
3. Reset/login, crash diagnostics/relaunch, and adaptive action checks.
4. Successful simultaneous operation on two devices.
5. Unattended verification under the actual Jenkins account.
6. Record a final adapter decision after those checks.

References: [Mobile MCP capabilities](https://github.com/mobile-next/mobile-mcp), [Appium iPhone device preparation](https://appium.github.io/appium-xcuitest-driver/latest/getting-started/device-setup/).
