# Apple and Tesla comparison for CIMT report design

Date: 30 October 2026  
Product: CIMT — Curtis Intelligent Mobile Test  
Status: research and design recommendations; no report redesign implemented

Next review artifact: the [HTML report design proposal](2026-10-30-html-report-design-proposal.md) specifies the page structure, interaction rules and implementation increments. It remains a proposal for approval.

## 1. Conclusion and scope

The comparison supports the main conclusion of the [HTML report gap analysis](2026-10-30-html-report-usability-gap-analysis.md): developers need outcomes, affected devices and failure evidence before the execution journal. The reviewed report contains Android results, but the information order makes them easy to miss.

Two recommendations change after this comparison:

1. Include accessibility and responsive behavior in the first increment, rather than postponing them to the last increment.
2. Keep primary navigation small and stable. Devices and build targets belong in the result overview and context selectors, rather than adding a new primary navigation item for every combination.

This is a comparison of published guidance and documented behavior. It is not an Apple certification, a Tesla compliance audit, or a completed browser usability test. The original static review limits still apply.

## 2. Source authority

**Apple:** the Human Interface Guidelines are published design guidance for Apple platforms. This review read the official Layout, Sidebars, Writing, Search fields, Disclosure controls, Color and Accessibility pages, including their official Markdown versions. General interaction principles can inform CIMT; native platform APIs and visual materials are not requirements for an offline HTML report.

