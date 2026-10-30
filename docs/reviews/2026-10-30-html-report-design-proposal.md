# HTML report design proposal

Date: 30 October 2026  
Product: CIMT — Curtis Intelligent Mobile Test  
Status: proposed for review; production rendering and approved requirements are unchanged

## 1. Purpose

A developer should quickly understand what happened, on which device and build target, and where to inspect the evidence. The report must also support a detailed investigation without making every reader work through the execution log.

This proposal resolves the presentation gaps in the [gap analysis](2026-10-30-html-report-usability-gap-analysis.md), using the refinements from the [Apple and Tesla comparison](2026-10-30-apple-tesla-report-design-comparison.md). It specifies behavior for a future implementation. The accompanying interactive design preview uses selected facts from the reviewed replay; it is not a regenerated report or a complete evidence browser.

## 2. Recommended layout

Use a restrained desktop layout with a small left navigation area. At narrower widths, move the same labelled navigation above the content and allow it to wrap. Keep all sections available. A horizontal navigation alternative is included in the design preview for comparison; the recommendation is the sidebar on wider screens.

The header identifies CIMT, the command, the exact run identity and the report state. Below it, use five sections:

| Section | Main question answered | Default content |
| --- | --- | --- |
| Overview | What happened? | Outcome, completion, cause of stopping, device/target table and essential run facts. |
| Findings | What needs investigation? | Confirmed failures first; clearly separated suspicions, blockers and unaccepted AI responses. |
| Devices | What happened on this device? | Selected context, scenario outcome, remaining work, coverage explanation and recorded steps. |
| Requirements | What was checked? | Scoped result summary and expandable checks with evidence links. |
| Activity | How did execution proceed? | Compact activity, complete chronological journal, preparation/build details, budget ledger and diagnostic downloads. |

These are sections of one local document, not separate pages or an application requiring a server. Production uses real section links and stable anchors. All essential content is available without JavaScript; optional filtering and the image viewer enhance it. The preview switches views to demonstrate the information structure, which is not a proposal to make production content dependent on JavaScript.

## 3. Overview

Show the following before the long evidence and activity sections:

1. **Verdict:** the saved outcome, such as Failed or Inconclusive.
2. **Completion:** Complete, Incomplete or In progress. A partial snapshot must be unmistakable and show its last update. Do not imply a live connection or automatic refresh.
3. **Explanation:** one short, evidence-backed sentence connecting failures and stopping reasons. Use deterministic wording from recorded facts; do not call AI to write it.
4. **Device/target table:** every expected combination, including work that never started.
5. **Run facts:** readable start/finish or update time, duration, branch/commit, model, request count and conservative accounted cost/limit where available. Replay also identifies the source build execution.

Example based on the reviewed replay:

> Failed · Incomplete  
> Android recorded two crash occurrences. Testing remained incomplete because the user stopped execution.

| Platform | Target | Verdict | Completion | Actions | Crash occurrences | Stop reason |
| --- | --- | --- | --- | --- | --- | --- |
| Android | Debug_Pride | Failed | Incomplete | 25 | 2 | User interruption |
| iOS | Debug_Pride | Inconclusive | Incomplete | 28 | 0 recorded | User interruption |

An explicit “View device steps” link opens the corresponding device/target context. Keep the whole table visible on Overview, even when another section has a device filter. Never present zero recorded crashes as proof that testing passed.

Use a single summary table rather than one large card per device/target. On narrow layouts, present each row as labelled fields without dropping columns or changing their meaning. Preserve a semantic relationship between each value and its label.

## 4. Findings and the investigation path

Every mandatory failure summary contains:

- A plain title describing the observed failure.
- Platform, device, target and scenario.
- Finding type and verification state.
- Observed trigger/result and occurrence count, when recorded.
- Direct links to exact recorded steps, screenshots and available diagnostics.
- Reproduction information from recorded actions, plus an explicit statement when the root cause or evidence is unavailable.

For the reviewed replay, show “Bluetooth control — 2 confirmed Android crash occurrences,” with links to saved steps 26 and 30. This groups related observations for reading; it does not establish one root cause or two distinct defects. Avoid inventing an exception or reproduction sequence from the control label alone.

The preferred route is **Finding → recorded step → evidence**. A finding may also link directly to its screenshot. Following a deep link must reveal the referenced record, select the matching context and clear any incompatible filters. Show that scope change. Opening evidence must not lose the path back to the finding.

Required failure text and evidence links stay visible when optional detailed finding/check sections are disabled. Raw JSON is always secondary. Unaccepted AI responses have a separate heading explaining that they do not determine the application verdict. Normal OS permission prompts are observations or blockers according to the existing instruction policy, never permission-only application failures.

## 5. Device steps and evidence

Within Devices, select device and target, then scenario when more than one exists. Use meaningful labels and include enough identity to distinguish two phones on the same platform. Do not show a selector with only one choice. Initially show all device summaries; choosing a summary reveals its detail.

Each recorded step has a compact heading with its exact saved ID, action/control and observed result. Expand details for the action intention, observation, crash/error, recovery and available screenshot. Use labelled text, not an unstructured paragraph. Keep failed and blocked steps easy to spot, without relying on color. Label reset/check records separately from device actions.

Anchor identity includes device, target, scenario and saved step ID; displayed step numbers are never renumbered. Generate safe, collision-free anchor tokens from stable record identity. Text and attribute values remain escaped. Step 0 and steps with duplicate numbers in different scenarios must remain independently reachable.

