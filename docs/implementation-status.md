# CIMT implementation status

Updated: 31 October 2026

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
- The existing key has been configured locally and one user-started run passed model-access preflight. Qualify inference and the real application run; a later network/TLS failure motivated optional network checkpoints.
- Verify real APK/IPA builds through the configured macOS adapter and refreshed signing profiles.
- Qualify the implemented lifecycle, scheduling, budget reservations, reset/login, masking, evidence, and crash recovery against the real application.
- Complete semantic scenario decomposition, setup, saved-action-history/adaptive replay, and real-app requirement-outcome acceptance. Current-instruction replay using retained apps is implemented below.
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

## Reviewed correction — screenshot masking

Done: inject native full-frame lossless PNG capture into the existing device adapter, keeping raw bytes in memory. Verify single-frame format and pixel orientation, then draw on a fresh opaque canvas to remove transparency and source metadata. Separate ScreenshotImage, MaskGeometry, and CaptureGuard responsibilities. Reject missing/non-finite/overflowed required bounds, non-finite scaling, and aspect mismatch beyond one pixel of rounding. Clip visible bounds before scaling and round outward with a two-image-pixel border. Valid offscreen sensitive fields keep their UI text hidden without painting nonexistent pixels.

Done: bracket capture with screen-size, UI-region, and readiness checks. Region ordering alone does not fail capture; changed or duplicated required regions do. Hide child UI text overlapping a container mask, and conservatively hide text with missing bounds when masks are present. Added simple image/coordinate/capture/native-command cases and [screenshot-masking documentation](screenshot-masking.md). Element-ID-only YAML rules and approved requirements remain unchanged.

Verified: 165 .NET unit tests, 155 Python tests, and 23 CLI/build/example checks pass: 343 checks total. All installed Python modules match the tested source; new modules import and public help works. No API call, real MAUI build, or private configuration access was needed. The read-only Android attempt stopped on the locked phone before capture or app action. The product owner requested skipping physical-device checks for now; no further device actions were attempted. No screenshots or raw UI text were saved.

Remaining: physical Android/iOS masking and credential-entry acceptance, accurate adapter bounds/orientation qualification, and the other open design/release work. UI and screenshot reads are not atomic; observable stability checks do not prove the absence of transient changes. That limit is documented without claiming complete privacy acceptance or relaxing FR-36.

## Physical masking follow-up — 29 October 2026

Done: resumed the previously skipped checks after both devices were connected. Both were online and unlocked. Android passed immediately. The iPhone initially had no DeviceKit installed and failed UI inspection before capture. Installed the helper using an existing profile matching both the phone and a valid available signing identity, then repeated the check successfully.

Verified: the production capture/masking path returned a 1080 × 2340 Android PNG and an 828 × 1792 iPhone PNG. Each had one selected visible mask with all its pixels black. Two Android text fields and four iPhone text fields were hidden. Both outputs were RGB PNGs with no image metadata. Raw screenshots and UI responses stayed in memory; only aggregate results were retained locally. No navigation, typing, reset, application-data change, AI call, or real MAUI build was performed. The separate iPhone helper installation was the device setup change. All 28 installed runtime modules matched source; no product source correction was needed, so the previously recorded 343 offline checks were not rerun.

Done: recorded repeatable readiness, disk-space, helper-status, and profile/identity matching findings in installation section 22. Removed four disposable CIMT installer archives after confirming the corresponding tools were installed. Private configuration and retained reports were preserved. Requirements and command/YAML contracts are unchanged.

Remaining: real credential-entry and orientation masking acceptance, simultaneous two-device operation, full MAUI build/install/reset/crash scenarios, final adapter qualification, Jenkins, second-Mac acceptance, and the other open design findings. These current-screen smoke checks do not close those gates. See [masking details](screenshot-masking.md).

## Independent test workspace — 29 October 2026

Done: prepared /Users/sumkar/Development/testing/FirstRun with private settings, application configuration, three text inputs, five application build-support files, separate work/reports folders, and a local usage guide. Existing private settings were copied without displaying their contents and kept owner-readable/writable only. Public paths are relative to FirstRun's configuration files. The supplied main branch, Release_Generic/Release_Pride targets, and both physical platforms are retained. Build adapters use the installed default workers, so the test folder can run independently of the source checkout.

Verified at preparation time: public input/build paths exist, shell scripts have valid syntax, output roots remained in FirstRun, private configuration permissions were 600, and the installed public launcher returned help from the independent folder. Private settings were not parsed and no model access or real application run was tested. The automatic-output correction below supersedes the manually prepared work/reports folders and output-root settings.

## Reviewed correction — CIMT creates all run output below the inputs

