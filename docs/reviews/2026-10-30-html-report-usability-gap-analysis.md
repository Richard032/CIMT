# HTML report usability gap analysis

Date: 30 October 2026  
Product: CIMT — Curtis Intelligent Mobile Test  
Status: analysis and proposed improvements; implementation is not authorized by this document

Follow-up: the [Apple and Tesla comparison](2026-10-30-apple-tesla-report-design-comparison.md) supports these findings and refines the proposed implementation order. It moves accessibility/responsive work into the first increment and separates primary section navigation from device/target selection. These are recommendations, not implemented changes.

## 1. Assessment

The report retains useful evidence, but it is difficult to use for the normal developer question: **What failed, on which device, and how can I reproduce it?** It reads mainly as an expanded execution log. The developer must search through preparation and technical detail before reaching the application results.

This is primarily an information hierarchy and navigation problem. The reviewed HTML contains Android results; their position makes them easy to overlook. Adding another shared report page would not solve this problem and would conflict with the confirmed folder contract.

Keep one report folder for each run/replay: `CIMT output/reports/report_<date-time>/index.html`. Improve the presentation inside that report. Do not introduce a shared latest page, alter recorded verdicts, or change saved evidence.

## 2. Evidence and review limits

Reviewed execution: `TestRun_ios_android_SingleTarget`, replay `2026-10-30_16-43-21-093`, 17:43–17:48 Europe/Zurich. It used Debug_Pride on iOS and Android. Final result: failed/incomplete after user interruption, with two confirmed Android crash occurrences and no recorded iOS crash.

Sources: the saved `index.html`, `result.json`, `ui-results.json`, and current report renderers. No private YAML was read. This is a static HTML/data/source audit, not a completed browser layout, keyboard, screen-reader, contrast, or user-timing test. Pixel positions and page heights have not been measured.

Measured properties of the saved page:

| Property | Measured result | Practical effect |
| --- | --- | --- |
| HTML size | 587,414 bytes | Size alone is not a proven performance problem; much of the content is duplicated technical detail. |
| Chronological activity | 960 entries, including 473 starts and 470 completions | Routine operations dominate the page. |
| Activity placement | Before requirement mapping and device results | The full timeline appears before the results the user is trying to inspect. |
| Activity text | About 129,000 characters, including whitespace | Large reading/scrolling burden before device evidence. |
| Device order | iOS first, Android second | Android follows 33 expanded iOS step records. |
| Step records | 33 iOS, 34 Android | These include reset/check records, not only device actions. |
| Screenshots | 68 image elements | All exist: 67 recorded-step images plus one rejected-response image. |
| Section anchors / jump links | 0 IDs and 0 fragment links | No direct jump to a device, finding, or recorded step. |
| Controls | No report search, filter, or navigation controls | Readers must scroll or use browser text search. |
| Default expansion | Both device step lists are expanded | Reading one device requires passing through another device's full detail. |
| Screenshot alternative text | Every image uses `Step evidence` | Images are not identified by device, step, or purpose. |
| Responsive metadata | Charset only; no viewport metadata | Responsive behavior needs design and browser validation. |

The saved report predates the newly installed command/identity title improvement. Current source now distinguishes run/replay in the title and header. Historical reports were intentionally left unchanged. That identity improvement is already implemented; it does not address the remaining layout gaps below.

## 3. Prioritized gaps

P1 means the gap obstructs finding or interpreting a test result. P2 means the gap slows investigation or makes a result easier to misunderstand. These are review priorities, not new product failure verdicts.

