# Hardcoded behavior and project-override audit

Date: 29 October 2026  
Source baseline: 70afdb85f2b50fab3a3755ba324d5698c744292e  
Status: review findings; no runtime or configuration changes made during this audit

## Scope and evidence

Reviewed the .NET CLI/run steps, default build worker, Python device/AI execution, supplied installation/build scripts, and the public FirstRun configuration/build scripts. Private YAML, API keys, and signing material were not read. No CIMT run, real application build, OpenAI request, phone action, or external-repository change was performed.

Installed consistency checks found no differences in 32 files: the host/build-worker assemblies match the local Release build outputs, all 28 installed Python modules match source, and both installed default build scripts match source. No extra installed Python module was found. The current FirstRun adapter matches the corrected example. These checks establish file consistency, not successful application acceptance or proof that no other defect exists.

The removed legacy CuRMiTagger injection was one confirmed defect. The following other assumptions and overrides remain.

## H1 — High: exploration rules are applied to exact scenarios

Evidence: [system prompt](../../runtime/action_prompt.py#L40) and [completion policy](../../runtime/scenario.py#L222).

The shared prompt always asks the model to explore reachable buttons, menus, and scrolling paths. The host then prevents completion while any observed control/state combination remains unactivated. Neither rule checks whether the instructions requested an exact scenario or broad exploration.

For example, instructions may ask to press Save and verify the value. If Delete is also visible but unrelated to the scenario, not activating Delete still blocks completion. This carries the original all-buttons example into generic testing. It conflicts with FR-14/FR-25 and is the previously recorded, still-open D4 finding in the [design review](2026-10-28-design-contract-review.md).

Correction needed: make the retained instruction objectives and permitted exploration scope authoritative. Report observed controls separately; only require exploration coverage when the instructions request it. Tests must distinguish Save-only work from an all-buttons objective.

## H2 — Medium: the default worker overwrites explicit build properties

Evidence: [EffectiveProperties](../../tools/Cimt.BuildWorker/BuildCommands.cs#L18) and [current tests](../../tests/Cimt.UnitTests/BuildWorkerTests.cs#L8).

The worker copies the supplied property map, then unconditionally assigns AndroidPackageFormats=apk on Android, and RuntimeIdentifier=ios-arm64, BuildIpa=true, ArchiveOnBuild=true on iOS. These become global command-line MSBuild properties for publish and metadata queries. Explicit conflicting YAML properties and project values lose to these assignments.

APK/physical-iPhone outputs were an intentional documented default-worker profile. The problem is treating these defaults as unconditional overrides even when the user explicitly supplied another value. The current Android unit test deliberately supplies aab and expects the actual command to use apk; it checks that the input dictionary was not mutated rather than that its requested behavior was preserved. This is similar to the old tagger test validating the implementation's assumption.

This needs alignment with FR-42 and FR-58. Defaults should fill missing values. If a requested output cannot be installed by CIMT, reject it with a clear error or require an explicitly selected supported build profile/replacement script. Do not silently replace a conflicting user setting. The audit has not changed this behavior.

## H3 — Medium: a crash always determines failure, regardless of instruction criteria

Evidence: [Python verdict](../../runtime/check_results.py#L81), [worker exit calculation](../../runtime/device_runner.py#L73), and [host verdict](../../src/Cimt/Reporting/RunOutcome.cs#L25).

A recorded crash forces failure. There is no resolved instruction-defined failure policy supplied to those decisions. A test that intentionally triggers a diagnostic crash and expects successful recovery can therefore fail even when its stated expected behavior occurred.

This is the previously recorded, still-open D6 issue. FR-31 gives testing instructions authority over failure criteria, while the implementation hardcodes crash-as-failure. A bounded explicit failure-policy contract or a product requirement decision is needed; crash detection and the three-matching-attempt recovery rule should remain separate from expected-result evaluation. This review does not relax either rule.

## H4 — Workflow restriction: external applications are blocked by a fixed list

Evidence: [foreground-app restriction](../../runtime/scenario.py#L158) and [prompt](../../runtime/action_prompt.py#L41).

Only the tested app and several fixed system/permission-app identifiers are allowed. Other foreground apps end the objective as unexplored work. There is no configuration for a legitimate browser sign-in, app-to-app handoff, or device-settings workflow requested by the testing instructions.

Keeping actions within the intended task is sensible, but the implemented scope is fixed rather than resolved from the requested workflow. This is a generic-capability restriction, not another build-tool injection. Define the supported workflow/allowance contract before expanding it, and keep unsupported paths explicitly incomplete.

## Application-specific changes still present in FirstRun

These are visible input/example behavior, not additional hidden calls in the generic build worker:

| Item | Current behavior | Consequence |
| --- | --- | --- |
| Resource-copy adaptation | [Example build.sh](../../examples/econ-button-crash/build/build.sh#L8) replaces one exact Windows copy Exec with MSBuild Copy inside the disposable project clone. | This still edits the cloned project. It is logged, leaves other bytes/steps intact, and is documented in FR-58. It should remain an explicitly selected application adapter rather than become a generic CIMT rule. |
| Application identities | FirstRun/application.yaml explicitly supplies ApplicationId for each branding/platform; the tracked example has the same type of values. | Those YAML properties override project-selected IDs. They may become stale when selecting another branch and must be reviewed as user configuration. They are not fixed IDs in the generic runtime. |
| Target labels | FirstRun names targets Debug_Generic/Debug_Pride but selects Release_Generic/Release_Pride as configuration. | The labels do not choose Debug builds. CIMT follows configuration; console messages currently display only the labels. No values were changed in this audit. |

No additional CuRMiT/ECON-specific executable invocation was found in the generic .NET/Python run/default-build paths. That is a scoped search/review result, not a guarantee about every third-party tool or future project.

## Other explicit implementation limits

- The [device runner](../../runtime/device_runner.py#L45) currently executes one combined objective per target/device. Explicit scenario decomposition and a complete instruction-objective inventory remain unfinished. The [earlier D3 finding](2026-10-28-design-contract-review.md) explains why a missing instruction objective can escape completion accounting. These are not new discoveries or completed features.
- [Budget](../../runtime/budget.py#L10) accepts one validated model snapshot and USD. It rejects other configured combinations; it does not silently substitute a model. This is documented as a current support limit. No price or model-access verification was performed during this audit.
- [Action requests](../../runtime/action_prompt.py#L97) include only the latest 24 actions and use fixed low reasoning effort and a 2,048-token output cap. Those are implementation choices, not per-run settings; full historical actions remain in local evidence. Long scenarios need qualification of this context policy.
- [The pilot installer](../../scripts/setup-prerequisites-macos.sh#L7) requires its pinned Xcode/profile. Manifest-driven setup remains unfinished. An installed profile is not proof that every MAUI repository/toolchain combination is supported.

## Rules that are intentional product requirements

At most two active devices, startup-only device enumeration, reset before each scenario, strict shared budget/deadline enforcement, three matching crash attempts, and deletion of owned temporary work after execution were explicitly specified. They should not be counted as unauthorized assumptions merely because their values are fixed. The verdict-policy issue in H3 is separate from the approved recovery count.

## Outcome and next work

The implementation still contains assumptions from the initial example. H1 and H2 are the closest remaining cases to the tagger mistake: generic execution imposes behavior instead of preserving the requested scope or settings. H3 and H4 require explicit policy alignment. The copy adaptation and app-ID values remain visible application-specific inputs.

This audit records these differences without changing requirements to fit the code. No tests were added or run because behavior was not changed; conclusions come from source review, existing test inspection, and installed-file comparisons. A fix should use the existing test projects/frameworks and verify the user's required behavior, including counterexamples, rather than encode another workaround as the expected result.