Done: updated FR-08/FR-30, added FR-52/FR-53 and AC-25/AC-26, and aligned architecture/product/path documentation. The input folder is selected from --run-config, otherwise --config. Installed execution is independent of launch location and source checkout. CIMT creates CIMT output/work and CIMT output/reports automatically. Users supply inputs only. This replaces the previous configurable/common-output-root policy at the product owner's explicit request.

Done: added the small OutputLayout service, preserved the selected folder across branch overrides and configuration-load failures, removed installation-folder report fallback, and checked output containment through aliases. Existing root fields load for compatibility but are ignored with a notice and retained output-layout.json metadata. Blocked output never overwrites user files or redirects reports elsewhere. Existing paired identity, retained reports, and owned-clone cleanup continue to apply.

Verified: 181 .NET tests, 155 Python tests, and 28 CLI/build/example checks passed, 364 total. The full suite passed, followed by the extra blocked-output case in the .NET suite. The installed host passed all five public output-layout checks from different launch folders using synthetic credentials and fake readiness tools. These cover automatic creation, paths containing spaces, shared settings, repeated reports, legacy roots, and missing/invalid YAML. No API request, real MAUI build, or device operation was needed.

Installed the corrected host and added a runnable example in examples/input-folder. FirstRun now contains only inputs and custom build support; the earlier empty work/reports folders were removed. Private configuration was not read or changed, and no actual FirstRun validation/test was started. Its CIMT output tree will be created by CIMT on invocation. Real model/application access, Jenkins, second-Mac acceptance, and other open product findings remain separate work.

## Reviewed correction — long helper socket addresses

Observed: the user's FirstRun passed model/runtime preflight without inference, then failed discovery and helper shutdown. The retained result and a read-only installed-helper status check identify a 110-byte socket address where the macOS helper limit is 103 bytes. This confirms key/model preflight for that run; it does not establish inference, app build, or device-control success.

Done: add NativeHomeLink to supply a short temporary transport address pointing into verified owned work. Actual helper files stay below the selected CIMT output tree. Existing unrelated files/links are never adopted or deleted. Normal/interrupted-work cleanup verifies the target before unlinking. Host and worker receive the same address. FR-52/AC-25 and the design document this internal coordination link; public command/configuration and output data placement remain unchanged.

Done: preserve redacted device-discovery and helper-stop errors, retain the redacted helper log before work cleanup, and avoid stopping a global helper when owned-address preparation never completed. These changes use small classes/methods and the existing unit-test framework. No provider or device runtime replacement was needed.

Verified: 196 .NET tests, 155 Python tests, and 28 CLI/build/example checks passed, 379 total. A real local socket binds through the short address while its file remains in a deeply nested target folder. Link ownership, missing/occupied targets, retained/redacted logs, and diagnostics have focused cases. The initial dangling-link test exposed a cleanup defect; it was corrected and the full suite passed. No real API call, MAUI build, or physical-device action was performed by these checks.

Installed: corrected host assembly matches the tested build. Private configuration and the user's reports were preserved. No actual FirstRun was rerun; the user controls the next run. See installation section 24. Physical discovery after this correction, real application execution, final adapter qualification, Jenkins, second-Mac acceptance, and other open findings remain unverified.

## Requirement update — live terminal output

Recorded FR-54/FR-55 and AC-27/AC-28 in requirements version 0.7 after the product owner requested visible Git, build, and debug output. Normal terminal and Jenkins execution must stream stdout/stderr/progress while commands run, identify relevant concurrent work, redact credentials across output chunks, and keep retained diagnostics. No verbose option may be required.

Implementation remains pending. The current process runner collects child output and stage messages do not provide complete live command output. This documentation-only update does not alter source, installed binaries, or the user's active execution. No runtime tests were run for the requirements edit.

## Reviewed increment — manual network-switch checkpoints (superseded wording)

Done: requirements version 0.8 adds FR-56/FR-57 and AC-29/AC-30; architecture version 0.14 and the product/installation guides define the workflow. NetworkCheckpoint handles optional terminal acknowledgement before authenticated OpenAI preflight, before repository/submodule access and all builds, and before AI testing after a successful build. Waiting counts toward the original deadline and preserves the lock, cleanup, redaction, and outcome rules. Configuration/key loading still happens at startup. No network changes, TLS bypass, automatic retry, or key display is introduced.

Done: omitted/false preserves unattended execution without reading input. True requires an interactive terminal; redirected/closed input stops explicitly. The shared deadline stops pending waits, and late acknowledgement cannot start work. Checkpoint stages record waiting/continued without response text. The post-build checkpoint is skipped when no installable build exists. The HTML now labels these as run stages. FirstRun/application.yaml and the tracked ECON example enable pauses; Jenkins must use false. Private configuration was not read or changed.