| ID | Priority | Gap and evidence | Required direction |
| --- | --- | --- | --- |
| UX-01 | P1 | No compact device-result overview. The top overview lists startup devices and available builds, but not each device's outcome, crash count, executed work and stop reason. | Put all configured target/device outcomes in a compact table near the top. Include not-started/blocked combinations rather than only scenarios with actions. |
| UX-02 | P1 | The 960-entry timeline precedes the application results. Android appears after all expanded iOS detail. | Put outcome, device summary and findings first. Keep chronological activity available in a clearly labelled compact/expandable section later. |
| UX-03 | P1 | No navigation anchors or filters. The user cannot select Android or jump to its crash. | Add a contents/navigation area and stable target/device/finding/step anchors. Add simple device, target and status filters with visible filtered counts. |
| UX-04 | P1 | Crash investigation relies on expandable raw findings JSON. The mandatory stopping reason says to see scenario findings, without a direct jump to the triggering control and evidence. | Show a readable mandatory finding summary: device, target, observed trigger, confidence, occurrence count, recorded reproduction, screenshot and available diagnostics. Keep raw JSON secondary. |
| UX-05 | P1 | Saved steps start at 0, but the HTML uses an ordinary ordered list starting at 1. Step references and visible list numbers can differ. | Display the exact saved step ID and use it for links from findings and requirements. Never renumber saved evidence in the UI. |
| UX-06 | P2 | Failed, incomplete and user interruption appear as separate values and repeated reasons. Their relationship is not summarized. | Explain the final outcome in one sentence, for example: “Android crashed twice; testing remained incomplete because the user stopped execution.” Keep verdict and completion distinct. |
| UX-07 | P2 | Routine start/completion pairs create separate long rows. Concurrent device operations share one global stream. | Offer compact operation rows and per-device context. Retain the complete ordered journal. Do not invent a completion or pair ambiguous events. |
| UX-08 | P2 | Screenshots are small linked thumbnails. Opening the image leaves the report; there is no in-report previous/next evidence view. | Add an accessible image viewer with step/device context, zoom and previous/next navigation. Retain ordinary image links as a local-file fallback. |
| UX-09 | P2 | Step notes are emitted as unlabelled paragraphs; action intention, actual outcome, errors and recovery are hard to distinguish. | Give each step a compact heading and labelled fields: action/control, observed result, error/crash, recovery and screenshot. Keep AI descriptions separate from observed outcomes. |
| UX-10 | P2 | Remaining-work arrays are shown as JSON-like text. Both workers also claim the other platform is outstanding, despite both being tested. | Present device-scoped bullet lists and distinguish AI-reported work from host coverage gaps. Correct cross-device scope in the worker separately; do not silently hide contradictory source data. |
| UX-11 | P2 | Coverage numbers count control/state combinations, while most readers will interpret “controls” as distinct buttons. The iOS number is 195 observed versus 18 activated. | Label the units consistently and explain limitations beside the numbers. Do not turn these counts into an “application coverage” percentage. |
| UX-12 | P2 | Time uses long UTC timestamps and duration in seconds; budget is raw JSON. | Show readable duration, clear timezone labels, model, requests and conservative accounted cost/budget as summary fields. Retain exact UTC values and ledger details for diagnosis. |
| UX-13 | P2 | Evidence, checks, inputs and full execution data repeat much of the same information. Full execution JSON alone adds substantial hidden page content. | Keep one readable presentation for normal use and a secondary technical-data section/download. Preserve every required observation and raw diagnostic record. |
| UX-14 | P2 | Navigation landmarks, contextual image labels and responsive support are incomplete. Status styling has little hierarchy. | Use semantic landmarks, contextual alternative text, keyboard-operable controls and responsive layout. Use visible text alongside status colors. Verify actual behavior before claiming accessibility conformance. |

A mandatory failure summary must remain useful when optional requirement, finding or scenario detail is disabled. The current renderer can hide detailed checks/findings behind those options while retaining only generic failure/count text. The redesign must preserve the reporting policy and make the failing action/evidence reachable without enabling raw diagnostic sections.

## 4. Requirement coverage and missing design definition

| Existing requirement | Current state | Gap |
| --- | --- | --- |
| FR-26: local HTML grouped by target/device/scenario | Data is present and grouped in long sections. | No quick comparison or navigation between groups. |
| FR-27: complete requirement results and evidence | Requirement text, scope and evidence links are present. | Need compact status overview and direct links to exact step IDs. A partial observation must not look like exhaustive application coverage. |
| FR-28: step screenshots and observed behavior | Images are present and individually linked. | Step identity, contextual labels and evidence browsing are weak. |
| FR-29: observations, reproduction and diagnostics | Substantial information is retained. | Too much is raw or duplicated; normal investigation is difficult. |
| FR-30 / AC-45: one folder per execution, including replay | Confirmed contract, with isolated report/evidence paths. | Preserve it. No shared report or folder redesign is needed. |
| FR-61: readable overview | Required identity/preparation fields exist. | Missing a concise device/outcome/finding summary. |
| FR-62: chronological activity | All 960 records are available. | Presentation overwhelms the page. Keep the section and full journal, with clearly labelled compact and detailed views. |
| FR-63 / FR-64: understandable failures and stopping reasons | Reasons are visible, but often generic or repeated. | Show causal explanation and readable evidence-backed finding summaries independently of optional details. |
| FR-69: partial/final reporting | Implemented and covered by existing checks. | Keep progress state clear after changing the layout; do not make partial reports look final. |

The existing requirements specify report content more strongly than usability. They do not currently define a device comparison table, jump navigation, filters, image viewer, or measurable usability checks. Those are proposed design additions, not claims that every missing control violates an already approved requirement. Exact step identity and understandable failure reporting also affect correctness and traceability.

