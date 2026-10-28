# Complete requirement mapping

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

Each objective gets a fresh result for every catalogue item. All start as not tested, with an explanation that no observation exists yet. The model receives these IDs, source text, and current results together with its masked screen and testing instructions. The original requirements text is not duplicated in that request.

Requirement checks must use a known requirementId. Instruction checks use an empty ID. Each decided check includes expected and observed behavior. The host supplies its step number and links the same masked screen used for that decision. CheckRecorder records and publishes the result before image storage, so a storage error cannot erase a known failure. Original check history remains available even when the current requirement status changes.

| Status | Required information and behavior |
| --- | --- |
| passed | Expected and observed behavior support the complete catalogue item. |
| failed | Expected and observed behavior contradict it. A later successful retry cannot erase the finding. A validated instruction override changes the applicable expectation, while retaining the original observation in history. |
| not tested | Explain why no evaluation was performed. |
| inconclusive | Explain why available observations cannot establish a decision. Later evidence may resolve it. |
| overridden | Explain the instruction/requirement conflict and supply an exact, nonempty instructionQuote from the testing instructions. Judge against that instruction; later checks do not cancel a valid override. App crashes and instruction failures still fail. |

Unknown IDs and invalid override references stop as an infrastructure/response error. No runtime question is asked, and missing evidence never becomes an invented pass. Checking that a quote exists establishes its source; the meaning of the conflict is still the model's interpretation and is visible for review.

## Coverage matrix and outcomes

The finalizer builds the matrix from configured targets and compatible startup devices, including targets whose builds failed and devices/objectives that never started. New devices are not added. A run with no compatible pair still reports each supplied item as not tested with an explanation.

Results are separated by target, platform, and device. Evidence from one combination cannot pass another. Every catalogue item and its scoped statuses appear in HTML and result.json. Source text, line range, expected/observed behavior, conflict quote, step reference, evidence link, or an unavailable-evidence explanation remain attached. The requirement matrix is mandatory coverage information; reports.sections still controls the existing optional step/check/diagnostic sections.

For an overall requirement: any failure wins; all not tested stays not tested; mixed unresolved results are inconclusive; all overridden stays overridden; otherwise completed passed/overridden combinations pass. An unresolved scoped result always keeps coverage incomplete, including when another scope failed. Navigation completion cannot hide an untested requirement. The final run preserves failed verdicts independently from incomplete execution and retains exit precedence 3, 1, 2, 0.

Mapping is complete when every requirement entry has a recorded result or an explicit explanation for every applicable combination, with document headings retained separately as context. That does not mean all requirements passed or were tested. Tests remain bounded by the configured time and AI budget; mapping adds no separate paid extraction phase.

## Example and verification

The [runnable offline demonstration](../examples/requirement-mapping/README.md) uses the real catalogue and report services with five synthetic observations, including a documented override and inconclusive result. No API key, phone, or real app is used. Exit 1 and incomplete completion are expected because the fixture deliberately includes a failure and unresolved work.

The development suite checks source grouping, IDs and line references, mapped status transitions, rejected unknown IDs/quotes, evidence failures, independent device/target scopes, failed-build coverage through the public command, all five rendered statuses, and final outcome precedence. Use bash scripts/check-development.sh. These checks do not replace Android/iOS application acceptance.