Verified: 214 .NET unit tests (including 18 checkpoint cases), 18 existing CLI/lifecycle checks, one macOS adapter fixture, and five public output-layout checks pass: 238 checks. The corrected host was installed, compared with the tested assembly, and checked through public help. No real FirstRun was executed, and no authenticated API request, real application build, or device action was issued. The user must exercise actual network changes and the resulting connections. Live terminal child-output streaming remains a separate pending requirement.

Observed blockers retained: the user's 13:03 run passed model access, device discovery, cloning, and recorded submodules, but all four builds failed in CuRMiTagger.exe under Mono (RuntimePolicyHelper/GetRuntimeInterfaceAsObject, NotSupportedException). No installable app was produced. The later 13:18 run stopped at OpenAI transport; a no-key diagnostic showed certificate-chain validation failing on the active network. Network checkpoints enable the requested operator workflow; they do not repair app-tool compatibility or prove backend reachability from the private network. See installation section 25.

## Correction — generic operation information and acknowledgement

The product owner rejected environment-specific instructions in checkpoint messages. execution.interactive-pauses replaces execution.network-switch-pauses. ExecutionCheckpoint now explains only the next operation and asks the user to press Enter. It contains no private/work network instructions or app-specific preparation. The phase positions, unattended default, input privacy, deadline, lock, cleanup, and error policies remain unchanged. Requirements version 0.9, architecture version 0.15, product/installation guides, examples, and FirstRun public inputs are aligned. Private YAML is not read or changed.

Tests explicitly verify generic messages as well as the existing wait, timeout, redirection, and privacy behavior. Verified: 214 .NET unit tests and 18 existing CLI/lifecycle checks passed (232 checks), including generic-message assertions. The installed host assembly matches the tested build and public help succeeds. No actual FirstRun, authenticated API access, application build, or phone action was started. Actual interactive execution remains for the user.

## User-started verification — generic checkpoints and labelled build targets

Report report_2026-10-29_14-03-22-908 records waiting/continued for both generic prompts, passed OpenAI model preflight without inference, completed physical-device discovery, and cloned main with its recorded submodules. Debug_Generic/Debug_Pride were attempted on Android/iOS. All four builds failed in the existing CuRMiTagger.exe/Mono pre-build integration: RuntimePolicyHelper calls GetRuntimeInterfaceAsObject, which throws NotSupportedException. The effective configuration retained Release_Generic/Release_Pride despite the Debug labels; no Debug build was established.

No installable build was produced, so the AI-testing checkpoint was skipped and no app interactions ran. Exit 3/inconclusive/incomplete is expected for this result. Generic interactive checkpoints now have user-run evidence through the build boundary; the third prompt and full application testing remain unverified. Next is Mac compatibility of the required tagger. See installation section 26. No real run was started by the assistant, and no private YAML or application source was changed.

## Correction — selected branch and project-defined tool integration

Verified the selected branch independently: testing/curmitAndNugets resolves to the recorded 8b50dd12f65e0f3ffd9f8df68013d56601473f45. That commit removes the tagger from application PreBuild. The local example override, added by CIMT integration, incorrectly reintroduced the legacy Mono/CuRMiTagger invocation. The earlier conclusion that the current branch required this executable was incorrect. Project-configured CuRMiT must follow the selected Visual Studio/MSBuild configuration.

Done: remove macos.targets/prebuild.targets and their injected global properties/Mono requirement. The example build script now changes only the one known Windows resource-copy command inside the run clone and delegates to installed defaults, preserving other project steps/imports/conditions/properties. No match or duplicate matches leave the project unchanged. FirstRun's live adapter is updated; application.yaml and private settings are unchanged. Requirements v0.10 (FR-58/AC-31), architecture v0.16, and user/install/build guides are aligned.

Verified: four example MSBuild fixture tests and four default-worker contract checks pass, plus shell syntax and live/source equality. No real CIMT run, MAUI build, API call, device action, application-source commit, submodule change, or developer-checkout modification was performed. Core CIMT binaries did not require replacement. Next is the user's retry with the corrected adapter. The prior build blocker does not establish what the selected branch will do under its own build configuration.

## Audit — other hardcoded behavior and overrides

The 29 October [hardcoded-behavior audit](reviews/2026-10-29-hardcoded-behavior-audit.md) confirms remaining exploration rules applied to exact tests, unconditional default-worker property overrides, fixed crash-as-failure policy, and an unconfigurable external-app restriction. It distinguishes these from explicit FirstRun copy/identity settings, known single-objective/model/context limitations, and approved fixed product rules. H1 and H3 overlap previously open design findings; they are not closed by the tagger correction.

Installed consistency checks match 32 source/build-output files with no extra Python module. No runtime/configuration behavior, requirement baseline, private YAML, app source, or device state was changed during the audit. No real run, application build, or API call was performed. The report records evidence and required follow-up rather than claiming that CIMT is fully generic or release-complete.

