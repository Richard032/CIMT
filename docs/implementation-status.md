# CIMT implementation status

Updated: 28 October 2026

## Reviewed increment 1 — adapter evaluation

Done: Android control probes for Mobile MCP and Appium; local evidence recorded; competing Android sessions diagnosed and isolated.

Blocked: iPhone helper signing. Mobile MCP is preferred for initial integration, but the final cross-platform selection gate remains open.

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

## Overall done

- Approved requirements and architecture/CLI/YAML design.
- Mac inventory, prerequisite bootstrap and rerun, maintained installation guide.
- Noninteractive Subgit application read access.
- Both adapter candidates installed and Android control evaluated.
- CLI/configuration foundation and readiness reports.
- Default build-script implementation and contract tests.

## Overall remaining

- Complete iPhone provisioning/control and final adapter qualification.
- Correct/configure app-specific macOS pre-build support and verify real APK/IPA builds.
- Implement full setup/run/replay, repository lifecycle, max-two-device scheduling, AI interpretation, strict billing reservations, reset/login, masking, crash recovery, and adaptive replay.
- Complete per-step application evidence and requirement-outcome reports.
- Complete runnable user command/reset demos, manifest-driven provisioning, Jenkins and second-Intel-Mac acceptance.
- Move CIMT's own repository to Subgit later when the destination/migration is supplied.

No requirement gate was silently relaxed. Integration fixtures and incomplete commands are explicitly distinguished from working product behaviour.
