# Readable run diagnostics

Updated: 30 October 2026. Scope: FR-61–FR-69 and AC-35–AC-43 for run/replay execution reports.

## Reading the report

### Approved usability design

The report now uses Overview, Findings, Devices, Requirements and Activity, in that order, with wide-screen sidebar navigation and wrapping navigation on narrow screens. Overview shows every known expected/observed device-target outcome before logs. Confirmed crash occurrences and suspected terminations remain separate; fixed host crash-kind values are treated as typed classifications during redaction. Mandatory failure cards include available expectations, observations and evidence links even when optional details are disabled. Failed requirement assessments without duplicate check records are also readable.

Device/scenario/record anchors are distinct. Visible step IDs are copied from saved data, including zero; an ambiguous duplicate cannot silently resolve to a different record. Findings and requirement results link unique steps. Steps label decision observations, actual outcomes, errors and recovery separately. Remaining plans retain their worker scope; future requests identify the current platform/device/target. Historical contradictory plans are not hidden or rewritten.

Each applicable section has local filters/search, selected-scope and shown/total text, clearing and empty-state behavior. A deep link opens ancestor disclosures and clears conflicting filters. Overview totals remain whole-run values. Contained PNG links open an optional native-dialog viewer with scenario/type grouping, saved-step image order, zoom, keyboard/Escape and focus return. Ordinary relative links and all main content remain available without JavaScript. Missing files and escaping paths/symlinks are explained.

Compact activity groups operation/context/status counts without assuming event pairings; the full ordered journal remains available. Time/duration and budget fields are readable, with exact records/downloads retained. The renderer embeds its fixed stylesheet/script in each report; no server, network dependency or changed output-folder contract is introduced. Early command/readiness/error reports use the same presentation shell and explicitly state that no app testing occurred. Historical reports are not regenerated.

See the approved [design proposal](reviews/2026-10-30-html-report-design-proposal.md), FR-70–FR-76 and AC-46–AC-50. Static/unit verification does not establish browser layout, keyboard/screen-reader conformance or the proposed ten-second/two-action usability targets. Those manual acceptance checks remain to be performed on representative reports.

The run header identifies command outcome, run, branch, and source commit. The mandatory Run overview shows UTC start/finish and elapsed seconds, target labels and actual build configurations, startup devices, app builds available, and the recorded AI inference count. An unavailable count is stated explicitly. Replayed artifacts retain their original source identity and build provenance.

Failures and stopping reasons show the actual saved device error, cancellation of another worker, limits/device stops, functional failures, and unresolved work. An infrastructure or masking failure does not prove an application crash. Install/reset/launch commands are preparation, not passed application tests. The existing verdict, completion, exit precedence, and requirement coverage still determine the outcome.

Each started scenario saves the latest redacted AI remaining-work list before check recording and limit handling. Finalization preserves that list after errors, adds known unresolved requirement/control counts without duplicate summaries, and publishes it for HTML and JSON. An incomplete scenario with no specific pending tasks states that testing has not finished and coverage is unconfirmed. Later plans replace older plans; explicit completion clears obsolete tasks. These lists describe recorded work, not a fabricated inventory of hidden screens. Targets never started remain visible in requirement coverage rather than invented scenario records.

Chronological activity lists timestamp, operation, status, context, available duration, message, and exception/log details. Device operations may overlap. A started operation without a matching outcome was interrupted or has no recorded completion. An Execute target operation completing means that invocation returned; the objective's verdict/completion and remaining work must still be reviewed. The same distinction applies to completed host stages that recorded individual build failures.

All three sections remain visible when optional report details are disabled. Exact errors are readable without opening raw JSON. Exception locations are expandable. Related log links are relative to the report and cannot escape it. Raw adapter/native diagnostic files remain available through their existing report locations; arbitrary raw UI/adapter responses are not copied into the activity timeline.

## Saved files and terminal output

activity.jsonl contains incrementally appended JSON records from the host and device workers. Fields are timestamp, operation, status, message, target, platform, device, durationSeconds, log, exceptionType, and details. Timestamps are UTC; duration uses a monotonic clock for operations. Each worker keeps its own context, and shared worker writes use one lock. The final report orders records by timestamp. A malformed/truncated record produces an explicit warning without discarding earlier entries. No activity is fabricated for an old report without a journal.

result.json adds activity, stoppingReasons, and durationSeconds. logs/execution-worker.log contains redacted captured worker output. Empty stderr does not hide device errors from ui-results.json. Structured activity lines appear live in the terminal; private stdin requests and arbitrary process output are not displayed through that channel. Full generic Git/build output streaming under FR-54/FR-55 remains separately tracked.