## Increment — work retention, preserved properties, and retained-app replay

Done: work and publish folders remain after finalization. Older verified work for the same inputs is removed only at the next clone boundary, after preflight/device checks and any acknowledgement. Other input folders/reports are protected. Ownership records support multiple retained work folders and the legacy record format. Owned helper recovery preserves work; unsuccessful stops retain the verified link. Helper logs are redacted in work and report copies.

Done: default build commands forward explicit properties unchanged and leave omitted values to the selected project/SDK. The four unconditional packaging/runtime/archive assignments were removed. Missing installable APK/IPA output reports the needed configuration instead of silently rewriting it. Audit finding H2 is resolved for the tested implementation.

Done: a completed build stage's successful apps are published in per-input retained-builds.json. Replay without --scenario loads/verifies/copies those already built apps, uses current instructions/requirements/setup and credentials, applies normal limits/device policies, preserves work, and creates a new report with original build provenance. Its ordered path has no Git/submodule/restore/build steps and no fallback rebuilding. The original binary identity/compiled settings are retained. Saved-action-history adaptation and the other audit/scenario acceptance gaps remain unfinished.

Requirements v0.11, architecture v0.17, product/installation guides, examples, and FirstRun public documentation are aligned. Private configuration, application.yaml, developer repositories, and existing reports are preserved.

Verified: 425 offline checks passed across the existing .NET/Python/CLI/build/example/layout suites. After the final helper-stop recovery change, 237 .NET tests and 20 CLI checks passed again. The public replay fixture reaches its fake UI worker with Git and build commands disabled; its artifacts are identical to the original build. Normal-run fixtures preserve work during preflight and remove earlier work only at the next clone boundary.

Installed and byte-verified the host/build-worker Release assemblies; public help passed. Installation section 28 records hashes. No API call, real app build, device action, private configuration read, or user test run was performed. Real application build/replay acceptance remains for the user.

## Observed follow-up — retained build fails on missing generated resource

The user-started 15:35 run confirms correct branch/commit and retained checkout/publish-job folders after failure. All four builds stop on missing template/strings.xml (MSB3030). Only the token-filled strings.template.xml is tracked; strings.xml is ignored and listed in CuRMiT-project.xml as generated output. The project still copies that output after its former generator call was removed. No app was installed or tested, and no new retained-build set was published.

No new software workaround was added. The intended application resource-generation process needs clarification; unresolved templates and fabricated build metadata are not substitutes. Installation section 29 records the evidence and the secondary warnings. Earlier offline success did not establish real clean-clone build acceptance.

Follow-up: the 15:52 user run picked up new commit 31836595 and now selects Debug configurations. The newly tracked strings.xml is the copy destination (values/strings.xml); the source (values/template/strings.xml) remains missing, so the same MSB3030 persists. The unchanged original project copy and portable adaptation agree on both paths. Resolve the obsolete application copy task or its intended source-generation process; no CIMT workaround or new build was added.

## Increment — readable failures, activity, overview, and stopping reasons

Implemented FR-61–FR-64 / AC-35–AC-38: mandatory HTML overview with actual configurations and AI count; incremental timestamped host/device activity with durations/context; readable errors and exception locations/log links; separate original failures, worker cancellation, limits/device stops, and incomplete work. Empty worker stderr no longer hides saved device errors. Machine results include activity/stoppingReasons/durationSeconds, and structured activity appears in the terminal. Optional detail settings do not hide these sections. Mask-coordinate diagnostics preserve rejection rules and omit UI values/pixels. The scope changes reporting, not app/device/reset/limit/crash/masking execution policies; full generic process-output streaming remains separately tracked.

Requirements v0.12, architecture v0.18, product guide v0.13, and the diagnostic-reporting contract are aligned. Verification passed: 442 offline checks across the existing suites (246 .NET, 163 Python/runtime, 20 CLI, four build contracts, four example adapters, five layout). The existing synthetic mapping demo produced expected exit 1/incomplete and passed static HTML/result checks. Visual browser preview was blocked by the local-file URL policy, so no visual acceptance is claimed.

Installed and byte-verified the host and 29 runtime modules; public help passed. No private configuration read, real app build/test/replay, API request, or phone operation was performed for this increment. Existing reports and user inputs remain intact. The observed Android mask-stability failure and real device acceptance remain open; installation section 30 records the findings and installation hash.

## Correction — remaining work after scenario interruption

Fixed the empty remaining-work list observed after iPhone relaunch failed. Each returned AI plan is saved with redaction before checks/limits can stop execution. A scenario finalization boundary retains that plan and adds known unresolved requirement/control counts on errors or early returns; a generic unfinished-objective message covers unknown pending work. Counts reflect accepted actions even if later capture fails. Later plans replace older ones, and completion clears obsolete tasks. Existing exit, verdict, crash, reset, device, and masking policies are preserved.

