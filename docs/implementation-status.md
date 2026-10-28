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
- Shared UTC run identity and paired work/report folder allocation, with collision, lock, retention, and portability checks.
- Main-branch example with both build configurations, private YAML template, text inputs, and an application-specific macOS pre-build adapter.

## Overall remaining

- Complete input-entry coverage, simultaneous-device checks, and full final adapter qualification.
- Supply the existing API key locally; verify model access and the real public-command run.
- Verify real APK/IPA builds through the configured macOS adapter and refreshed signing profiles.
- Qualify the implemented lifecycle, scheduling, budget reservations, reset/login, masking, evidence, and crash recovery against the real application.
- Complete semantic scenario decomposition, setup/replay, adaptive replay, and real-app requirement-outcome acceptance.
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


## Reviewed increment — small responsibilities and unit tests

Done: added repository development rules in AGENTS.md: small classes and methods, one purpose per method, simple designs, simple English comments, focused unit tests, and no proxy pattern. Added shared formatting rules and a developer guide.

Done: separated command parsing/routing, settings and redaction, process access, time limits, run steps, owned cleanup, builds, outcome policy, and HTML. The build worker now separates request/argument/process/artifact/result responsibilities. The Python worker now separates scheduling, objectives, actions, coverage, crashes, reset, screen capture/masking, evidence, budget, prompts, HTTPS, and MCP messages. Tests use normal constructors with fake dependencies; constructor bypasses were removed. Legacy regression cases now have named methods and setup helpers.

Verified: 68 unit tests passed (36 .NET; 13 existing Python policy tests plus 19 new component/scenario tests). All 18 CLI/configuration/cleanup regression checks, four simulated build-contract checks, and one MSBuild adapter fixture also passed: 91 checks in total. No paid API requests, physical-device operations, or real MAUI builds ran during this refactor.

Review: this changes internal structure, not the approved command/configuration or test behavior. No requirement gate was relaxed. Real app builds and device acceptance remain pending. Use bash scripts/check-development.sh for the complete development suite; see the [developer guide](development.md).

## Reviewed increment — defects R1–R7

Done: fixed all six confirmed defects from the [product review](reviews/2026-10-28-product-implementation-review.md). Explicit instruction/requirement checks now affect verdicts without needing a crash. Navigation alone cannot pass. A returned failure remains visible if a limit expires, and later evidence can resolve an earlier unknown check. Sensitive fields are checked on both sides of capture. Known crashes and performed actions survive capture/storage errors. Native commands receive their redactor through the constructor. Replacement build scripts use per-field YAML fallbacks; invalid target metadata allows later targets to continue. Helper shutdown errors no longer prevent verified owned-clone deletion.

Done: separated device scheduling from execution. Small recording services test zero, one, two, and three devices without real threads, barriers, locks, report setup, or method replacement. Updated AGENTS.md and the development guide with both rules about complicated unit tests. HTML shows recorded checks and evidence, and keeps failed totals visible when detail sections are disabled.

Verified: 62 .NET unit tests, 64 Python unit tests, 18 CLI/lifecycle regression checks, four build-contract simulations, and one MSBuild example fixture pass: 149 checks total. They make no OpenAI calls, operate no physical phones, and do not build the real MAUI application. Test count describes the verification performed, not product completeness.

Installed on the first Mac: republished the host and build worker, copied all Python support modules, and checked the public help command. Installed host/module files match the corrected source build. Existing private configuration was preserved.

The command and YAML interface and approved requirements remain unchanged. Complete per-requirement inventory/evaluation, explicit scenario decomposition, setup/replay, interruption/run-identity work, real app/device qualification, Jenkins, and second-Mac acceptance remain open. The iPhone is unavailable. Existing-key configuration and real model access remain unverified; no private YAML was read or changed during these fixes.

## Reviewed increment — complete requirement mapping

Done: catalogue every nonblank supplied source item before preflight/builds, with original text, one-based line ranges, generated IDs, and a hash of the redacted source snapshot. Wrapped text remains together; compound items are assessed as a whole. No heading/context text is silently omitted. Every objective starts with a result and explanation for every item.

Done: require known catalogue IDs in requirement checks; validate exact instruction quotes for overrides; preserve failed findings across retries; resolve unknown results by ID; retain expected/observed behavior, step references, masked screenshots, or evidence-error explanations. Check recording has its own small service. The model receives current requirement results without duplicating the source text.

Done: render every requirement and applicable target/startup-device pair, including failed builds, locked devices, and work that never started. Missing coverage prevents a pass; unresolved scopes keep completion incomplete even alongside a failure. HTML and result.json retain the complete matrix. The public command/YAML interface is unchanged, and no paid extraction/planning call was added.

Done: added a runnable offline five-status demonstration in examples/requirement-mapping, including an explained override and an inconclusive result. It uses real catalogue/report services with synthetic observations; its exit 1 and incomplete result are expected. It does not use OpenAI, build a real app, or operate a phone. See [mapping documentation](requirement-mapping.md).

Remaining: real Android/iOS requirement-evaluation acceptance, semantic scenario decomposition, setup/replay, interruption/run-identity work, final adapter qualification, Jenkins, and second-Mac acceptance. The iPhone remains unavailable. Private configuration was not read or changed.