Free diagnostic messages and exception locations are redacted before storage/display and HTML-escaped for the page. Typed host metadata remains distinct from secret-bearing text, preserving timestamps, statuses, IDs, numbers, and evidence paths even with short secret values. No prompts, API payloads, credential values, local-variable dumps, raw screen text, or unmasked screenshots are added. Changed-mask errors may include up to ten before/after redacted identifiers and coordinate tuples plus total region counts. Screen-size errors include before/after dimensions. Rejection and stopping rules are unchanged; no retries or masking bypasses are introduced.

## Verification

The existing .NET unit-test project exercises overview metadata, failure/cancellation explanations, timeline ordering, partial records, disabled optional sections, escaping/redaction, path safety, saved-worker errors with empty stderr, and final JSON. Python unittest cases exercise durations, original exception propagation, redaction of terminal/journal messages, separate cancellation/limit statuses, concurrent appends, a fake device failure, and adapter setup failing before device execution starts. CaptureGuard tests check geometry-only diagnostics without UI values. The existing public-command fixtures check mandatory report sections and failed-build activity.

Checks use synthetic inputs, fake services, and local files. They do not establish real device/app acceptance. Existing report folders and private YAML are not rewritten; richer reporting starts with new runs/replays after installation.

Earlier diagnostic increment: 442 checks passed in the existing offline suites. That host and all 29 runtime modules were installed and byte-verified. The synthetic demo passed structure/content checks; visual inspection was blocked by the browser local-file URL policy. No real app or device test was started.

Approved usability increment: 548 relevant offline checks passed (286 xUnit, 218 Python unit, 22 runtime-policy and 22 public CLI/lifecycle). Script syntax, report anchor/link integrity after relocation, four synthetic PNGs and fourteen static text/background color pairs were checked. The final host and scoped worker module were installed and byte-verified; public help passed. Browser layout, keyboard/screen-reader qualification, text-enlargement behavior and user-timing measurements remain open. The runnable two-platform example is [requirement mapping](../examples/requirement-mapping/README.md); its expected exit 1 describes synthetic failures, not a real app test.

## Screenshot transition retries

New captures can retry a valid screen/mask-region transition at most three times, with 250 ms waits inside the run deadline. The timeline identifies discarded attempts without raw UI text or pixels. The final accepted masked image follows the existing evidence links and HTML step display. If all attempts fail, the report keeps the underlying evidence error and explicitly says that no verified screenshot was saved. This supersedes the earlier no-retry description for transient valid geometry changes; invalid geometry, image, device, and tool failures still stop immediately. Historical missing screenshots are not reconstructed.

## Unaccepted AI responses

For FR-65/AC-39, each rejected candidate is retained under its scenario as rejectedResponses, separately from checks and executed steps. Every entry contains its attempt, decision-step context, redacted validation error/candidate, and the already masked screen used for that decision, or an evidenceError. Candidate fields are untrusted data: even source, status, and requirementId are redacted. Raw provider envelopes, private requests, prompts, and unmasked images are not added. This is a diagnostic record, not a verified finding or hidden reasoning.

The mandatory HTML section exposes these candidates even with optional details disabled. A failed observation in an unaccepted response remains inspectable after successful correction; it does not automatically fail the app or disappear from history. Previously accepted failures remain effective. Rejection and successful recovery appear in chronological activity with attempt and device/target context. Exhaustion is an explicit AI response-correction infrastructure error; other workers retain their separate cancellation reasons. Rejected remaining-work lists do not replace the last accepted plan.

## Exploration outcomes and interrupted runs

Step details show the selected control and the observed UI outcome after execution, including rejected coordinates or unavailable evidence. Saved exploration memory includes all known control paths, attempts, transitions, and the accepted pending plan. It does not claim every observed change is a functional pass. Current-control, pending-path, and stalled-path summaries help the next AI decision continue the scenario. No-progress proposals are retained as unaccepted diagnostics; exhausted no-progress replanning leaves the scenario incomplete without cancelling unrelated work.

The host catches Ctrl+C/SIGTERM and records User interruption separately from infrastructure failure. It keeps earlier findings and applies normal exit precedence. Interim index.html and result.json are written through the same production rendering/redaction pipeline at stage boundaries and about every two seconds during UI execution. The JSON inProgress/updated fields and HTML partial marker identify snapshots; finished remains null until finalization. Latest budget data is read from ai-budget.json, including pending reservations when an API request has not settled. Each file is replaced atomically. A force-killed process leaves the preceding complete snapshot, which is explicitly not a confirmed final result. Existing reports are not retroactively regenerated.


## Cancellation messages — 31 October 2026

Host stages and nested device operations use the known user-stop state before logging an exception. An adapter/process pipe closing during cancellation is reported as stopped with User interrupted execution, instead of a new failed operation. An interrupted action/observation retains that stopping reason and cannot claim observed UI change or no change without a completed observation. Previously recorded crash/action failures retain their priority. Successful cleanup still completes; a genuine cleanup failure or a pipe failure without user cancellation remains an error. This uses existing cancellation state and saved observations, without additional diagnostic collection or evaluation. Existing reports are preserved.
