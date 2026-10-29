# Physical-device adapter evaluation

Date: 29 October 2026  
Status: both candidates have Android/iPhone basic control evidence; full application qualification remains open

## Decision

Mobile MCP was the preferred candidate provisionally after the first Android checks. Following Xcode account recovery, Appium was the first candidate to demonstrate basic control on both physical platforms. Mobile MCP subsequently passed eight guarded iPhone smoke checks as well. **Final adapter selection is not approved by these smoke checks:** the agreed gate still requires a real MAUI application, reset, and unattended operation. CIMT retains its interchangeable adapter boundary.

Both candidates have demonstrated Android control. Appium has now demonstrated iPhone UI inspection, screenshots, and navigation; Mobile MCP's separate DeviceKit helper is installed and its guarded unlocked-phone check passed. The approved full qualification gate is preserved.

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
| iPhone control | DeviceKit 0.0.35 installed; all eight guarded iPhone Settings/UI/screenshot/swipe/Home checks passed after unlocking. | Passed: signed WDA installed/launched; UI, screenshots, Home and Settings navigation verified. |
| Successful simultaneous Android+iOS control | Not demonstrated. | Not demonstrated. |
| MAUI install/reset/login/crash workflow | Not demonstrated. | Not demonstrated. |
| Jenkins account operation | Not demonstrated. | Not demonstrated. |

A returned command is not proof of every expected visual transition. These are control smoke checks, not app requirement test results.

## Android ownership finding

Appium's first Android session failed with UiAutomation not connected while Mobile MCP's daemon still owned automation state. After stopping the native daemon, Appium created its session and completed UI/screenshot/navigation checks.

CIMT must give one adapter exclusive ownership of each device and clean up its sessions/helpers. The maximum two-device policy means two different devices, not two competing adapters on one phone.

## iPhone signing findings

The follow-up check found one valid legacy iPhone Developer identity with its private key available, plus valid app-specific development profiles matching that identity and the connected phone. The earlier statement that no development identity was available was incorrect. The matching wildcard development profiles are expired, and no usable helper-specific profile was found. App-specific ECON profiles do not provision an unrelated automation helper.

Mobile MCP requests agent installation with a provisioning profile. Appium's session reported no usable development profile for WebDriverAgent, plus device-install diagnostics. No signing checks were disabled and no new account credentials or certificates were created.

The first dedicated WebDriverAgent build with automatic provisioning exited 65 because Xcode rejected its saved Apple-account login. After the product owner restored account access, the same build succeeded and signature verification passed. Its new development profile covers the connected phone. The phone is paired, wired, and has Developer Mode and developer services enabled. Appium then installed/launched the signed WDA helper and completed 11 control checks. See installation sections 11–12.

## Original Mobile MCP preference and current evidence

Mobile MCP's structured tool vocabulary and accessibility refs fit the intended autonomous action loop; the Android result includes identifiers/bounds needed for later element-ID masking. That original preference was an engineering inference. Both candidates now have basic Android/iPhone control evidence. Mobile MCP's guarded iPhone check passed after unlocking; complete MAUI workflows remain unproved. The original preference remains provisional and the final decision must follow the remaining gate.

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

1. Finish candidate comparison: Appium signing/UI/screenshot/navigation now pass; Mobile MCP helper signing/installation now pass; guarded iPhone basic control now passes. Input-entry coverage remains open.
2. A real application build and install on both platforms.
3. Reset/login, crash diagnostics/relaunch, and adaptive action checks.
4. Successful simultaneous operation on two devices.
5. Unattended verification under the actual Jenkins account.
6. Record a final adapter decision after those checks.

References: [Mobile MCP capabilities](https://github.com/mobile-next/mobile-mcp), [Appium iPhone device preparation](https://appium.github.io/appium-xcuitest-driver/latest/getting-started/device-setup/).


## Follow-up control check after Xcode recovery

The dedicated Appium helper build completed with exit 0 and passed strict signature verification. The first session waited for the phone to be unlocked. UI source and screenshots worked, but an immediate query after Home still returned Settings. That first result is retained.

A repeat probe kept the same expected foreground applications and added a bounded eight-second polling wait for transitions. All 11 checks passed: physical session, UI source, Settings screenshot, Settings foreground, Home command, SpringBoard foreground, Home screenshot, Settings reactivation, Settings foreground after return, return-Home command, and session closure. The Home transition was observed after about 1.2 seconds. Screenshots were inspected locally and show Settings and the Home screen.

The signed helper remains installed for reuse; the temporary Appium server and its owned test process were stopped. No real MAUI application, reset/login flow, crash recovery, text entry, or simultaneous two-device execution was validated by this check.


## Mobile MCP DeviceKit follow-up

The refreshed profile inventory now contains an unexpired team wildcard development profile covering the phone and matching available signing identities. The stock Mobile CLI installer successfully signed and installed DeviceKit 0.0.35 without helper source changes or bundle renaming.

The initial control probe timed out launching Settings. UI and screenshot responses were returned, but local inspection showed the passcode screen. A repeated attempt had the same readiness issue. These are retained as incomplete application checks, not passed app control. devicectl JSON confirmed passcodeRequired=true.

The probe now checks iPhone lock readiness before application actions. An actual locked-device check verified that it records one failed readiness check and stops before launch/screenshots/gestures. Installation is complete. The first probe was pending an unlocked phone; the subsequent successful result is recorded below. See installation section 13. Raw profile details, device IDs, UI, and images remain private.


## Successful Mobile MCP check after unlocking

The fresh guarded iPhone-only probe passed all eight checks: unlocked readiness, Settings launch, UI elements, screenshot, swipe command, Home command, Home UI elements, and Home screenshot. Local image inspection confirmed Settings and the Home screen. Previous lock-screen attempts remain preserved; the readiness blocker is resolved for this check.

The temporary MCP client and native daemon were stopped. DeviceKit remains installed. This is basic control evidence on the inspected phone/toolchain, not proof of text input, simultaneous operation, application reset/login/crash handling, Jenkins execution, or the complete final adapter gate.

## Read-only production masking check — 29 October 2026

Both connected platforms passed the production lossless-PNG capture and element-ID masking smoke check. Android returned 1080 × 2340 pixels; iPhone returned 828 × 1792 pixels. The selected visible mask was black, its UI text was hidden, and image metadata was absent. Checks ran sequentially without navigation, typing, app resets, AI calls, or a real MAUI build. No raw screen image or UI response was saved.

The connected iPhone initially had no DeviceKit installed. Installing it with an existing profile matching the phone and an available signing identity restored UI access; the repeated check passed. Connection and pairing must therefore be checked separately from helper installation. No CIMT product-code change was needed. See [installation section 22](installation.md#22-connected-device-masking-check--29-october-2026) and [masking limits](screenshot-masking.md).

This adds physical capture/masking evidence. It does not establish real credential-entry, orientation changes, simultaneous two-device operation, application reset/crash handling, or unattended Jenkins acceptance. Final adapter selection remains open.
