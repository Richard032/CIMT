# Requirements and implementation design review

Reviewed: 28 October 2026. Source baseline: main at d14f0854ec2bda74d50770e05a3c624d0be2ed76, including shared run identity.

This review compares the current code with the approved requirements and architecture. It does not change implementation or approved requirements. Findings D1–D5 have small offline reproductions. D6 is a contract mismatch found by reading the requirements and outcome policies.

## D1 — P1: secret removal can change the test result and damage JSON

Locations: [CheckRecorder](../../runtime/check_recorder.py), lines 15–24; [Redactor.object](../../runtime/redaction.py), lines 40–46; [RunReportWriter](../../src/Cimt/Reporting/RunReportWriter.cs), lines 47–48. Related requirements: FR-27, FR-31, FR-36; generated identity is also affected under FR-30.

CheckRecorder validates a model check, then removes secret values from every string, including status, source, and requirement ID. These changed values become the input to the verdict policy. RunJournal applies the same general transformation to worker results. The report writer also removes secrets from an already serialized JSON document, including its property names and numbers.

Reproduction: use the invented password `failed`, record an instruction failure and a separate successful instruction check, and complete the objective. The failure status becomes `<redacted>`. The verdict policy no longer recognizes it as a failure. The actual Python exit policy returns 0, and the actual .NET report writer also produces a passed result with exit 0 when no requirements file is supplied. This is a confirmed false pass, independent of model behavior.

A second reproduction uses the invented password `1` and a numeric stage value of 1. The actual report writer replaces that unquoted number with `<redacted>` and produces invalid result.json. A credential matching part of the generated timestamp can also change the reported identity without changing the folder or retained identity manifest.

Recommended correction: separate typed control data from text that can contain secrets. Never change status values, internal IDs, or JSON syntax during secret removal. Redact sensitive text fields before serialization and before storage. Validate the final internal record used for decisions. Treat unexpected status values as an error rather than a possible pass.

Simple regression cases: a credential equal to `failed`; a credential matching a requirement ID; a one-digit credential; and a credential matching the run year. Verify the verdict, valid JSON, and unchanged identity separately.

Resolution, 28 October 2026: the product owner requested the redaction fix. Record-aware redaction now preserves control metadata while scrubbing observations. Final JSON is sanitized as parsed values before serialization; HTML preserves metadata and sanitizes JSON details before encoding. Unknown check statuses cannot produce a pass. The synthetic Python-to-.NET reproduction now retains failed and exit 1; digit, ID, identity, and evidence-link cases pass. See [redaction verification](../redaction.md). Existing reports remain historical evidence.

## D2 — P1: escaped secret text can bypass screenshot masking

Location: [Redactor.sensitive](../../runtime/redaction.py), lines 48–58. Related requirements: FR-28 and FR-36.

Secret detection searches inside json.dumps(element). JSON escapes non-ASCII characters, quotes, backslashes, and control characters. The original secret can therefore be present in an ordinary UI label but absent from its serialized spelling. The text is redacted by a different path, while the screenshot rectangle is left visible. Explicit element-ID rules and secure-field recognition do not protect an ordinary label that displays the secret elsewhere.

Reproduction: an ordinary `status-label` contains the invented secret `páss`. Redactor.sensitive returns false. ScreenMasker changes the returned UI text to `<redacted>` but leaves the image inside the label bounds unchanged. The probe checks whether the rectangle is painted; it does not use a real screenshot or real credential.

Recommended correction: search the original string values in the UI structure before JSON encoding. Keep the existing element-ID and secure-field checks. Use separate simple tests for Unicode, quotes, backslashes, nested text, and a normal non-sensitive label.

Resolution, 28 October 2026: original nested UI strings now drive secret detection, and pixel tests pass for Unicode, quotes, backslashes, and newlines. Sensitive elements also mask nested UI text values. Required-mask failure still stops execution. D2 is resolved for the tested implementation; real-device masking acceptance remains open.

Screenshot follow-up, 28 October 2026: lossless native capture, clean image export, finite/clipped/outward-rounded geometry, screen-size stability, and overlapping child UI text are covered by separate services and regression cases. See [screenshot masking](../screenshot-masking.md). The product owner requested skipping physical-device checks after the locked Android check, so device acceptance is still open.

## D3 — P1: instruction completion has no complete instruction inventory

Locations: [scenario_verdict](../../runtime/check_results.py), lines 85–98; [ScenarioRunner._complete](../../runtime/scenario.py), lines 221–238. Related requirements: FR-14 and FR-25.

Requirements have host-owned IDs and coverage rows. Testing instructions have free-form check subjects only. A single successful instruction check is enough for the verdict policy once the model says complete and supplies an empty remaining list. There is no list of expected instruction objectives to compare with the recorded checks.

Reproduction: supply two objectives, Save and Delete, but record only a successful Save check. With no outstanding observed controls or supplied requirement rows, the policy accepts passed. The host cannot identify the missing Delete objective. Prompt wording asks the model to cover the task, but the completion calculation cannot verify that coverage.

Recommended correction: produce a retained list of instruction objectives before execution, preserve explicit scenario boundaries, and give each objective an ID and a result. Compute completion from those records. A missing observation must remain incomplete. Keep model interpretation visible, since an inventory does not guarantee that the model understood every instruction correctly.

