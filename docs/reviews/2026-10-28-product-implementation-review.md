# CIMT product and implementation review

Date: 28 October 2026, Europe/Zurich. Reviewed local source corresponding to commit 552506d65132eb3aa58012f42c7c4c5062520d0f. The original review below is followed by a defect-resolution record. It is not release approval.

## Assessment

CIMT is an engineering prototype with an initial exploration engine. It is not yet ready to produce trusted daily-testing or nightly Jenkins verdicts. The product definition covers the intended workflow, but the current code implements only part of it and contains correctness defects.

The last refactor improved readability and separated several useful boundaries. It did not establish that the product behaves correctly. I reran all 91 existing checks successfully, then reproduced six defects with isolated synthetic inputs. No OpenAI request, application build, or physical-device operation was used for this review. The iPhone is currently unavailable; iPhone acceptance remains pending.

P1 means fix before relying on test results or credential handling. P2 means an important implementation or maintainability problem to fix before release. Documented unfinished features are listed separately from defects.

## Confirmed implementation defects

### R1 — P1: functional failures can be reported as passed

Location: runtime/scenario.py, lines 199–212; runtime/action_prompt.py, lines 8–23.

The final scenario verdict is failed only when the crash list is nonempty. Otherwise, complete exploration becomes passed. There is no structured result for a failed functional check. The model can describe a violation in its observation, but that does not affect the verdict.

Reproduction: complete an objective with no outstanding controls, no crashes, and the observation “FAIL: saved seat value is lost after reopening; requirement is violated.” The result is passed.

Impact: testing a bug description or requirements can produce a false pass. This conflicts with FR-19, FR-27, and FR-31. Completing navigation does not prove expected behavior.

Suggested change: introduce a small explicit check-result model and a pure verdict policy. Keep execution completion separate from check success. Record each supplied requirement's status and evidence, including overridden and not-tested results.

Simple tests: successful check; failed check without crash; inconclusive check; requirement overridden by instructions; failure followed by a limit.

### R2 — P1: a new sensitive field can escape screenshot masking

Location: runtime/screen_capture.py, lines 36–45 and 63–69.

UI elements are read before the screenshot. The code reads elements again only when the first list already contains a sensitive element. If a password screen appears between that first read and image capture, the screenshot can contain sensitive content while masking still uses the old empty/non-sensitive list.

Reproduction: return no sensitive elements on the first UI read, then a screenshot containing a configured Password field. A second UI read would identify the field. The current code makes only one UI read and returns the field's pixels unchanged.

Impact: the image can later be stored and sent to AI without the required mask. This conflicts with FR-36 and AC-23. This was a synthetic reproduction, not an observed disclosure of a real credential.

Suggested change: verify both the presence and geometry of sensitive fields across capture, including transitions from a non-sensitive screen. Discard evidence and stop when reliable masking cannot be established.

Simple tests: unchanged sensitive field is masked; field moves and capture stops; sensitive field appears during capture and no image is returned.

### R3 — P1: screenshot failure discards an already detected crash

Location: runtime/crashes.py, lines 139–145; runtime/scenario.py, lines 82–85.

CrashRecovery observes native crash evidence, then takes and saves a screenshot before recording the crash. If capture fails, the method raises before appending the crash or the performed step. Device handling records an infrastructure error, but the known test finding is missing.

Reproduction: the monitor returns a matching crash diagnostic, then snapshot raises an evidence error. The stored crash count remains zero and the scenario remains inconclusive.

Impact: the report can lose the exact bug CIMT was asked to find. The final exit may correctly indicate infrastructure failure, but the test verdict still needs to retain the known failure. This conflicts with FR-21, FR-28, FR-29, and the separate verdict/completion rules.

Suggested change: record and publish the finding and action before optional evidence capture. Record capture failure separately. Preserve failed + incomplete when infrastructure failure takes precedence.

Simple tests: crash with screenshot; known crash with failed screenshot; screenshot failure without a known crash.

### R4 — P2: native command failure raises AttributeError

Location: runtime/device_commands.py, lines 15–21 and 38–41.

NativeDevice.native calls self.redactor.text on a nonzero result, but the constructor never sets self.redactor.

Reproduction: a fake native process returns exit 1. The observed exception is AttributeError rather than InfrastructureError.

Impact: the original device problem is hidden. Callers that treat unavailable crash diagnostics as recoverable do not catch this different exception, so it can stop the run instead.

Suggested change: provide the error-redaction dependency directly, or use a safe generic error. Keep error classification predictable.

Simple tests: successful native JSON; nonzero native result; invalid JSON; process timeout. Each test needs one simple fake process result.

### R5 — P2: replacement-script YAML fallbacks are not honored