Requirements v0.13 (FR-64/AC-38), architecture v0.19, product guide v0.14, diagnostic contract, and installation v0.18 are aligned. Relevant existing suites passed 438 checks: 247 .NET, 158 Python unit, 13 runtime policy, and 20 CLI/lifecycle. Eight Python and one HTML regression tests were added. Installed scenario.py matches tested source byte-for-byte; existing reports/private inputs remain untouched. No real app test or API call was started. The iPhone launch/control investigation and other acceptance gaps remain open.

## Correction — remove project rewriting from supplied build wrappers

Removed the Windows resource-copy replacement from the source ECON example and both local test input folders. The shared wrapper only delegates to the installed default platform script. Project files and build requests stay unchanged; platform compatibility and tool integration belong to the selected application project. This supersedes the earlier copy-rewrite adapter behavior. Configured target/platform/branch values and private settings are unchanged.

Requirements v0.14 (FR-58/AC-31), architecture v0.20, product v0.15, installation v0.19, and the build contract/example are aligned. Existing retained apps and work are preserved; a normal run is needed to produce an app with the unchanged project. No real app build, OpenAI request, or phone operation was performed. The app icon/startup issue remains under investigation.

Verified: all four existing example-build fixture checks passed; shell syntax and equality of all three wrapper copies passed. No installed binary/runtime replacement was required.

## Correction — screenshots across OS permission transitions

Implemented bounded fresh-capture retries for valid screen-size or sensitive-region changes, including the observed Bluetooth permission alert during initial capture. CaptureChanged is separate from invalid geometry and arbitrary infrastructure failures. ScreenCapture retries at most three times, waits 250 ms within the run deadline, and releases only a newly validated masked image. Mobile logs discarded attempts without UI values or pixels. HTML now explicitly identifies scenarios with no verified screenshot instead of leaving missing evidence unexplained.

Requirements v0.15 (FR-28/FR-36/AC-10), architecture v0.21, product v0.16, installation v0.20, and the screenshot/diagnostic guides are aligned. The initial failure made no AI requests and saved no image, so historical evidence is not recoverable. Existing app behavior, verdict policy, masking checks, private input files, and reports are preserved. Full physical-device acceptance and the separate wrong-app/foreground issue remain open.

Permission decisions are controlled by testing instructions. The AI guidance requires explicit authorization to accept or deny an OS request; otherwise a blocking prompt is reported as blocked/incomplete, not a permission-only app failure. Capture retries only collect images and never click dialog buttons. For the local TestRun_SingleDevice_SingleTarget inputs only, instructions now authorize Allow (or its equivalent) for the tested ECON-M application. FirstRun and public example instructions were not given that authorization.

Verification: 449 relevant offline checks passed (249 .NET, 167 Python unit, 13 runtime policy, 20 public CLI). The published host and five changed Python modules were installed and byte-verified; installed help passed. Only TestRun_SingleDevice_SingleTarget's text instruction/README was updated locally. No private configuration, existing report, application source, or device state was changed, and no live run or API request was started.

## Bounded AI response correction — 30 October 2026

FR-65 / AC-39 are implemented. The check schema ties source to an empty/nonblank requirement ID through nested alternatives. InvalidAgentResponse distinguishes correctable model contract/mapping errors from transport, masking, device, storage, refusal, and incomplete-provider failures. DecisionRecovery validates shape, checks, catalogue membership, and override quotations before the accepted plan/ledger or action can change. It permits the initial answer plus two corrections, checking the shared stop/deadline and obtaining a fresh verified masked screen before each correction. Agent still reserves and settles the shared budget for every request.

Rejected candidates and their decision screenshots/evidence errors are published as redacted unaccepted diagnostics, separately from check/action history. Their fields receive no typed metadata exemption. HTML exposes them with an explicit verdict exclusion even when optional details are disabled. Activity logs contain rejection/recovery reason and device/target/attempt context, not raw candidate text. Earlier accepted failures remain effective. Exhaustion retains remaining work and uses the existing exit-3 blocking-error/shared-cancellation policy; time/budget stops retain normal precedence. No action is replayed by correction.

Requirements v0.16, architecture v0.22, product v0.17, installation v0.21, diagnostic reporting, and the development guide are aligned. New tests cover invalid-then-valid execution once, three-response exhaustion, unknown IDs, invalid override quotes, preserved accepted and unaccepted failures, malformed JSON, invalid-metadata/feedback redaction, fresh refs, deadline/budget stops, activity context, refusal/incomplete output, and capture/storage errors. No private configuration, historical report, application repository, or device state is modified. Live API schema acceptance and real-device testing remain separate acceptance gates.

