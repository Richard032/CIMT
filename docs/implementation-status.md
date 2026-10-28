# CIMT implementation status

Updated: 28 October 2026

## Reviewed increment 1 — adapter evaluation

Done: Android control probes for Mobile MCP and Appium; local evidence recorded; competing Android sessions diagnosed and isolated.

Follow-up: Appium iPhone signing and basic control now pass. Mobile MCP was preferred provisionally before those results; its DeviceKit helper is now installed, while application control remains pending an unlocked-phone check. The final qualification gate remains open.

See [evaluation](adapter-evaluation.md).

## Reviewed increment 2 — CLI/configuration foundation

Done: .NET command parsing, YAML mapping merge/list replacement, declaring-file path origins, explicit model/time/budget presence checks, unknown-key validation, owner-only secret files, redacted effective configuration, single-run lock, and local HTML readiness/error reports.

Verified: zero-warning build; 15 foundation checks passed; installed validate command checked the actual Subgit branch and connected devices. This demonstration used a synthetic credential for presence checking only and sent no OpenAI request.

Working command: validate. Help is available. setup/run/replay names are recognized but their execution engines explicitly return error/incomplete reports. No fake application pass is emitted.

## Reviewed increment 3 — default build scripts

Done: Android/iOS defaults installed, shared .NET worker, request/result contract, artifact disambiguation, failure/stale-result protection, and signing-property output redaction.

Verified: four simulated contract checks passed; actual Android/iOS publish attempts executed against a temporary main clone with submodules.

Blocked: Android repository pre-build assumes Windows commands; iOS provisioning unavailable. No successful real installable artifact yet.

See [build contract](build-script-contract.md).

## Reviewed follow-up — connected iPhone

Done: wired pairing, Developer Mode, developer services, and tunnel verified. A valid legacy development identity and matching app-specific profiles were confirmed, correcting the earlier identity classification.

Initial blocker: Xcode rejected its saved Apple-account login during automatic provisioning (exit 65). The product owner restored access; the next build/signature check passed and Appium completed 11 iPhone control checks. Mobile MCP subsequently installed its separate DeviceKit helper using a matching wildcard profile; its application probe is blocked by the phone lock.

Done on follow-up: WDA helper installed/launched, UI source/screenshots/Home/Settings navigation checked, and session/server cleanup completed. The initial early foreground-query failure is retained; a bounded transition wait resolved it on retry. See installation sections 11–12. Application build acceptance, final adapter selection, and the overall remaining work below remain open.

## Reviewed follow-up — Mobile MCP DeviceKit

Done: valid wildcard profile checked against expiry, development entitlement, phone inclusion, and available signing identities. Stock DeviceKit 0.0.35 installation succeeded. No helper source or bundle-identifier changes were needed.

Blocked: phone locked again. Initial raw UI/screenshot responses showed the passcode screen; Settings launch timed out. Those responses do not establish application control. A lock-state guard was added to the engineering probe and verified to stop application actions on the locked phone.

Next: unlock and keep the phone unlocked, then run the iPhone-only guarded probe. Installation section 13 contains the procedure. No full adapter qualification is claimed.

## Overall done

- Approved requirements and architecture/CLI/YAML design.
- Mac inventory, prerequisite bootstrap and rerun, maintained installation guide.
- Noninteractive Subgit application read access.
- Both adapter candidates installed and Android control evaluated; Appium iPhone helper/control verified in 11 smoke checks; Mobile MCP DeviceKit installed.
- CLI/configuration foundation and readiness reports.
- Default build-script implementation and contract tests.

## Overall remaining

- Complete unlocked Mobile MCP iPhone application control, input-entry coverage, and full final adapter qualification.
- Correct/configure app-specific macOS pre-build support and verify real APK/IPA builds.
- Implement full setup/run/replay, repository lifecycle, max-two-device scheduling, AI interpretation, strict billing reservations, reset/login, masking, crash recovery, and adaptive replay.
- Complete per-step application evidence and requirement-outcome reports.
- Complete runnable user command/reset demos, manifest-driven provisioning, Jenkins and second-Intel-Mac acceptance.
- Move CIMT's own repository to Subgit later when the destination/migration is supplied.

No requirement gate was silently relaxed. Integration fixtures and incomplete commands are explicitly distinguished from working product behaviour.