Location: src/Cimt/Execution/ApplicationBuilds.cs, lines 47–68 and 79–86.

The default build worker has fallback logic, but the public orchestration does not merge a replacement script's result with platform YAML. It rejects missing result metadata before applying configured artifact/app-id values. A successful script without a result file is also treated as failed even when YAML supplies both fields.

Reproduction: configure an existing YAML artifact path and app-id, then have a successful script return JSON containing only app-id. The run rejects it as invalid artifact metadata rather than using the configured artifact.

Impact: an explicitly approved custom-script workflow fails. The exception also leaves the normal target-build loop, preventing subsequent targets from being attempted in this case. This conflicts with FR-43, the product guide's per-field precedence, and AC-21.

Suggested change: resolve each result field using script metadata first and YAML for missing values, then validate the resolved result. Resolve YAML artifact paths from the clone root.

Simple tests: complete script result; artifact from YAML; app-id from YAML; both fields from YAML; unusable resolved metadata.

### R6 — P2: a helper-stop exception prevents clone deletion

Location: src/Cimt/Execution/WorkDirectoryManager.cs, lines 90–102.

The owned folder is removed after the helper-stop process call. If that call throws, folder removal is never attempted. The coordinator reports a cleanup error, but the clone remains despite the filesystem being usable.

Reproduction: create a correctly owned work folder and use a fake helper-stop command that throws. The work folder remains.

Impact: failed runs can retain source clones unnecessarily. This conflicts with FR-08. A later successful run may recover it, but that does not make this cleanup path correct.

Suggested change: handle helper shutdown and owned-folder removal independently. Attempt owned deletion even when helper shutdown fails, while preserving both errors.

Simple tests: helper stop succeeds; helper returns an error; helper throws; owned deletion itself fails.

## Design and test review

### R7 — P2: the scheduling unit test is too complicated under the new rules

Location: tests/test_runtime_components.py, lines 309–359; runtime/run_ui.py, lines 22–75.

The scheduling test combines a thread barrier, lock, shared counters, nested factory/functions, runtime method replacement, temporary report files, and a complete execution context. It also combines three concerns: using all devices, limiting concurrency, and report production.

This violates the new instruction to simplify source when a unit test needs advanced code, then split the behavior into simple cases if needed. The problem is broader than method length: scheduling is still tested through composition, real threading, and reporting together.

Suggested change: separate queue/scheduling decisions from thread execution and file reporting. Use simple cases for one device, two devices, a queued third device, and a worker stopping. Keep any real concurrent stress check clearly separate from the small unit tests. Avoid adding a generic framework or proxy layer.

Other concerns:

- Several operational results are still untyped dictionaries. Missing fields and wrong response shapes can fail late. Small records for check/scenario/build results would make the contracts clearer.
- The current tests concentrate on selected policies and successful fakes. They missed the six error paths above. Test count should not be used as a measure of product completion.
- The repository AGENTS.md does not yet contain the two latest rules about complicated unit tests. The development guide should also record them.
- Comments and service names are clearer than before. Continue that style, but judge responsibility by what a class owns, not by its line count alone.

## Remaining product and operational gaps

| Area | Current implementation | Gap against the approved product |
| --- | --- | --- |
| Requirement evaluation | Requirements are passed as text and shown in the report. | No complete set of per-requirement statuses/evidence or explicit conflict results: FR-19/27, AC-09. |
| Scenarios | One objective per target/device. | Explicit scenario boundaries, reset between individual scenarios, and continuing independent work after equipment blocks are not implemented: FR-14/15/17. |
| Replay | Command is recognized but returns an unimplemented error. | Adaptive replay and its demonstrations remain missing: FR-22/48, AC-18/19. |
| Setup | Pilot prerequisite helpers exist; cimt setup is unimplemented. | Manifest-driven reusable provisioning, replacement/resume behavior, and second-Mac proof remain open: FR-33/34/50. |
| Interrupted runs | Ownership markers support cleanup during a later run. | No graceful cancellation handler or retained previous-report link/interruption record; recovery is reached through run preparation rather than every launch: FR-08/38, AC-12/16. |
| Run identity | Work and report names use independently generated times; work adds a random suffix. | They do not share the required timestamp: FR-30, AC-22. |
| Real app/device acceptance | Helper control probes and simulated execution checks exist. | The reviewed run engine has not completed a real signed MAUI build/install/reset/exploration workflow. The iPhone is unavailable. |
| Jenkins and portability | Public CLI is intended for both terminal and Jenkins. | No completed nightly pipeline, second-Intel-Mac, or portable report acceptance demonstration. |

The limitations are partly disclosed in the status documents. They should remain explicit release blockers, rather than be presented as completed behavior. Some product-guide sections still say the run engine is pending even though later sections describe its implementation; consolidate current status separately from historical records.