Verified for this increment: 99 .NET unit tests, 87 Python unit tests, 18 CLI/lifecycle checks, four simulated build-contract checks, and one MSBuild fixture passed: 209 checks total. The public-command regression also verifies that a failed build remains in the requirement matrix. The offline demo retained all five statuses, an exact instruction override quote, source line references/fingerprint, and the expected failed/incomplete outcome. No live API call, real MAUI build, device operation, or private-configuration read was performed.

First-Mac mapping installation verified: republished the host, copied all Python support modules, checked public help, and compared installed files with the source build. Private configuration was preserved.

## Reviewed increment — run identity exactly follows the folder contract

Done: replace independent work/report clocks and suffixes with one RunIdentity and allocated RunFolders pair. The command captures invocation time once, and every temporary/retained folder name uses the same selected timestamp. The completed open engineering details are UTC, millisecond precision, and one shared millisecond advance on collisions. Actual start and deadline remain unchanged.

Done: retain run-identity.json and propagate the same ID through final/command reports, HTML, progress, runtime requests/results, and CIMT_RUN_ID for child processes. Allocate report-only identities for validation and early failures. Keep the Mac lock until final/error reporting finishes. Rejected invocations cannot enter the run or alter active work/reports.

Done: prevent report placement inside planned/owned cleanup folders, including aliases; never adopt a newly occupied work path; protect retained reports during interrupted cleanup; keep older ownership records readable. The public-command fixture captures the actual work name before cleanup and verifies the report and runtime identity afterward.

Verified: 119 .NET unit tests, 88 Python unit tests, 18 CLI/lifecycle checks, four simulated build-contract checks, and one MSBuild fixture passed: 230 total. Focused cases cover names, UTC, collisions, files/links/reservations, original deadlines, declaring-file roots, metadata, report retention/copying, command/error locks, and rejected invocation safety. No live API, real app build, or physical-device operation was performed.

No requirements were relaxed. The format/timezone/collision choices complete details the design had explicitly left open. Full interruption history and graceful cancellation remain pending, along with the other scenario/setup/replay, real-device, Jenkins, and second-Mac release work. See [run identity](run-identity.md).

First-Mac identity installation verified: republished the host, copied all Python modules, checked public help, and confirmed installed files match the source build. The offline demo retained matching folder, result, and HTML identity metadata. Private configuration and existing reports were preserved.

## Reviewed correction — document headings are context

Done: recognize explicit Markdown hash and underlined headings in a separate reader. Retain heading text, level, and original line ranges without requirement IDs or statuses. Keep active section context beside each actual requirement for the worker and report. Heading-looking code examples and ambiguous plain prose are not guessed to be headings.

Done: retain all headings in requirements.json, final result.json, and a mandatory HTML context section, including heading-only documents and when optional input details are hidden. Headings no longer prevent a passed requirement from completing. Updated FR-27, AC-24, architecture, mapping rules, product guide, review resolution, and the runnable example. Table-header classification and platform applicability remain separate decisions.

Verified: 142 .NET unit tests, 89 Python tests, and 23 CLI/build/example checks passed: 254 checks total. The synthetic example retains one context heading and its five requirement results. No API, real app build, phone operation, or private configuration read was needed. The first Mac's installed host and action prompt match the tested source; public help works.

Other findings in the [design review](reviews/2026-10-28-design-contract-review.md), including redaction, instruction coverage, exact-scenario scope, and failure-policy priority, remain open. This correction does not close real-device or release acceptance.

## Reviewed correction — redaction preserves results and masks original UI text

Done: resolve design-review D1 and D2. Python record-aware redaction preserves status/source, generated IDs, action metadata, target/device identity, and evidence links while scrubbing observations and unknown payload fields. CheckRecorder validates after redaction. Unknown check statuses cannot produce a pass. The .NET final report sanitizes parsed record values before serialization; HTML preserves metadata and displays sanitized JSON details. Configuration snapshots and build logs share corrected text handling, including overlapping secrets, existing markers, and supported JSON-escaped spellings.

Done: detect screenshot secrets in original nested strings before JSON escaping. Preserve UI references/control types while masking secret text. Element-ID/secure-field masks also hide nested UI text values. Unreliable required masks still stop execution. Added small classes, simple English comments, focused tests, and [redaction documentation](redaction.md). Approved requirements and public command/YAML contracts are unchanged.

Verified: 165 .NET unit tests, 113 Python tests, and 23 CLI/build/example checks pass: 301 checks total. The original instruction-only false-pass case now retains failed and exit 1 through the actual Python recorder/journal and .NET report writer. Tests separately cover valid JSON for a one-digit secret, unchanged run identity and requirement IDs, retained evidence links, escaped observations/diagnostics and decoded HTML, marker-prefix secrets, and pixel masking for Unicode/quotes/backslashes/newlines. No API, real MAUI build, phone operation, or private configuration read was used.

First-Mac installation verified: republished the host and build worker, copied all Python modules including record_redaction.py, compared installed files with the tested source, and checked public help. Historical reports and private configuration remain unchanged. Real-device privacy acceptance and the other review findings remain open: complete instruction coverage, exact-scenario scope, table/platform applicability, and instruction-defined failure policy.
