# Readable run diagnostics

Updated: 30 October 2026. Scope: FR-61–FR-64 and AC-35–AC-38 for run/replay execution reports.

## Reading the report

The run header identifies command outcome, run, branch, and source commit. The mandatory Run overview shows UTC start/finish and elapsed seconds, target labels and actual build configurations, startup devices, app builds available, and the recorded AI inference count. An unavailable count is stated explicitly. Replayed artifacts retain their original source identity and build provenance.

Failures and stopping reasons show the actual saved device error, cancellation of another worker, limits/device stops, functional failures, and unresolved work. An infrastructure or masking failure does not prove an application crash. Install/reset/launch commands are preparation, not passed application tests. The existing verdict, completion, exit precedence, and requirement coverage still determine the outcome.

Chronological activity lists timestamp, operation, status, context, available duration, message, and exception/log details. Device operations may overlap. A started operation without a matching outcome was interrupted or has no recorded completion. An Execute target operation completing means that invocation returned; the objective's verdict/completion and remaining work must still be reviewed. The same distinction applies to completed host stages that recorded individual build failures.

All three sections remain visible when optional report details are disabled. Exact errors are readable without opening raw JSON. Exception locations are expandable. Related log links are relative to the report and cannot escape it. Raw adapter/native diagnostic files remain available through their existing report locations; arbitrary raw UI/adapter responses are not copied into the activity timeline.

## Saved files and terminal output

activity.jsonl contains incrementally appended JSON records from the host and device workers. Fields are timestamp, operation, status, message, target, platform, device, durationSeconds, log, exceptionType, and details. Timestamps are UTC; duration uses a monotonic clock for operations. Each worker keeps its own context, and shared worker writes use one lock. The final report orders records by timestamp. A malformed/truncated record produces an explicit warning without discarding earlier entries. No activity is fabricated for an old report without a journal.

result.json adds activity, stoppingReasons, and durationSeconds. logs/execution-worker.log contains redacted captured worker output. Empty stderr does not hide device errors from ui-results.json. Structured activity lines appear live in the terminal; private stdin requests and arbitrary process output are not displayed through that channel. Full generic Git/build output streaming under FR-54/FR-55 remains separately tracked.

Free diagnostic messages and exception locations are redacted before storage/display and HTML-escaped for the page. Typed host metadata remains distinct from secret-bearing text, preserving timestamps, statuses, IDs, numbers, and evidence paths even with short secret values. No prompts, API payloads, credential values, local-variable dumps, raw screen text, or unmasked screenshots are added. Changed-mask errors may include up to ten before/after redacted identifiers and coordinate tuples plus total region counts. Screen-size errors include before/after dimensions. Rejection and stopping rules are unchanged; no retries or masking bypasses are introduced.

## Verification

The existing .NET unit-test project exercises overview metadata, failure/cancellation explanations, timeline ordering, partial records, disabled optional sections, escaping/redaction, path safety, saved-worker errors with empty stderr, and final JSON. Python unittest cases exercise durations, original exception propagation, redaction of terminal/journal messages, separate cancellation/limit statuses, concurrent appends, a fake device failure, and adapter setup failing before device execution starts. CaptureGuard tests check geometry-only diagnostics without UI values. The existing public-command fixtures check mandatory report sections and failed-build activity.

Checks use synthetic inputs, fake services, and local files. They do not establish real device/app acceptance. Existing report folders and private YAML are not rewritten; richer reporting starts with new runs/replays after installation.

Final verification: 442 checks passed in the existing offline suites. The tested host and all 29 runtime modules were installed and byte-verified. The synthetic demo passed structure/content checks; visual inspection was blocked by the browser local-file URL policy. No real app or device test was started.
