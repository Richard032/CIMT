# UML, requirements and implementation alignment

Reviewed: 26 November 2026. Baseline: `main` at `b2b9ced`, after the rename in PR #23. Scope: all repository Mermaid diagrams, their current explanatory contracts, related agent handover and the remaining rename findings. `feature/vscode-development` is a separate branch; this review does not import its features into main.

## Findings and corrections

| Finding | Correction |
| --- | --- |
| The class diagram invented `KnowledgeLookup.lookup`. | Show the callable `__call__` protocol and its actual arguments/result, independently of the store's app-scoped lookup method. |
| Diagrams omitted registered tool translation and implied only text decoding. | Show the default agent's tool and text routes; neither dispatches a device action. Execution retains the queue and actual observations. |
| Several sequences implied a separate feedback request, or only issue feedback after batches. | Show complete successful, unchanged and failing paths through the next normal decision. Mark feedback delivered only after a reply completes. |
| Some sequences dispatched every queued item, including `done`, as a device command. | Separate device actions from note/recall/recovery/finish; defer `done` behind earlier commands without applying predicted checks. Show failure cancellation before observation. |
| Context descriptions retained the removed local byte allowance, full-tree duplication and a deleted `DecisionRecovery` component. | Document exact AI-owned history selection without local deferral, compact current controls with retrievable full observations, and the actual AiInteraction boundary. |
| Recovery appeared as a pre-dispatch semantic gate. | Show repetition facts after execution and AI-directed recovery on the next request, with no replacement action or acknowledgement gate. |
| Run/finalization diagrams missed proposal independence, usage reporting and report registration. | Show host-owned outcome calculation, renderer-owned usage reading, independent post-run proposal windows and local viewer registration after finalization. Add the knowledge-review/persistence sequence. |
| Historical strict-budget wording conflicted with current FR-24 and the implementation. | Align current requirements, architecture and the validation message with counted-input admission, full settlement and authorized post-run exceptions. No budget behavior changes. |
| Adapter sequence did not clearly distinguish retryable startup errors from other errors. | Show typed retry only, cancellation/deadline bounds, valid empty inventory and the later app-settling delay. Native helper source remains unchanged. |
| The rename lost protection for old generated output folders. | Ignore both `CIMT output/` and `TestPilot output/`; existing private files are not moved or rewritten. |
| Migration documentation claimed development-only files existed on main; the agent handover still described a superseded branch and absent knowledge feature. | Identify branch availability and refresh the handover, PR-only workflow and knowledge/accounting responsibilities. |

The diagrams were corrected where the implementation follows the current approved contract. This review does not restore superseded design behavior, add a layer, change AI action ownership, or treat future approved features as implemented.

## Requirement and source traceability

| Contract | Source checked | Existing validation |
| --- | --- | --- |
| DR-01; FR-95–FR-98: layer boundaries, resources, readiness | `runtime/ai_instructions/`, `test_planning/`, `stopping_policy/`, `device_adapter/`, `ai_interaction.py` | `test_ai_instructions.py`, `test_ai_interaction.py`, `test_device_startup.py`, runtime-policy checks |
| FR-88–FR-90: selection and recovery | `runtime/test_planning/context_memory.py`, `loop_recovery.py`, `runtime/scenario.py` | Context selection, planning regression and scenario suites |
| FR-99/FR-101: FIFO and complete feedback | `runtime/command_reply.py`, `command_queue.py`, `batch_feedback.py`, `observation_recorder.py`, `scenario.py` | Command queue, batch feedback, scenario and report suites |
| FR-102–FR-106: evidence, independent contracts and tools | `runtime/decision_agent.py`, `agent.py`, `agent_tools.py`, `result_review/`, `ai_services.py` | Agent, tool, result-review, independent-agent and request-record tests |
| FR-24 and post-run proposals | `runtime/budget.py`, `run_ui.py`, `result_review/`, `knowledge/proposals.py`; `Execution/RuntimeSteps.cs` | Accounting, proposal and execution lifecycle tests |
| Final outcome and worker protocol | `Execution/RunCoordinator.cs`, `RunFinalization.cs`, `RuntimeResults.cs`, `Reporting/RunDiagnosticsRenderer.cs` | Existing .NET execution/outcome/report tests and fake-worker CLI/lifecycle checks |
| Knowledge lookup, proposal-only AI access and user approval | `runtime/knowledge/`; `src/TestPilot/Knowledge/KnowledgeReports.cs`; `RunEngine.cs` | `test_knowledge.py` and existing knowledge editor/launcher checks |
| Rename privacy and branch scope | `.gitignore`, `docs/testpilot-rename.md`, `GPT continuation.md` | Tracked-text scan, ignore checks, source tree and branch inspection |

All source paths in the table are relative to the repository; .NET paths without a prefix are under `src/TestPilot/`. Test names refer to the existing `tests/` suites.

## Verification and limits

The existing `scripts/check-development.sh` completed successfully on 26 November 2026: 364 .NET unit tests, 634 Python unit tests, 33 runtime-policy checks, 22 fake-tool CLI/lifecycle checks, four simulated build-contract checks, four example checks and six public output-layout checks passed (1,067 total). The existing installed dependencies were used; no dependency was added.

`git diff --check` passed. Local Markdown link targets resolve. Both old and new generated output paths pass `git check-ignore`. Eleven Mermaid diagrams in seven documents were reviewed against source; rendering verification is recorded below when available. No live device test, replay, paid AI request or installation is part of this review. Offline checks establish the recorded contracts, not exploration quality, exhaustive path coverage, provider invoice accuracy or release readiness.

The diagrams describe current-instruction replay over retained builds. Saved-action adaptation, setup automation, Jenkins qualification and representative two-platform/another-host acceptance remain tracked in [release readiness](../release-1.0.md) and [implementation status](../implementation-status.md). This review does not close those gaps by changing requirements or drawing future behavior as current.
