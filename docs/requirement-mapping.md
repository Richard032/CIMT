# Complete requirement mapping

## Device Adapter boundary and startup recovery

FR-98 / AC-68 map to runtime/device_adapter/. DeviceStartup owns the fixed apps list probe and 90-second cumulative window; NativeDevice classifies/redacts the known native startup failure. Mobile.connect orders lock checks, startup readiness and client connection before app setup. Execution supplies cancellation; stopping_policy/ retains exhausted-error scope. test_device_startup.py covers bounds, failures, cancellation, connection ordering and import boundaries; test_defect_policies.py covers redacted error types and unchanged scope. Existing capture/lifecycle/platform suites use the new package. scripts/install-cimt-runtime.sh packages all modules and removes obsolete flat files. See [Device Adapter](device-adapter.md).

## Input-only layer and human-interface information

FR-97 / AC-67 map to runtime/ai_instructions/: InstructionContext, ActionPromptBuilder and human_interface. They provide sources, credential aliases, fresh masked adapter observations and exact AI-selected context. Reply decoding is a separate execution component. ScenarioRunner supplies repetition notices after execution instead of vetoing the proposed command. tests/test_ai_instructions.py verifies control/source information and import boundaries; ScenarioTests verifies refresh after a note, fourth-tap execution, recovery information and shared limits. Mobile MCP remains the confirmed adapter. See [AI Instruction and Context](ai-instruction-context.md).

## AI replies and resource exchange

FR-96 / AC-66 supersede the earlier FR-65/AC-39 response-correction contract. runtime/command_reply.py binds explicit commands and preserves full original text. AiInteraction coordinates requests without response approval; input preparation is in ai_instructions/. CheckRecorder and TestPlanner store optional AI records; unknown joins remain unbound. ScenarioRunner keeps notes/feedback and honors AI finish while reporting unresolved work. PlanningHtmlRenderer displays redacted/escaped full replies. Existing suites cover minimal commands, more than three notes, optional metadata, unavailable addresses, shared limits and privacy. See [AI Resource Exchange](ai-resource-exchange.md).

## Stopping scope and layer folders

FR-95 / AC-65 map to ActionExecutor's ref forwarding, typed DeviceActionError parsing, ScenarioRunner's action feedback and separate requested-target identities in exploration/crash records. Existing tests exercise absent/disabled targets, AI-selected follow-up after an adapter rejection, unchanged credential protections and distinct unknown refs. These checks do not claim that a stale ref can be resolved by the native adapter.

FR-32 / AC-63 map to the typed app-launch result in RpcMessages, the Execution Stopping Policy under runtime/stopping_policy/ and DeviceRunner's error recording. Existing unit tests verify both platform directions, preserved launch errors, continuing work without cancellation, global handling of other infrastructure failures and final exit precedence. DR-01 / AC-64 map to the named layer folders in the architecture and complete-package copying in scripts/install-cimt-runtime.sh. See [execution stopping](execution-stopping.md). Live dual-device qualification remains separate.

Implemented increment: 28 October 2026. Covers the catalogue, mapped observations, all five statuses, and target/device coverage required by FR-19 and FR-27. Real application acceptance remains separate.

## Source catalogue

The host reads the existing optional inputs.requirements text. No new command, YAML field, ID format, or paid planning call is required. Before runtime preflight, cloning, or builds, it saves requirements.json and the redacted input snapshot. The catalogue contains the source snapshot's SHA-256, items with generated IDs, original text, one-based start/end lines, and headingContext. Its separate headings list retains heading text, level, and source lines without IDs or test statuses. The hash identifies the redacted snapshot, not the original secret-bearing input.

IDs are REQ-0001, REQ-0002, and so on, in source order. Identical input creates identical IDs. Existing labels such as FR-01 stay in the text. Duplicate labels or duplicate text remain separate items. IDs are local to a source version; use the hash and original text when comparing runs.

Grouping is deterministic and conservative:

- Blank lines separate paragraphs.
- Bullets, numbered items, labelled IDs such as FR-01, and table rows start separate requirement items.
- Explicit Markdown headings are context: one to six leading hash characters followed by whitespace or end of line, or a title followed by an equals/dash underline. Up to three leading spaces are accepted. Heading-looking text in fenced or indented code stays source text. A heading ends the preceding requirement; it is never joined to that requirement.
- Each requirement keeps the active heading hierarchy. A new heading replaces its sibling and deeper headings. The AI receives that context with the requirement, rather than being asked to test a heading.
- A line ending with a period, question mark, or exclamation mark closes its current item before the next nonblank line.
- Other wrapped lines stay together. Multiple conditions within one item remain one combined expectation; every condition must have evidence before it can pass.
- No nonblank source text is silently discarded. Recognized headings remain in requirements.json, final result.json, and a mandatory HTML context section, including heading-only and trailing-heading input. They do not block completion. Plain unmarked titles, background prose, table headers, and other ambiguous text are not guessed to be headings; they remain requirement items and may be unresolved with an explanation. Use a list of testable expectations when separate decisions are important.