## Suggested order of work

1. Fix false verdicts, masking transitions, and crash-evidence preservation. Add the small cases listed above first.
2. Fix native error handling, build-result fallback resolution, and cleanup after helper exceptions.
3. Simplify the scheduling test and its source boundary under the updated AGENTS.md rules.
4. Add scenario and requirement-result contracts before extending replay or increasing exploration complexity.
5. Run one real Android path through the public command, then restore iPhone access and qualify iOS. Complete Jenkins and second-Mac proof before release acceptance.

Keep the approved product definition. These findings call for implementation fixes and completion of the agreed scope; they do not justify silently reducing requirements.

## Verification record

- Existing suite: 36 .NET unit tests, 32 Python unit tests, 18 CLI/lifecycle regression checks, four simulated build-contract checks, and one MSBuild adapter fixture: all 91 passed.
- Additional isolated review reproductions: six defects confirmed, as described in R1–R6.
- Review reproduction files: /private/tmp/cimt-review-20261028/reproduce.py and HostProbes/Program.cs under that folder.
- Existing-suite log: /private/tmp/cimt-review-20261028/baseline-checks.log.
- Implementation, private configuration, and deployed application data were not changed. Only this review document was added to the project.

## Resolution record — 28 October 2026

The original findings above describe the reviewed snapshot, not the corrected source. The fixes keep the approved requirements and public command/YAML interface.

| Finding | Correction | Regression evidence |
| --- | --- | --- |
| R1 | Structured checks carry expected/observed behavior and status. Failed checks affect scenario, worker, host, and HTML outcomes. Navigation alone cannot pass. Findings survive a limit reached during the model request. Later evidence can resolve an unknown check; failures remain recorded. | test_defect_policies.py, test_runtime_components.py, OutcomeTests.cs, CheckReportTests.cs. Full per-requirement inventory remains release work. |
| R2 | Capture always compares sensitive-field presence and positions before and after the screenshot. A change stops image return. | Appearing, disappearing, moving, unchanged-sensitive, and unchanged-clear screen cases. |
| R3 | Crash findings are published before capture/storage; evidence errors are separate. The action is retained if capture or recovery fails. Startup storage failure follows the same rule. | Capture/storage failures with a known crash, capture failure without a crash, startup storage failure, and scenario action persistence. |
| R4 | NativeDevice receives its redactor in the constructor. | Successful JSON, redacted nonzero result, invalid JSON, and timeout. |
| R5 | A pure resolver applies script-first, YAML-for-missing precedence per field. The host accepts no result file when YAML provides both values. Invalid metadata is recorded per target. | BuildResultTests.cs and BuildIntegrationTests.cs: complete/partial/missing metadata and an invalid target followed by a successful target. |
| R6 | Helper shutdown and owned-folder deletion are independent attempts. The ownership guard remains mandatory. | Successful stop, nonzero stop, thrown stop error, and changed ownership token. |
| R7 | DeviceScheduler submits work to a bounded executor. Simple recording services test submission separately from real threads and reports. Both test-complexity rules are in AGENTS.md and the development guide. | Separate zero-, one-, two-, and three-device cases. These verify the two-worker submission contract, not physical-device concurrency. |

Final offline verification: 62 .NET unit tests, 64 Python unit tests, 18 CLI/lifecycle checks, four build-contract simulations, and one MSBuild example fixture passed: 149 checks. The full log is local at /private/tmp/cimt-defect-fix-checks-20261028.log. No paid API request, real MAUI build, physical-device operation, or private-configuration read occurred.

These corrections close R1–R7 for the tested paths. They do not close the release gaps listed above. The iPhone remains unavailable, and a real application run remains necessary before relying on the product for daily or nightly verdicts.

## Follow-up — complete requirement mapping increment

The catalogue/mapping gap listed in the original review is now implemented for the tested paths. The host preserves every nonblank source item with text, ID, line references, and a redacted-source fingerprint. Checks reference known IDs, overrides retain an actual instruction quote, and final coverage includes every applicable configured target/startup-device pair. Failed builds and unstarted/locked devices retain explicit unresolved results. Unresolved scopes keep completion incomplete even when another scope failed.

The [mapping contract](../requirement-mapping.md) documents deterministic source grouping and compound-item interpretation. It does not claim semantic scenario decomposition or real application acceptance. The [offline demonstration](../../examples/requirement-mapping/README.md) exercises all five statuses through the real catalogue/report services with synthetic observations. Other release gaps in this historical review remain open.

Mapping verification: 99 .NET and 87 Python unit tests plus 23 regression/contract checks passed (209 total). The five-status synthetic demo passed its report checks with expected exit 1/incomplete completion. Real-app acceptance remains pending.