Verification for this increment: 467 relevant offline checks passed (250 .NET unit tests, 184 Python unit tests, 13 runtime-policy checks, and 20 public CLI/lifecycle checks). The final host was published successfully. The installed host and eight changed/new runtime modules match the tested files byte-for-byte, and installed public help passed. Installed cimt.dll SHA-256: df3f2d9d51693a5011b74954531d3d183eb7d7fe8fd8af3bfb5888d778ee0bc2. Backup: /private/tmp/cimt-before-decision-correction.e8hvj7ht. No real app run/replay, paid API request, or phone action was started.

## Exploration continuity and interruption reports — 30 October 2026

FR-66–FR-69 / AC-40–AC-43 are implemented. ExplorationMemory stores whole-scenario views, identified controls, attempts, untried paths, transitions, observed UI outcomes, and the accepted pending plan. Current refs are rebound per capture and the prompt receives bounded relevant summaries, independently of the recent 24-action window. Reports persist the complete redacted memory and show observed outcomes. No cross-run resume or semantic proof of functional success is claimed.

No-progress validation rejects three unchanged attempts or repeated navigation without new paths and requests bounded replanning. Explicit repeat tests use an exact instruction quote and reason; the host verifies quote membership, while the AI interprets its meaning. Exhausted no-progress replanning stops only that scenario incomplete. Other response-contract, crash, evidence, budget, and shared-failure policies keep their existing behavior.

RunInterruption propagates Ctrl+C/SIGTERM through host cancellation and a report-local marker; RunSignals/RunControl propagate worker stops. New stage/process/action dispatch checks cancellation, and pending checkpoints/text reads cancel. The UI worker gets five seconds to publish before process-tree termination; uncancelled owned-helper cleanup and final incomplete reporting follow. Previously established failures retain precedence. Atomic interim HTML/JSON is generated through the production report pipeline at stage boundaries and about every two seconds during device work, using current saved worker/budget snapshots. Forced kill leaves the last complete snapshot explicitly partial.

Requirements v0.17, architecture v0.23, product v0.18, installation v0.22, diagnostic reporting, and development guidance are aligned. Existing offline test infrastructure covers long-history/current-ref memory, navigation cycles, untried paths, repetition authorization, scenario-only blocking, interruption flags/markers and adapter errors, checkpoint/process/stage cancellation, failure precedence, and partial/final report lifecycle. Two public-command checks use temporary fake runtimes to verify one SIGINT and forced termination without OpenAI or device access. Historical user reports, private YAML, application source, and device state are not changed. Real API/device acceptance remains a user-started run/replay.

Verification for this increment: 503 relevant offline checks passed (261 .NET unit tests, 207 Python unit tests, 13 runtime-policy checks, and 22 public CLI/lifecycle checks). These include actual SIGINT delivery to a temporary fake-runtime CIMT child, forced termination of a separate child after an interim report was saved, checkpoint cancellation, and a closed-pipe interruption race. The final host published successfully; installed host and all 12 changed/new runtime modules match the tested files byte-for-byte, and installed public help passed. Installed cimt.dll SHA-256: 97d66b943637304fef2bfef6f3a5fbf49ae7579480a8fa4318cec33ea44cf990. Original installation backup: /private/tmp/cimt-before-exploration-stop.7pl43htt. No real app run/replay, paid API request, device action, private configuration edit, or historical-report rewrite was performed for this increment.

## Compact AI input performance increment — 30 October 2026

Implemented the first measured execution optimization under FR-66/AC-40. ActionPromptBuilder sends compact recent-action navigation/outcome records and failed/overridden finding summaries, avoiding repeated full checks, old plans, and predictive prose. Original history is unchanged, and the complete catalogue/current decisions and exploration memory remain available to AI. Prompt guidance requests only new/changed assessments; no host-side finding suppression or result-policy change is introduced.

An offline comparison of the user's saved 15:04 UTC run measured the latest 24 history records at 46,184 serialized bytes before projection and 4,840 afterward (89.5% smaller for that portion). This does not establish total-request, billing, or wall-clock improvement. The same run's completed AI operations averaged 4.404 seconds and captures averaged 2.819 seconds; see performance.md for scope and nesting.

Requirements v0.18, architecture v0.24, product v0.19, installation v0.23, and the performance/development guides are aligned. Verification passed: 212 Python unit tests and 13 runtime-policy checks (225 targeted checks). Five new prompt-builder cases use the existing unittest infrastructure. No real app run/replay, paid request, device action, private configuration read/edit, historical-report rewrite, model change, or screenshot-check relaxation was performed.

Installation verification: the installed action_prompt.py matches the tested source byte-for-byte (SHA-256 c0e27c0ae6eceeb55166ae064ac2d353e427ab203935574bb16aaf725fcc35ee). The previous module is backed up at /private/tmp/cimt-before-compact-history.pzjfq7_7/action_prompt.py. No run was active during replacement. The host is unchanged; no real test run or API request was started.