This provides complete source accounting. Requirement IDs count requirement entries only, so IDs after a removed heading can change compared with older catalogues; use the source hash, original text, and line references when reviewing retained reports. A heading-only document has no requirement evaluations and cannot by itself prove that an instruction objective passed. This does not claim automatic semantic decomposition of every sentence or proof that the model understood every condition. Semantic scenario planning and platform applicability remain separate work.

## Mapping observations

Each objective gets a fresh result for every catalogue item. All start as not tested, with an explanation that no observation exists yet. Bootstrap provides these IDs, source text and current results; subsequent working requests use AI-selected records with the current masked screen and authoritative testing instructions. The complete catalogue remains locally retrievable. The original requirements text is not duplicated in that request.

Every check names a stable taskId matching its source. Requirement checks also use a known requirementId; instruction checks use an empty requirement ID. Subject text is not identity. Each recorded check gets a host ID and affects planning status once. Each decided check includes expected and observed behavior. The host supplies its step number and links the same masked screen used for that decision. CheckRecorder records and publishes the result before image storage, so a storage error cannot erase a known failure. Original check history remains available even when the current requirement status changes.

Check redaction preserves known status/source words and canonical requirement IDs while removing secrets from other supplied text. The recorder stores AI findings without a response-format or semantic gate. Final JSON/HTML retains IDs, statuses, hashes, and evidence links without running text replacement over serialized data. See [redaction](redaction.md).

| Status | Required information and behavior |
| --- | --- |
| passed | Expected and observed behavior support the complete catalogue item. |
| failed | Expected and observed behavior contradict it. A later successful retry cannot erase the finding. An AI-declared instruction override changes the applicable expectation, while retaining the original observation in history. |
| not tested | Explain why no evaluation was performed. |
| inconclusive | Explain why available observations cannot establish a decision. Later evidence may resolve it. |
| overridden | Explain the instruction/requirement conflict and supply an exact, nonempty instructionQuote from the testing instructions. Judge against that instruction; later checks retain the recorded override. App crashes and instruction failures still fail. |

FR-96 removes host evaluation of source links and quotations. Unknown IDs remain unbound and do not update unrelated catalogue entries or block an action. Original replies remain inspectable. The AI interprets conflicts, reports evidence and owns the assessment; CIMT retains unresolved coverage and known failures without inventing a pass.

## Coverage matrix and outcomes

The finalizer builds the matrix from configured targets and compatible startup devices, including targets whose builds failed and devices/objectives that never started. New devices are not added. A run with no compatible pair still reports each supplied item as not tested with an explanation.

Results are separated by target, platform, and device. Evidence from one combination cannot pass another. Every catalogue item and its scoped statuses appear in HTML and result.json. Source text, line range, expected/observed behavior, conflict quote, step reference, evidence link, or an unavailable-evidence explanation remain attached. The requirement matrix is mandatory coverage information; reports.sections still controls the existing optional step/check/diagnostic sections.

For an overall requirement: any failure wins; all not tested stays not tested; mixed unresolved results are inconclusive; all overridden stays overridden; otherwise completed passed/overridden combinations pass. An unresolved scoped result always keeps coverage incomplete, including when another scope failed. Navigation completion cannot hide an untested requirement. The final run preserves failed verdicts independently from incomplete execution and retains exit precedence 3, 1, 2, 0.

Mapping is complete when every requirement entry has a recorded result or an explicit explanation for every applicable combination, with document headings retained separately as context. That does not mean all requirements passed or were tested. Tests remain bounded by the configured time and AI budget; mapping adds no separate paid extraction phase.

## Example and verification

The [runnable offline demonstration](../examples/requirement-mapping/README.md) uses the real catalogue and report services with five synthetic observations, including a documented override and inconclusive result. No API key, phone, or real app is used. Exit 1 and incomplete completion are expected because the fixture deliberately includes a failure and unresolved work.

The development suite checks source grouping, IDs and line references, mapped status transitions, rejected unknown IDs/quotes, evidence failures, independent device/target scopes, failed-build coverage through the public command, all five rendered statuses, and final outcome precedence. Use bash scripts/check-development.sh. These checks do not replace Android/iOS application acceptance.