**Tesla:** no public general UI design guideline equivalent to Apple's HIG was found in the official sources searched. This review instead read the official North American Model 3 manual's Touchscreen and Car Status sections. Statements below describe documented behavior; applications to CIMT are our inferences. Tesla explicitly says the interface can vary with software, options and market. [Tesla Touchscreen](https://www.tesla.com/ownersmanual/model3/en_us/GUID-518C51C1-E9AC-4A68-AE12-07F4FF8C881E.html)

## 3. What the sources support

| Source | Published guidance or documented behavior | Application proposed for CIMT |
| --- | --- | --- |
| [Apple Layout](https://developer.apple.com/design/human-interface-guidelines/layout) | Order content by importance; group and align related information; disclose detail progressively; adapt to available space and text size. | Put results first. Use aligned device/target rows and compact detail sections that remain readable when resized. |
| [Apple Sidebars](https://developer.apple.com/design/human-interface-guidelines/sidebars) | Navigation should have clear labels and manageable hierarchy; compact alternatives can suit limited space. | Use a few stable report sections. Keep device/target selection separate from primary navigation. A sidebar is an option, not a requirement. |
| [Apple Writing](https://developer.apple.com/design/human-interface-guidelines/writing) | Use plain, consistent wording, descriptive action labels and useful explanations of errors and empty states. | Explain what happened and why testing stopped. Label links such as “View Android crash step 26.” Explain why an expected result or image is absent. |
| [Apple Search fields](https://developer.apple.com/design/human-interface-guidelines/search-fields) | Make search scope understandable and allow useful filtering. | Label filters and search as applying to this report, with visible device/target scope and result counts. |
| [Apple Disclosure controls](https://developer.apple.com/design/human-interface-guidelines/disclosure-controls) | Keep essential choices visible; reveal advanced detail when relevant, using descriptive labels. | Keep failure summaries visible. Collapse routine activity and raw JSON under meaningful headings. |
| [Apple Color](https://developer.apple.com/design/human-interface-guidelines/color) and [Accessibility](https://developer.apple.com/design/human-interface-guidelines/accessibility) | Give colors consistent meanings; provide alternatives to color, readable content, meaningful accessibility descriptions and keyboard operation. | Use status words alongside color. Add semantic structure, contextual image labels, visible focus and keyboard support. |
| [Tesla Car Status](https://www.tesla.com/ownersmanual/model3/en_us/GUID-80B80D48-E3A9-4857-864B-F4CC9B56FD7E.html) | A dedicated area shows current vehicle status, with content changing for parked, driving and charging states. | Inference: retain clear run identity and outcome while the reader investigates device details. For saved reports, this means recorded execution state, not live telemetry. |
| [Tesla Touchscreen](https://www.tesla.com/ownersmanual/model3/en_us/GUID-518C51C1-E9AC-4A68-AE12-07F4FF8C881E.html) | Controls search can jump to a setting; information icons explain nearby settings; alerts can expose more detail and resolution information. | Inference: provide direct routes from a failure to its recorded step, screenshot and available diagnostics, plus explanations beside unfamiliar metrics. |

## 4. Comparison with every recorded gap

“Supported” means the source supports the design direction. The exact component and acceptance threshold remain CIMT proposals.

| Gap | Comparison | Decision |
| --- | --- | --- |
| UX-01 — device/target overview | Supported by Apple hierarchy; Tesla status presentation offers a useful analogy. | Keep P1. Include all expected combinations, including blocked and not-started work. |
| UX-02 — logs before results | Strongly supported by Apple hierarchy and disclosure guidance. | Keep P1. Move findings and outcomes above the journal. |
| UX-03 — navigation and filters | Supported by Apple navigation/search; Tesla documents direct access through search. | Keep P1. Start with section anchors; add scoped filters without crowding navigation. |
| UX-04 — readable failure evidence | Supported by Apple writing/disclosure; Tesla documents contextual alert detail. | Keep P1. Failure cards must work independently of optional technical sections. |
| UX-05 — mismatched step IDs | A CIMT traceability defect. Neither source defines CIMT step numbering. | Keep P1 based on saved evidence. Display exact recorded IDs. |
| UX-06 — outcome versus stop reason | Apple writing supports clearer explanation; Tesla separates status from additional alert detail. | Include the causal outcome sentence in the first increment. Preserve separate verdict and completion values. |
| UX-07 — excessive activity rows | Apple disclosure supports a compact default presentation. | Keep P2. Preserve event order and unfinished operations in the full journal. |
| UX-08 — screenshot browsing | Apple accessibility supports usable image access. Neither reviewed source specifies a test-report viewer. | Keep P2. Viewer, zoom and previous/next controls are CIMT proposals. |
| UX-09 — unlabelled step notes | Apple grouping and consistent writing support labelled information. | Keep P2. Separate intended action, observed result and recovery. |
| UX-10 — remaining work | Apple writing supports understandable presentation. Incorrect cross-device claims are a separate data defect. | Keep both work items: readable scoped lists and correction of worker scope. Preserve contradictory evidence explicitly. |
| UX-11 — coverage meaning | Clear terminology supports better labels; neither source validates this coverage metric. | Keep P2. State the unit: observed control/state combinations. Avoid an application coverage percentage. |
| UX-12 — raw time and budget | Apple writing supports consistent labels; Tesla status displays offer only a contextual analogy. | Keep P2. Show readable units, timezone and accounted cost, with exact records available. |
| UX-13 — duplicated technical data | Apple disclosure supports a simpler normal reading path. | Keep P2. Retain raw evidence as secondary detail/downloads. |
| UX-14 — accessibility and resizing | Explicitly supported by Apple's accessibility and layout guidance. | Raise to P1 for the redesigned components and include verification in the first increment. |

The gap analysis measured 960 activity records, 67 step records and 68 screenshots. Those measurements establish the current information burden. They do not establish a measured load-time problem or prove an accessibility violation without browser testing.

## 5. Refined report proposal

The following is a CIMT design proposal derived from the comparison, not a layout prescribed by either company.

**First view:** execution identity, recorded/partial state, verdict, completion and a short causal explanation. Follow with the device/target outcome table, including actions, confirmed crash occurrences and stop reasons. Distinguish no recorded crash from proof that an application is crash-free.

**Primary navigation:** Overview, Findings, Devices, Requirements, Activity. Technical downloads can sit within Activity. Use device and target selectors within the relevant content. Begin with all devices visible in the overview; selecting one must make the narrower scope clear. Use navigation links for sections and labelled controls for filtering.

**Investigation path:** readable finding → exact device/target/scenario step → screenshot and available diagnostics. Keep the selected context visible and offer an explicit return route. A compact identity header may remain visible while scrolling if it does not obscure content or keyboard focus.

**Detail:** collapse routine operations, raw payloads and full input copies by default. Keep required failure summaries and missing-evidence explanations visible. Filtered views must expose their scope and counts. Retain the complete chronological journal and original evidence.

**Evidence:** show a contextual caption with device, target and saved step ID. If adding a viewer, support keyboard operation, close/Escape, focus return and an ordinary image-link fallback. Keep original screenshots and masking unchanged.

**Meaning:** distinguish a confirmed crash, an AI suspicion, a rejected response, an infrastructure failure and a normal OS permission prompt. Never invent a root cause, reproduction step or missing stack trace. Separate actions from step records and crash occurrences from distinct defects. Budget figures describe CIMT's conservative accounting, not a verified provider invoice.

**Presentation:** use restrained color, aligned fields, readable spacing and explicit labels. Let narrow layouts stack content without hiding results. Validate text enlargement and keyboard access from the beginning. No decorative animation is needed to explain a saved run.

## 6. Limits and implementation order

Do not copy vehicle driving layouts, gesture-only shortcuts, icon-only navigation or native Liquid Glass effects into this report. Tesla's driving constraints differ from a developer's investigation task. Apple's platform-specific control dimensions and APIs also do not directly define web implementation choices. The useful transfer is information priority, context, discoverability and clear feedback.

Apple's caution about multiple disclosure buttons concerns a particular push-style control. It is not a general prohibition on several HTML detail sections. Keep disclosure shallow and understandable rather than applying that rule mechanically. [Apple Disclosure controls](https://developer.apple.com/design/human-interface-guidelines/disclosure-controls)

Recommended increments:

1. **Result discovery and correctness:** device/target summary, causal outcome sentence, readable failure cards, section/step links and exact saved IDs. Include keyboard operation, semantic structure, status text, image labels and responsive behavior for these components.
2. **Investigation:** scoped filters, compact steps/activity, accessible evidence browsing and readable remaining work, time and budget.
3. **Validation and refinement:** test larger reports and additional result states; complete cross-browser and assistive-technology review, then refine from developer feedback. Accessibility verification starts in increment 1 and continues here.

Retain the proposed ten-second result-discovery check and two-action failure/evidence path from the original analysis. These are CIMT usability targets, not Apple or Tesla rules; they still need manual validation. Check narrow windows and 200% text enlargement, keyboard navigation, focus visibility, non-color status recognition and missing-evidence states. Do not claim accessibility conformance from markup inspection alone. [Apple Accessibility](https://developer.apple.com/design/human-interface-guidelines/accessibility)

Keep one existing timestamped folder per run/replay, relative local evidence and offline operation. No shared latest page, external service, reporting framework, model request or change to testing/budget policy is required. This review changes recommendations only; product requirements and renderer behavior remain unchanged until the redesign is approved and implemented.