## Configured model and Luna budget support — 30 October 2026

FR-23/FR-24 and AC-44 now cover selecting gpt-5.6-luna through the existing ai-model.name while retaining the Mini snapshot. Access checks and inference use the effective configured name without fallback. Budget settlement and full-context reservations include default cache-write and long-context charges; requests pin the priced 30-minute cache lifetime for the Luna profile. Ledger metadata and successful preflight identify the selected model. No new YAML fields or provider/admin credentials are introduced.

Requirements v0.19, architecture v0.25, product v0.20, installation v0.24, run-engine guidance and performance guidance are aligned. Automatic online pricing, ten-step cost queries, generic user-defined rates and multi-step plans remain deferred. No private YAML, historical report, application source or physical device is changed. Live Luna model access, quality and speed acceptance require a user-started run.

Verification for Luna support: 217 Python unit tests, 22 runtime-policy checks, and 22 existing public CLI/lifecycle checks passed (261 relevant offline checks). Fourteen new cases cover model selection and the additional pricing rules. The CLI fixtures use temporary simulated runtimes, without API or physical-device access. The installed budget.py, agent.py, and run_ui.py match the tested source byte-for-byte after checking /Users/Shared/CIMT/state/run.lock for active holders. Backup: /private/tmp/cimt-before-luna.dvwn2h8p. Installed SHA-256 values: budget.py 3505d8e685c158ad3fdc90dc7840fbd622b48ca85c3628ac30de2bf04f6b8b9f; agent.py d22efb9203517d9e80bf1e65f7e8ab75e9089fad2eeaa15b3cdc58dd01763760; run_ui.py 8cd657cf79544aecf4289e3ffff2a43afa79f43134757065d5dc740d498d3655. Host and private configuration are unchanged. No real app test, paid API request, or phone action was started.

## Per-execution replay report correction — 30 October 2026

FR-30/AC-45 reaffirm one timestamped report folder for each run and replay. Removed the shared-latest publisher, base redirection, root HTML output and cross-run latest link. RunEngine and RunReportWriter retain their original per-invocation reporting path. Replay build reuse still creates its own report, including both device results and relative evidence, without modifying earlier reports.

Kept clearer run/replay command and identity labels in HTML titles/headers. CommandSession also retains the parsed command for early error HTML/JSON. Updated the existing public replay fixture and replaced latest-page tests with focused per-execution report cases. Requirements v0.20, architecture v0.26, product v0.21 and installation v0.25 now describe the corrected contract. No private configuration or historical report is changed.

Verification for the corrected per-execution contract: 266 xUnit cases and 22 existing public CLI/lifecycle checks passed (288 relevant offline checks). The replay fixture verifies its own dated HTML command/identity and absence of a shared entry or HTML base. The corrected host published successfully; all six installed files match the tested publication, and installed public help passed. Installed cimt.dll SHA-256: 15c5fb853c15f7a81a556b92a76bab910d3a24e88cbc3c5e449f2725a68ba924. Backup: /private/tmp/cimt-per-run-install.UbVTdZ/previous-host.

Removed only the three shared reports/index.html files introduced by the previous update, from FirstRun, TestRun_SingleDevice_SingleTarget and TestRun_ios_android_SingleTarget. Verified timestamped report HTML hashes were unchanged. Python runtime, build worker/scripts, private settings, application source, and saved results remain unchanged. No real run/replay, model request or device action was started.


## Cancellation classification correction — 31 October 2026

FR-68/AC-42 now cover stopped activity/step reporting throughout nested interrupted operations. ActivityLog receives the shared user-stop state. ScenarioRunner retains a stoppingReason, and StepHtmlRenderer displays it without creating an action error. DeviceRunner saves the final observations even when closing the connection fails. Successful cleanup remains completed; non-interrupted adapter errors remain failures; earlier application/infrastructure outcomes keep their precedence. No historical report was rewritten.

Verified: 297 xUnit tests, 241 Python tests, 22 runtime-policy checks and 22 public CLI checks passed. The host published successfully. Installed the six host files and four changed runtime modules under the run lock, with backup and byte verification; see installation section 41. No new live app test or API request was made.

The product owner cancelled the additional startup-diagnostics fix; its edits were fully removed before publication/installation. Coverage counting is unchanged. Repeated-action and capture-speed corrections remain reviewed proposals, not implemented behavior; see the [focused review](reviews/2026-10-31-cancelled-replay-follow-up.md). Requirements v0.24, architecture v0.30, product v0.25 and installation v0.29 describe this scope.


### Host cancellation reporting follow-up

