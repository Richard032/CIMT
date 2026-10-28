# CIMT implementation status

Updated: 28 October 2026

## Reviewed increment 1 — adapter evaluation

Done: Android control probes for Mobile MCP and Appium; local evidence recorded; competing Android sessions diagnosed and isolated.

Follow-up: Appium iPhone signing and basic control now pass. Mobile MCP was preferred provisionally before those results; its DeviceKit helper is now installed and eight guarded iPhone smoke checks passed after unlocking. The final qualification gate remains open.

See [evaluation](adapter-evaluation.md).

## Reviewed increment 2 — CLI/configuration foundation

Done: .NET command parsing, YAML mapping merge/list replacement, declaring-file path origins, explicit model/time/budget presence checks, unknown-key validation, owner-only secret files, redacted effective configuration, single-run lock, and local HTML readiness/error reports.

Verified: zero-warning build; 15 foundation checks passed; installed validate command checked the actual Subgit branch and connected devices. This demonstration used a synthetic credential for presence checking only and sent no OpenAI request.

At this increment the working command was validate. Help and explicit setup/run/replay limitations were available. The initial run engine described below supersedes that run status. No fake application pass is emitted.

## Reviewed increment 3 — default build scripts

Done: Android/iOS defaults installed, shared .NET worker, request/result contract, artifact disambiguation, failure/stale-result protection, and signing-property output redaction.

Verified: four simulated contract checks passed; actual Android/iOS publish attempts executed against a temporary main clone with submodules.

Build acceptance remains open: the Android attempt hit Windows-specific pre-build commands, and the iOS attempt failed provisioning. iOS needs revalidation with the refreshed profiles. No successful real installable artifact yet.

See [build contract](build-script-contract.md).

## Reviewed follow-up — connected iPhone

Done: wired pairing, Developer Mode, developer services, and tunnel verified. A valid legacy development identity and matching app-specific profiles were confirmed, correcting the earlier identity classification.

Initial blocker: Xcode rejected its saved Apple-account login during automatic provisioning (exit 65). The product owner restored access; the next build/signature check passed and Appium completed 11 iPhone control checks. Mobile MCP subsequently installed its separate DeviceKit helper using a matching wildcard profile; its subsequent guarded unlocked-phone probe passed all eight smoke checks.

Done on follow-up: WDA helper installed/launched, UI source/screenshots/Home/Settings navigation checked, and session/server cleanup completed. The initial early foreground-query failure is retained; a bounded transition wait resolved it on retry. See installation sections 11–12. Application build acceptance, final adapter selection, and the overall remaining work below remain open.

## Reviewed follow-up — Mobile MCP DeviceKit

Done: valid wildcard profile checked against expiry, development entitlement, phone inclusion, and available signing identities. Stock DeviceKit 0.0.35 installation succeeded. No helper source or bundle-identifier changes were needed.

Initial blocker (resolved): phone locked again. Initial raw UI/screenshot responses showed the passcode screen; Settings launch timed out. Those responses do not establish application control. A lock-state guard was added to the engineering probe and verified to stop application actions on the locked phone.

Resolved on follow-up: the product owner unlocked the phone; a fresh guarded iPhone-only probe passed all eight smoke checks. Settings and Home screenshots were inspected locally. The temporary client/daemon were stopped. Installation section 13 records the procedure and result. No full application/adapter qualification is claimed.

## Overall done

- Approved requirements and architecture/CLI/YAML design.
- Mac inventory, prerequisite bootstrap and rerun, maintained installation guide.
- Noninteractive Subgit application read access.
- Both adapter candidates installed and Android control evaluated; Appium iPhone helper/control verified in 11 smoke checks; Mobile MCP DeviceKit installed and eight guarded iPhone smoke checks passed.
- CLI/configuration foundation and readiness reports.
- Default build-script implementation and contract tests.
- Initial public run path, local support runtime, bounded action selection, owned clone lifecycle, max-two-device scheduling, evidence/report generation, and failure precedence, checked with simulations.
- Main-branch example with both build configurations, private YAML template, text inputs, and an application-specific macOS pre-build adapter.

## Overall remaining

- Complete input-entry coverage, simultaneous-device checks, and full final adapter qualification.
- Supply the existing API key locally; verify model access and the real public-command run.
- Verify real APK/IPA builds through the configured macOS adapter and refreshed signing profiles.
- Qualify the implemented lifecycle, scheduling, budget reservations, reset/login, masking, evidence, and crash recovery against the real application.
- Complete scenario decomposition, setup/replay, adaptive replay, and full requirement-outcome reporting.
- Complete runnable user command/reset demos, manifest-driven provisioning, Jenkins and second-Intel-Mac acceptance.
- Move CIMT's own repository to Subgit later when the destination/migration is supplied.

No requirement gate was silently relaxed. Integration fixtures and incomplete commands are explicitly distinguished from working product behaviour.

## Reviewed increment — user-facing main-branch exploration

Done: the requested workflow now enters through cimt run. The example folder holds default and application YAML, instructions, requirements, setup notes, and macOS build scripts. Both Release_Generic and Release_Pride are configured on Android/iOS. The executable project and branding identifiers match inspected main source; the separate developer checkout was not changed. The source-inspection clone was deleted.

Done: .NET orchestration and an isolated Python support worker now implement the initial single-objective path. Mobile MCP remains the provisional integration. Host code owns device scheduling, resets, masking, limits, credential entry, crash counters, reporting, and owned cleanup. setup/replay and full scenario decomposition remain unfinished. See [run-engine notes](run-engine.md).

Verified: zero-warning CLI build; 18 CLI/configuration/lifecycle checks, 13 runtime-policy checks, four simulated build-contract checks, and one macOS MSBuild-adapter fixture passed. These 36 checks do not run the real MAUI app or call OpenAI. The runtime was installed with Python 3.14.8, Pillow 13.0.0, and truststore 0.10.5.

Blocked live run: the user chose an existing OpenAI key, but no usable local source has been supplied. An ignored, owner-only example private YAML was prepared with an empty field. Public cimt validate stopped at that field with exit 3 and wrote its error report under the example's timestamped reports folder. No inference, app reset/install, or button exploration occurred in this increment.

Review: the macOS adapter preserves tagging and copying in a fixture; the actual tagger and APK/IPA builds remain unverified. iOS reinstall verifies container reset only; Keychain/backend state needs app hooks where applicable. Current model support is restricted to the documented snapshot/USD pricing profile. These implementation limits are disclosed; the approved release requirements remain unchanged.

Next: provide the existing key locally, validate the example, then execute its documented public run command. Review real build/device results before closing any application or adapter acceptance gate.