Full semantic scenario planning is already documented as unfinished. This finding identifies the false-pass consequence of that gap; it does not claim that scenario planning was previously delivered.

## D4 — P2: observed button coverage overrides an exact scenario's scope

Locations: [ScenarioRunner._complete](../../runtime/scenario.py), lines 224–229; [CoverageTracker](../../runtime/coverage_tracker.py). Related requirements: FR-14 and FR-25.

Every observed enabled control is treated as required work, regardless of the test instructions. This is useful for the requested button-exploration example, but it is also applied to exact scenarios.

Reproduction: the exact objective is to press Save and verify the saved value. Save and Delete are visible; Save is activated and the check passes. Completion is still forced to incomplete because Delete was not activated. Making this test complete would require expanding its scope beyond the requested scenario.

Recommended correction: distinguish exact scenario scope from permitted exploration. Keep observed-control counts as report information. Only make unactivated controls block completion when the instructions require that exploration. Add separate tests for exact Save-only work and all-buttons exploration.

D3 and D4 are separate mistakes: missing requested work can pass, while unrelated visible work can prevent completion.

## D5 — P2: source context is treated as mandatory test work

Locations: [RequirementCatalogue](../../src/Cimt/Execution/RequirementCatalogue.cs), lines 29–36 and 48–53; [RequirementResults.unresolved](../../runtime/requirement_results.py), lines 67–69; [action prompt](../../runtime/action_prompt.py). Related requirement: FR-27. Design decision needed for input classification.

The catalogue preserves every nonblank source block as a requirement, including document headings and table headers. The prompt correctly prevents invented passes for context, but also requires such context to remain not tested. Every not-tested row then prevents completion.

Reproduction: `# Requirements` followed by `- Saving must work.` produces two mandatory catalogue items. Even after Saving passes, the heading keeps the objective inconclusive. Normal document formatting can therefore prevent successful completion forever.

The requirements ask for a result for every supplied requirement. They do not define how to distinguish a testable requirement from source context, or how to handle requirements that apply only to one platform. The mapping design currently resolves that omission by making all source text mandatory work.

Recommended design decision: retain all source content, but distinguish requirement entries from supporting context. Define applicability separately from the five evaluation statuses. Report every classification and its reason; do not silently discard ambiguous text. Decide this contract before changing the catalogue or completion policy.

Resolution of document headings, 28 October 2026: the product owner requested this fix. Explicit Markdown headings are now retained as separate context with text and line references. They have no requirement IDs/statuses and cannot block completion. Requirements retain their active section hierarchy, and HTML shows all recognized headings even if optional input details are hidden. FR-27/AC-24 and mapping documentation record the clarified contract. Plain prose, table-header classification, and platform applicability remain separate decisions; D5 is resolved for recognized document headings only. Other review findings are unchanged.

## D6 — P2: instruction-defined failure rules have no execution contract

Locations: [FR-31](../requirements.md), line 81; [scenario_verdict](../../runtime/check_results.py), lines 79–80; [CrashRecovery](../../runtime/crashes.py), lines 182–186; [RunOutcomePolicy](../../src/Cimt/Reporting/RunOutcome.cs), lines 24–25. Design decision needed for rule priority.

FR-31 says instructions define failure criteria, and defines crash-as-failure as the fallback when no criteria are supplied. The worker and final .NET policy always treat a recorded crash as failure. Neither policy receives a resolved instruction-defined failure rule. A model check cannot change that outcome.

Example: an explicit test asks CIMT to trigger the app's diagnostic crash action, relaunch, and pass if recovery works. Under the present code, the recorded crash forces failure even when the stated expected behavior was observed. The same issue affects instructions that define a narrower set of failures.

Recommended design decision: define which outcome rules instructions may change. Keep crash detection and the three-attempt recovery rule independent from the verdict rule. Either implement a recorded, bounded failure policy that both runtimes enforce, or explicitly amend the requirement so crashes always fail. Do not silently change either contract during a fix.

## Verification and limits

The existing development suite passes: 119 .NET unit tests, 88 Python tests, and 23 CLI/build/example checks, for 230 checks total. These passing tests do not cover the confirmed counterexamples above.

Additional offline probes used real Redactor, ScreenMasker, CheckRecorder, ScenarioRunner completion, worker exit policy, RequirementCatalogue, and RunReportWriter services with invented data. The false-pass example was passed from the Python policy into the real .NET final report writer. Temporary probe files and output are under `/private/tmp/cimt-design-review-*`; the suite log is `/private/tmp/cimt-design-review-checks-20261028.log`.

No OpenAI calls, phone operations, real application builds, or private configuration reads were needed. The review is not real-device acceptance. Existing documented gaps—setup/replay, complete scenario planning, interruption recovery, adapter qualification, Jenkins, and second-Mac acceptance—remain open and are not counted as newly discovered defects here. No new run-folder allocation defect was confirmed in this review.

## Recommended order

1. Fix D1 and D2, adding the small regression cases above.
2. Address D3 and D4 together through explicit objective scope and completion rules.
3. Confirm the input classification and failure-policy decisions in D5 and D6, then update the matching documentation and implementation.
4. Rerun the offline suite and counterexamples before resuming real application acceptance.