The host activity boundary now receives the run token so a pipe exception after user cancellation is logged as stopped before RunCoordinator handles it. Cleanup stays uncancelled, preserving genuine finalization failures. ExplorationMemory uses the saved interruption reason rather than claiming an observed unchanged/changed UI when observation did not finish. Earlier failure outcomes remain visible. General no-progress signatures, coverage counting and capture-speed behavior are unchanged.

Verification passed: 299 xUnit, 243 Python, 22 runtime-policy and 22 public CLI checks (586 offline checks). Host publication and installation of the six host files plus exploration_memory.py passed with lock, backup, byte verification and installed help. Requirements v0.25, architecture v0.31, product v0.26 and installation v0.30 describe the correction. No live test or API call was started; no prior report was rewritten.


## Separate Test Planning and Exploration layer — 31 October 2026

Implemented FR-82–FR-87 and the offline portions of AC-52–AC-55 as a separate runtime/test_planning package. TestPlanner owns the source-linked plan/map workflow without device/API/storage/report dependencies. A concrete instruction-derived objective or catalogue task is required before dispatch. Typed bounded updates preserve task/source identity. The layer retains input candidates, explicitly scoped paths, configuration-sensitive states, current-ref rebinding, verified direct return routes and no-progress counters that ignore known OS status indicators. Generic controls can be identified from current visible refs. A visited path never marks a test passed; checks retain requirement/override/failure precedence.

Execution provides observations and checks through the entry point and keeps one-action-at-a-time device control. Observation snapshots are saved before AI requests and after correction refreshes, so transport failures retain discovered work. A data-preserving restart action operates only on the verified tested app, with a cancellation boundary between termination and relaunch. HTML presents source-linked tasks, work status versus test result, scope explanations, states/transitions and last-observed configuration provenance. Existing redaction/masking, permission policy, budgets, crash handling, raw legacy coverage counters and historical reports remain authoritative. Current Mobile MCP execution remains; Appium switching and capture acceleration are not included.

Requirements v0.26, architecture v0.32, product v0.27, installation v0.31 and development guidance document the new boundary and behavior. The generic examples/test-planning inputs and README demonstrate focused language/configuration testing with normal commands. No new YAML field or key is required. Full-path/combination completeness and cross-run map reuse are not claimed.

Verified: 304 xUnit, 280 Python, 22 runtime-policy and 22 public CLI checks passed (628 offline checks). Published and installed 19 matching host/runtime files under the run lock with backups and byte verification; installed help, package import/schema smoke check and installer syntax checks passed. Live usefulness, configuration checks on real apps and browser layout remain qualification work; no new mobile test or paid API request was started. See installation section 42 for backup/hash details.


## AI-owned context and recovery corrections — 31 October 2026

Implemented FR-88–FR-94 and revised FR-66/FR-67. AI exclusively selects context relevance through summary/collection/address/range decisions, with null retaining its selection unchanged. Removed host last-N/field projections and task/state/path input windows. Full accepted decisions, masked observations, registered screenshots, checks and map records remain local. AI recall retrieves selected history without app actions; historical image bytes require explicit selection, registered digest verification and containment. Identical current/historical pixels share a payload. Evidence-name reuse does not overwrite earlier pixels.

Added a capacity-only 64 KiB selected-record package guard. It defers the entire oversized package with an explicit request for a smaller AI selection, rather than choosing a subset. AI can recall a revised selection or explain blocked remaining work. Actual provider context limits, shared spending/time limits and cancellation remain. Supported cache controls use an explicit stable-instruction breakpoint; provider token/cache details and request purpose are recorded without relaxing conservative cost enforcement.

Separated repetition/recovery from format correction. Every repetition signal or AI-detected loop pauses app actions, refreshes masked evidence and requests AI-directed recovery. AI may retrieve omitted evidence, replan, explain intentional work or finish blocked. Renewed loops request renewed assessment beyond three episodes; schema correction and crash limits remain separate. Valid checks from a non-dispatched repetition proposal are saved before refreshing evidence. Premature completion with unresolved work returns to AI reconsideration.

Fixed task/check identity after redaction using taskId and monotonic recorded check IDs. Historical checks cannot overwrite a new blocker. Structural paths remain stable through passive status changes while full UI observations remain recoverable. Configuration refinement preserves observed navigation and earlier known variants. HTML shows working memory, recovery decisions and available request usage. Requirements v0.27, architecture v0.33, product v0.28, installation v0.32 and the linked contract/example include the sequence diagram and acceptance mapping.

Offline validation: 307 xUnit tests, 318 Python tests, 22 runtime-policy checks and 22 fake-tool public CLI/lifecycle checks passed (669 checks). Installer shell syntax and Python compilation checks passed. The source is not installed by this increment. No new live mobile test, replay, device action or paid OpenAI request was started. Live usefulness, cost savings and browser-layout acceptance remain pending.
