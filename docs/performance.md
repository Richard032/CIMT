# CIMT execution performance

Updated: 30 October 2026. Scope: measured user-run baseline and the first runtime optimization.

## Measured baseline

The user-started replay report_2026-10-30_15-04-19-467 lasted 361 seconds including preparation/checkpoints and cancellation. The iOS target ran about 331 seconds. Its saved activity contains 27 completed AI decision operations (including a correction request), 28 accounted inference requests, and 26 tap operations plus a swipe. The API ledger records 413,765 input tokens and 11,512 output tokens. No new paid request was made to collect these measurements.

| Operation | Mean observed duration | Measurement scope |
| --- | --- | --- |
| AI decision operation | 4.404 seconds | 27 completed operations; can include correction |
| Masked capture/validation | 2.819 seconds | 29 captures; includes two UI reads and other checks |
| Tap execution operation | 1.498 seconds | 26 operations, including rejected attempts |
| Startup-state check | 0.786 seconds | 27 checks |

These durations are observed components, not independent benchmark guarantees. Capture is nested inside post-action observation, and raw tool timings must not be added again. Timing varies with UI state, device/tool response, network, model output, and corrections.

## First optimization: compact recent actions

The prompt previously repeated full check descriptions, expected behavior, unchanged unknown results, predictive prose, and earlier remaining-work lists inside each of 24 historical actions. The complete catalogue/current requirement results and exploration memory were already supplied separately.

ActionPromptBuilder now projects navigation facts and observed outcomes, retaining compact failed/overridden findings and credential aliases. It does not mutate the original records. Full findings, history, and screenshots remain in reports. AI guidance requests new assessments instead of repeating unchanged unknown results, while retaining catalogue coverage and explicit objective evidence.

An offline comparison reconstructed the latest 24 history records from saved steps and used the public prompt builder:

| History portion | Serialized bytes |
| --- | ---: |
| Previous full records | 46,184 |
| Compact input | 4,840 |
| Reduction | 89.5% |

The comparison uses the same JSON encoding for both versions. It measures the recent-history portion only, not the screenshot, full request, token bill, model quality, or live latency. No live speed-up percentage is claimed. The next user-started run/replay can compare AI operation duration, input/output tokens, useful control coverage, and total duration for comparable work. Different paths or a different action count are not a controlled timing comparison.

## Further opportunities

The measured capture and tap costs remain substantial. Device-query batching or persistent adapter connections need separate evaluation and instrumentation. The two UI reads around masking, fresh readiness checks, and crash evidence are retained. Fixed settling waits are a smaller part of the measured run and can increase capture retries if reduced without a stable-screen policy. Model changes or multi-action plans need separate quality/cost evaluation. None of these additional changes is included in this increment.

## Optional configured Luna comparison

The validated pricing profiles now include gpt-5.6-luna. Operators can select it through the existing ai-model.name; installation does not change private input files. Access checks and inference use the selected model without fallback. Standard service tier, low reasoning effort, and the 2,048-token output cap remain in place. The Luna request fixes the default 30-minute cache lifetime so accounting includes the correct cache-write bound. Strict shared budget enforcement includes long-context charges and uncertain usage.

Luna support is an alternative for user-started evaluation, not a demonstrated speed or quality improvement. Compare total time, distinct paths, repeated navigation, rejected decisions, findings, and cost on equivalent app states. The earlier 89.5% reduction measures only compact history on a saved Mini run. No live Luna inference or device comparison was performed.