## 5. Proposed page structure

One `index.html` inside the execution's existing report folder:

```text
Run/replay identity · date/time · branch/commit · target
FAILED                         INCOMPLETE — user interruption
Android crashed twice; testing stopped before full exploration.

Device/target overview
Platform   Target        Result         Actions   Crashes   Stop reason
Android    Debug_Pride   Failed         25        2         User interruption
 iOS       Debug_Pride   Inconclusive   28        0         User interruption

Navigation: Summary | Findings | Android | iOS | Requirements | Activity | Diagnostics

Findings
  Bluetooth control: 2 confirmed Android crash occurrences
  [Recorded reproduction] [Step 26] [Step 30] [Screenshots] [Diagnostics]

Selected device and scenario
  Summary · observed/blocked work · step list
  Step 26 — Bluetooth control — confirmed crash — relaunch succeeded
  [Screenshot] [Observed outcome] [Action details]

Requirements
  Compact scope/status matrix; expand source and observations

Chronological activity
  Compact milestones · device/operation/status filters · full ordered journal

Technical details and downloads
  Build provenance · inputs · logs · raw JSON · conservative budget ledger
```

The example uses the recorded replay counts. Actions and recorded steps must have different labels: 53 actions versus 67 step records. Two crash occurrences at the same recorded control are not automatically two distinct bugs, and do not establish a single shared exception/root cause. The report should say what was observed and what remains unknown.

## 6. Proposed acceptance checks

These are review proposals for the next implementation increment:

1. In the two-device replay fixture, the first desktop overview shows Android and iOS outcomes, target, crash counts and primary stop reason. Conduct a manual check that a developer can identify the failed device within ten seconds.
2. Reach the Android failure, exact recorded triggering step and screenshot through no more than two navigation actions. Links must identify both device and scenario.
3. Visible step IDs exactly match saved JSON IDs, including step 0 and crash steps 26/30. Requirement and failure links land on those exact records.
4. Keep all chronological records available. A filtered/compact view shows its scope and counts; clearing it restores all records. Unfinished operations remain explicitly unfinished.
5. Display failure summaries even when optional detail sections are disabled. Separate confirmed crashes, suspected exits, infrastructure errors and normal permission prompts.
6. Show missing evidence explicitly. Keep rejected AI responses separate from accepted findings; an unaccepted observation must never appear as a verified failure.
7. Test two devices, several targets, a blocked device, a failed build, an interrupted run, an active partial report and an execution with no screenshots. Do not leave empty sections that look like missing results.
8. Verify keyboard navigation and image viewing on desktop and narrow layouts. Check focus visibility, contextual image labels and status readability without relying on color.
9. Open the report directly from disk without network access or a web server. All evidence remains relative and inside the same execution folder. Preserve existing redaction and HTML escaping. Do not load external scripts/fonts or alter historical reports.
10. Keep rendering deterministic from saved report data. No model calls, device operations, changed spending limits or changed verdict/completion policy are needed for the redesign.

## 7. Recommended implementation order

**First increment:** device/target summary, concise outcome explanation, findings above logs, section anchors, exact step IDs, and readable mandatory failure cards. These changes address the strongest causes of the “Android is missing” impression.

**Second increment:** device/status filters, compact step/activity views, evidence viewer and readable remaining-work/budget/time fields.

**Third increment:** responsive/accessibility verification, large-report navigation checks and refinement based on user review.

Keep these changes in the existing report renderer responsibilities and unit-test project. A new reporting framework, separate server, shared latest report, or testing-agent redesign is not needed for this work. Worker-generated cross-device remaining-work statements and unavailable native exception stacks are separate data-quality gaps; a new layout must disclose them rather than claim to fix them.

## 8. Source locations

- [RunHtmlRenderer](../../src/Cimt/Reporting/RunHtmlRenderer.cs): section order, expanded device steps, step labels, image links, raw details and budget output.
- [RunDiagnosticsRenderer](../../src/Cimt/Reporting/RunDiagnosticsRenderer.cs): overview, stop reasons and expanded activity entries.
- [RequirementHtmlRenderer](../../src/Cimt/Reporting/RequirementHtmlRenderer.cs): expanded requirement/scoped evidence presentation.
- [Requirements](../requirements.md): FR-26–FR-30, FR-61–FR-64, FR-69 and AC-45.
- Reviewed saved execution: `/Users/sumkar/Development/Testing/TestRun_ios_android_SingleTarget/CIMT output/reports/report_2026-10-30_16-43-21-093/`.

No application code, renderer code, installed component, private configuration or historical report was modified during this review. The only added project artifact is this analysis.