The evidence viewer shows the actual saved masked image, its context and capture relationship when known. A decision screenshot must not be labelled “after action” unless the record establishes that timing. Provide zoom, previous/next available screenshot within the selected scenario, close/Escape and focus return. Keep an ordinary relative image link available. Missing or rejected evidence gets a reason, not a blank image box. Preserve masking, redaction and link containment.

Remaining work uses device/scenario-scoped lists. Clearly label model-reported plans separately from deterministic requirement/control accounting. Disclose conflicting statements. The known cross-device worker scope defect needs its own correction; the renderer must not quietly remove inconvenient source data. Coverage labels say “observed control/state combinations” and “activated combinations,” with a short limitation beside the values. Do not calculate an application coverage percentage.

## 6. Requirements, activity and filters

Requirements presents each saved requirement with its status, scope and evidence route. Do not merge results from different devices into an unexplained single result. Expand source text and individual checks when needed. Preserve overridden and untested states, plus the distinction between instruction checks and requirement checks.

Activity begins with compact operations and important warnings/errors. The full ordered journal is always available. Pair start/end records only when their recorded identity makes the pairing unambiguous; otherwise retain separate entries. Never infer success from a host stage returning when individual work failed. An operation without a recorded finish remains unfinished.

Use local device, target and status filters where they help investigation; add text search for steps/activity. Labels identify the section being searched. Show “Showing X of Y” and the selected scope, with Clear filters. Start with a broad scope and show an explanatory empty state if no records match. Overview totals remain unfiltered and visibly labelled as whole-run values. Filtering changes presentation only; it cannot change verdicts, counts in saved data or execution policy.

Readable timestamps use UTC consistently, for example “30 Oct 2026, 16:43:21 UTC.” Exact machine timestamps remain in details. Use short durations such as “2 min 18 sec.” State “Not recorded” for unavailable values. Display conservative accounted cost, configured budget and pending reservations with their actual meaning; never describe them as a verified invoice. Keep build provenance, effective redacted inputs, logs and raw data under descriptive technical headings in Activity.

## 7. Visual and accessibility behavior

Use a neutral background, clear headings, aligned fields and restrained spacing. Reserve strong color for meaningful statuses and use text alongside it. Navigation, links and controls must look interactive. Avoid decorative effects, gesture-only controls and dense icon-only navigation.

Use semantic header/navigation/main regions, logical headings, table labels and contextual image descriptions. Keep native link/button/select behavior, visible keyboard focus and essential information available without hover. Handle long labels and device IDs with wrapping. Support narrow windows and text enlargement without hiding results. If a compact header remains visible while scrolling, it must not cover focused controls or anchor destinations.

The first implementation increment must verify keyboard navigation, focus visibility, non-color status recognition, narrow layouts and 200% text enlargement. The evidence viewer needs additional keyboard/focus checks when introduced. These checks do not replace later screen-reader, contrast and cross-browser validation.

## 8. Data and implementation boundaries

Keep one `CIMT output/reports/report_<timestamp>/index.html` per run or replay, with its own relative evidence. No shared latest page is introduced. Partial and final updates use the existing atomic publication path. Historical reports remain unchanged. Opening a report directly from disk must work offline after the whole report folder is moved.

Use the existing .NET report pipeline and unit-test project. Keep RunHtmlRenderer responsible for composition and scenario/evidence presentation, RunDiagnosticsRenderer for overview/stopping/activity, and RequirementHtmlRenderer for requirement results. Introduce focused helpers only when shared identity, formatting or summary rules justify them. Do not add a framework, server, interface hierarchy or AI dependency to reporting.

All summary values derive from saved host/worker data. Missing states must be represented explicitly; expected device/target combinations must not be invented when the snapshot lacks the information. If the existing saved schema cannot support a required summary reliably, report that design/implementation difference before changing the contract.

## 9. Acceptance and delivery

| Increment | Scope | Evidence needed |
| --- | --- | --- |
| A — find the result | Header/outcome, full device/target overview, readable failure summaries, section and exact-step links; accessibility baseline. | Existing test project covers step 0, duplicate step IDs in different scopes, missing device work, disabled optional details, partial/final states, escaping and contained links. Manual result-discovery check. |
| B — investigate | Scoped filters, readable steps/remaining work/coverage, compact activity, evidence viewer, time/budget presentation. | Filter clearing and empty states, failure deep links across filters, unfinished operations, missing screenshots, viewer keyboard/focus behavior and offline moved-folder check. |
| C — qualify | Large reports, multiple targets, blocked/disconnected devices, failed builds, interruption and browser/accessibility review. | No lost journal/evidence records; usability checks on representative reports, contrast and screen-reader checks, developer review. |

Use the reviewed two-device replay as the baseline: identify the failed device within ten seconds and reach its exact triggering step and evidence through no more than two navigation actions. These are proposed CIMT targets requiring manual validation. The design preview demonstrates the route, not a completed timing or accessibility test.

Traceability: A covers UX-01–UX-06 and the UX-14 baseline; B covers UX-07–UX-13; C verifies the whole design. UX-10's worker scope correction remains a separately identified correctness task. Existing FR-26–FR-30, FR-61–FR-64, FR-69 and AC-45 remain authoritative. Navigation/filter/viewer behavior and usability thresholds are proposed additions to approve before implementation.

Review decisions: choose the recommended sidebar or the horizontal alternative; confirm the five sections and result-first reading order; confirm increment A as the first implementation scope. This proposal does not authorize changing test behavior, budgets, permission handling or retained evidence.
