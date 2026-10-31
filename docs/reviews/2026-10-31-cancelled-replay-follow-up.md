# Cancelled replay: focused follow-up review

Date: 31 October 2026

Source: saved replay report_2026-10-31_06-48-22-356, its activity journal, redacted UI snapshots, and the current CIMT/installed adapter code. This review made no paid AI requests and started no new device test. Durations describe this run only.

## Approved scope

| Item | Decision | Result |
| --- | --- | --- |
| 1. Underlying startup diagnostics | Cancelled by the product owner | All new diagnostic-collection edits removed before publication/installation. Existing diagnostic behavior remains. |
| 2. Repeated actions | Review a possible fix | Recommendation below; no exploration change implemented. |
| 3. Coverage counts | Ignore | No coverage/counting change. |
| 4. Cancellation messages | Fix | Interrupted operations and steps show stopped, while genuine failures and earlier findings are retained. |
| 5. Slow capture | Review a possible fix | Recommendation below; no capture/action optimization implemented. |

## 2. Why actions repeated

The Android history contains six taps on Choose Location (steps 31–33 and 37–39) and three on Personal (41–43; the last capture was interrupted). The registration screen remained blocked by required account/passcode/captcha validation. There was no recorded no-progress replan.

ExplorationMemory compares every UI element to decide whether an action changed the screen. In saved adjacent snapshots, 31→32 changed only the SystemUI mobile signal element; 32→33 changed clock/signal; 37→38 changed the clock; 38→39 changed the signal element. Those changes reset the unchanged-attempt counter despite no useful app progress. Snapshots 41→42 had no UI differences. The separate repeated-path safeguard had not yet reached its blocking threshold before navigation changed the path.

The tapped registration tabs are android.view.View entries with only ref, type, text and coordinates in the saved normalized UI. No clickable flag, role, action list or enabled flag is available there. CoverageTracker.is_control does not recognize this generic type; ExplorationMemory reuses that predicate for its current-control summaries. Its path label also omits the text fallback, so the saved label is merely tap. These observations explain gaps in the memory given to AI; they do not establish that every generic view is an actionable control.

Recommended smallest correction, for a separate approved change:

1. Give exploration its own progress comparison. Exclude narrowly identified status-bar clock/signal entries while retaining app text, validation messages, modal changes and OS permission dialogs. Do not filter all SystemUI entries or change coverage keys/counts.
2. Keep per-view/per-control attempt counts stable across those status updates. Preserve the existing three-attempt rule and bounded replan path; no extra AI evaluation is needed.
3. Include text in remembered path labels. Keep generic views already selected by AI visible in the relevant exploration summary. Do not classify every android.view.View as a button. A wider actionable-view rule needs trustworthy adapter metadata first.

Verify with simple existing-project tests: clock/signal-only changes cannot reset no-progress; real validation/dialog/navigation changes remain observable; ref changes bind to the same control; explicit repeat instructions still work; the fourth unchanged attempt requests a replan. Keep coverage counting untouched, as requested.

Risk: an overly broad OS filter could hide a real permission dialog or keyboard transition. Use exact status-bar identities and retain the original UI evidence. Observed UI change remains an observation, not a functional pass.

## 4. Cancellation correction

The saved run correctly retained the earlier iOS failure and produced final HTML/JSON. However, adapter shutdown during capture produced failed/Broken pipe activity rows before the final user-stop reason. Classification happened only at the device boundary, after nested activities had already logged failures.

ActivityLog now shares RunControl's user-stop state and reports exceptions during that known interruption as stopped with the existing interruption reason. This also covers nested operations. It does not prevent cleanup or rewrite saved activity. Successful cleanup remains completed. ScenarioRunner saves a stoppingReason instead of inventing a new actionError for the interrupted action, and HTML displays that reason. An earlier crash label retains precedence. DeviceRunner always attempts final publication after connection closure, handles close errors, and preserves the original device error if cleanup also fails.

Without a known interruption, pipe/adapter errors remain real failures. Earlier application failures retain exit 1; earlier infrastructure failures retain exit 3. Interrupted incomplete work alone retains exit 2. No crash detection, evaluation, masking, budget, coverage or retry rule was added. This cannot guarantee finalization after a force kill or an unavailable filesystem.

## 5. Where execution time went

Completed Android activity rows from this replay:

| Operation | Count | Mean | Median |
| --- | ---: | ---: | ---: |
| Capture and validate masked screenshot | 33 | 15.115 s | 14.590 s |
| List UI elements | 69 | 6.845 s | 6.783 s |
| Tap tool call | 30 | 6.342 s | 6.776 s |
| AI action request | 32 | 3.850 s | 2.874 s |

UI calls are nested inside captures; do not add these rows as independent costs. A capture checks readiness and dimensions, reads UI, obtains a lossless PNG, reads UI again, verifies sensitive regions/dimensions, checks readiness again, then masks. Two roughly 6.8-second UI reads account for much of a roughly 15.1-second capture.

The installed MCP adapter launches mobilecli for each command. UI listing uses dump ui. A ref tap uses io tap @ref; the installed adapter's double-tap implementation explicitly documents that ref taps dump UI again. This is a plausible reason tap latency resembles UI-read latency, but the journal does not measure the native dump separately. There is no evidence here that removing MCP alone would remove the delay, or that model choice is the main bottleneck.

Recommended next investigation, without changing execution policy:

1. Compare a native UI dump with the MCP UI call on the same stable screen, recording durations only. Separate process startup, native UI enumeration and transport costs. Measure serially and with the normal maximum of two workers to identify resource contention. This measurement remains pending.
2. If native enumeration dominates, evaluate a supported persistent native/helper connection or an upstream UI-dump optimization. If wrapper overhead dominates, consider a CIMT adapter method calling the same native operation directly, after verifying identical element normalization and valid refs. Do not edit third-party source silently.
3. Treat coordinate taps as a separate tradeoff: they may avoid ref-resolution dumps, but coordinates from before an AI request can become stale. Do not switch all ref taps to coordinates without an explicit freshness/target validation policy, especially for credentials and permission dialogs.
4. Retain both sensitive-region checks, dimension/orientation checks, readiness checks, PNG masking and current action/crash evidence. An atomic UI/image backend could reduce reads only after equivalent guarantees are demonstrated. No such capability is established in this review.

First recommendation: measure the native boundary before selecting a transport rewrite. Keep the configured model and current evidence policy. Do not promise a speed-up percentage from these component timings.


### Cancellation follow-up: host stages and observation wording

A second review found the Python worker classification was fixed, but host RunActivityLog.Run still logged an IOException as failed before RunCoordinator recognized user interruption. Host stages now receive the cancellation token and log stopped with the known interruption reason first. Cleanup remains uncancelled so actual finalization failures are preserved. ExplorationMemory also retains the interrupted step reason instead of generating an observed-unchanged result from a stale screen. Recorded crash/action failures retain priority. The broader repeated-action and speed proposals above remain unimplemented, and no additional startup diagnostic collector was added.


### Approved planning implementation

The product owner subsequently approved instruction/requirement-driven planning and required it as a separate layer. The Test Planning and Exploration package implements that increment, including known status-indicator filtering, source-linked path scope, current-ref generic-input discovery, configuration-sensitive states and persistent tasks. See architecture section 31 and FR-82–FR-87. Legacy coverage counters and capture timing/checks are unchanged. The earlier additional startup-diagnostics item remains cancelled. Appium adapter replacement and capture-speed work are not part of this implementation.
