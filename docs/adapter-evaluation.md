# Physical-device adapter evaluation

Date: 28 October 2026  
Status: Android checks completed; Appium iPhone control verified; full qualification remains open

## Decision

Mobile MCP was the preferred candidate provisionally after the first Android checks. Following Xcode account recovery, Appium is now the first candidate to demonstrate basic control on both physical platforms. **Final adapter selection is not approved by these smoke checks:** the agreed gate still requires a real MAUI application, reset, and unattended operation. CIMT retains its interchangeable adapter boundary.

Both candidates have demonstrated Android control. Appium has now demonstrated iPhone UI inspection, screenshots, and navigation; Mobile MCP's separate iPhone helper still needs a valid profile. The approved full qualification gate is preserved.

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
| iPhone control | Blocked: DeviceKit agent not installed and requires a signing profile. | Passed: signed WDA installed/launched; UI, screenshots, Home and Settings navigation verified. |
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

Mobile MCP's structured tool vocabulary and accessibility refs fit the intended autonomous action loop; the Android result includes identifiers/bounds needed for later element-ID masking. That original preference was an engineering inference. Appium now has stronger demonstrated cross-platform control evidence. Mobile MCP iPhone compatibility and complete MAUI workflows remain unproved; the final decision must follow the remaining gate.

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

1. Finish candidate comparison: Appium signing/UI/screenshot/navigation now pass; Mobile MCP signing/control and input-entry coverage remain open.
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
