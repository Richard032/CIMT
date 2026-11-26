# AI-owned context and recovery

**Current decision context:** Each request contains original instructions, fresh masked evidence, feedback, and selected scenario records. Previous chat messages are not sent. The AI may explicitly select registered historical screenshots.

> Contract and dated evidence: later refinements supersede earlier wording. Recorded test counts and live observations belong to their stated dates, not the current full-suite result. See [implementation status](implementation-status.md), [release readiness](release-1.0.md), and the [current usage guide](product-guide.md).

Date: 31 October 2026. Requirements: FR-88–FR-97. Source implementation and offline validation; installation and live acceptance are separate.

## Responsibility

FR-96 removes response-format evaluation and three-attempt correction exhaustion. See [AI Resource Exchange](ai-resource-exchange.md) for command decoding, optional records, original reply retention and resource feedback. Earlier schema/quote/ID prerequisites are superseded.

The AI exclusively decides what history and context to retain in working memory, summarise, omit from a request or retrieve. TestPilot stores complete records and resolves the AI's exact selections. It does not rank relevance, choose a history window, silently truncate records or choose app recovery actions. Original instructions and requirements remain authoritative. An AI summary is working memory, not a replacement correctness oracle.

Test Planning and Exploration stores the records and AI selections. AI Instruction and Context supplies those retained records and fresh masked screen/control information without receiving replies. ContextMemory applies selections, TestPlan owns task/source identity, ExplorationMemory/ApplicationMap hold observations and LoopRecovery holds recovery requests. Execution owns device calls, storage, report publication, privacy and mechanical resource limits. All inference uses the configured model and shared budget/deadline.

## Context contract

FR-95 extends the AI-ownership boundary to ordinary action selection. The AI may select a ref or coordinate from current evidence, earlier observations or its expectations. The latest accessibility tree is evidence, not an action whitelist. TestPilot forwards supported requests and records adapter-reported interaction rejections for the next AI decision, without choosing another action. It still enforces technical execution and privacy constraints. An earlier ref may be stale; its requested identity and returned outcome are retained without claiming it was an observed control or a completed action. Credential entry requires a verified maskable field before typing any secret.

Context is optional under FR-96. Omitting it or returning null retains the previous AI summary/selection without regenerating it. To change it, return:

```json
{
  "summary": "Settings was visited. Saving has not yet been checked.",
  "includeAll": ["tasks"],
  "records": [
    { "collection": "actions", "id": "latest" },
    { "collection": "states", "id": "@0:3" }
  ]
}
```

Available collections are commands, actions, decisions, observations, screenshots, tasks, paths, states, transitions, requirements, checks, configuration, coverage and routes. The request's catalogue gives their full counts. Bootstrap supplies available records before the AI has made a selection. After that, an empty selection omits historical record content while keeping the AI's summary, collection counts, authoritative instructions and current masked evidence. It does not delete anything locally.

Task, requirement, state and path addresses use their stable IDs. Configuration uses its generated control ID. Commands, accepted decisions, actions, checks and transitions also have zero-based addresses. Commands retain batch/order/status and any reason why they were not executed; they are plans until dispatch. Every collection accepts @0 for its first record and @3:7 for the exact half-open range selected by AI. Unknown/out-of-range addresses return resource feedback without clipping to a different selection or blocking commands. latest follows the newest record only when explicitly selected by AI. Routes use the task ID and contain verified observed edges to that task's AI-selected targetState. Empty routes are not evidence of successful navigation.

An action of recall changes context without a tap, swipe, wait, restart or reset. Remaining commands in its batch run first; the updated selection is used when execution next requests a decision. This lets AI inspect omitted records before acting. Accepted response/selection records remain in decisions, including recall and recovery requests. Device action history remains in actions. observations retains the already captured masked UI data; screenshots exposes stable addresses of saved masked images; the AI can retrieve an older screen without relying on its summary or adding a new device query. Historical pixels are sent only when explicitly selected by AI, are labelled as historical, and must still match the registered image digest. Identical current/historical pixels share one image payload. Evidence-name reuse preserves earlier images instead of replacing them. Retrieval and filtering consume API budget; update the summary/selection with normal decisions when possible instead of adding a separate filtering call to every step.

Current UI evidence, execution scope, fixed permission/safety instructions and collection counts form the protocol frame. These are not a host-selected relevance subset. AI may select current or earlier refs; the adapter returns whether the requested ref is usable. Full requirement records remain available even when AI omits them from its working context; unresolved catalogue items still prevent complete coverage.

## Capacity and cost

The selected history is sent without an automatic 64 KiB deferral. The AI can request individual records to keep its context focused. Provider context limits apply to the whole request, including source inputs, current evidence, and selected historical screenshots. If the request is too large or the provider fails, TestPilot reports the actual failure rather than silently dropping selected records. All selected image input remains covered by the provider-counted input reservation.

Supported pricing profiles with prompt-cache controls place an explicit cache breakpoint after stable system instructions. Actual reuse depends on provider eligibility and matching context; it is not assumed. Budget records input/output tokens and optional cached-token counts for each settled request. Missing cache details are unavailable, not zero. The conservative accounted spending bound continues to charge validated upper rates without relying on optional cache discounts. Context-selection and recovery requests use the same reservation/cancellation/deadline path as ordinary decisions.

## Recovery contract

After executed unchanged attempts or repeated traversals without discovery, TestPilot supplies repetition facts and a recovery notice in the next instruction with fresh masked evidence. This does not veto an AI-selected command. A signal does not itself prove a functional defect or an unproductive loop. The AI determines whether repetition is intentional and chooses its revised approach. AI may also return recover with recovery id -1, decision replan and a reason to request this workflow before counters signal.

Every pending request has a stable ID. Its response includes:

```json
{
  "id": 0,
  "decision": "replan",
  "reason": "Inspect earlier settings outcomes, then try the unvisited selector."
}
```

Suggested recovery decisions are replan, intentional or blocked, with an explanation. These are optional records, not permission to act. The AI can issue recall or notes while recovery remains pending. A command can continue without a structured acknowledgement; TestPilot records that fact without inventing an explanation for the AI. repeatInstruction/repeatReason can explain deliberate reproduction.

Each renewed repetition signal opens a new request. There is no fixed three-episode semantic recovery stop. The AI can still make poor choices; time/budget/cancellation bound execution. FR-96 removes schema/source evaluation and the three-response correction limit. Transport, masking, storage and refusal/incomplete-response failures keep their existing policy. Three matching crashes remain a separate crash-recovery limit. TestPilot does not choose a replacement button, restart/reset the app or discard history for loop recovery.

AI done/complete ends interaction. TestPilot preserves unresolved plan, path and requirement work and reports incomplete coverage; it does not choose an extra reconsideration request. The AI owns when to finish and should explain blockers.

## Identity and mapping corrections

Optional checks use taskId and source/requirement IDs for linking; an unknown reference stays unbound without blocking a command. Display subjects can be redacted without breaking identity. CheckRecorder assigns monotonic check IDs and publishes before image persistence. Checks and observations remain recorded across recovery capture. A repetition notice does not veto an executable AI action; actual dispatch outcomes determine whether an app action occurred. TestPlan applies each check once, keeps a new blocked status when there is no new assessment, and preserves failure/override precedence.

Map identity distinguishes screen structure, observed input values and last-observed configuration. Passive text changes remain full masked UI observations, fingerprints and normal screen evidence without multiplying structural button paths. A changing label is still visible to AI and can be meaningful; the host does not decide its correctness or remove the source observation. Configuration learning refines observed navigation relationships. A changed known value does not globally alias an earlier configuration variant. Verified routes remain guidance. Current evidence is supplied, while the AI may select earlier refs or expected targets under FR-95.

## Reporting and validation

HTML shows AI-selected working context, source-linked tasks, path scope, the application map and AI-directed recovery. Recovery entries identify trigger, reason, AI decision/explanation and waiting/continued/blocked status. A waiting entry after cancellation means no completed recovery decision was recorded. JSON retains full redacted AI replies, optional decisions, selections and resource feedback; HTML exposes the original replies as escaped text. The run overview includes available input/output/cache counts and request-purpose usage records. Both report boundaries redact text while preserving typed IDs. Historical reports remain unchanged.

Existing offline suites cover AI-only selection, exact paging, action-free retrieval, selected context without local byte deferral, task identity after redaction, historical-check replay, passive status changes, route refinement, repeated recovery beyond three episodes, AI-detected loops, cancellation, reporting and shared accounting. These do not establish live exploration quality or cost savings. Future user-authorised comparisons should measure requirement completion, useful coverage, repeated actions, recovery success, lost evidence, note-only replies, latency and total usage including filtering/recovery. No new TestPilot app run is part of this source increment. FR-97 keeps Mobile MCP and separates the input-only layer from command decoding and execution; see [AI Instruction and Context](ai-instruction-context.md).

## Sequence

```mermaid
sequenceDiagram
    actor User
    participant Run as Execution
    participant Inputs as AI Instruction and Context
    participant Memory as Planning and Exploration
    participant Agent as DecisionAgent
    participant Device as Device Adapter
    participant Report as Local records and reports

    User->>Run: Configuration, instructions and requirements
    Run->>Memory: Initialize source-linked records
    Run->>Device: Prepare app and capture initial masked evidence
    loop While another decision is allowed
        Run->>Inputs: Refresh evidence and assemble next request
        Inputs->>Device: Capture fresh masked observation
        Device-->>Inputs: Current screen and image
        Inputs->>Memory: Retrieve exact AI-selected records and recovery notice
        Memory-->>Inputs: Selected records, counts and unavailable-address feedback
        Inputs-->>Run: Original inputs, current evidence and mandatory pending batch results
        Run->>Agent: Decide under shared cancellation, deadline and counted-input budget gate
        Agent-->>Run: Commands and optional AI-owned context or planning records
        loop Commands in FIFO order until handoff or stop
            alt Recall or note
                Run->>Memory: Retain AI selection and records without a device action
            else AI requests recovery
                Run->>Device: Refresh masked evidence
                Run->>Memory: Record recovery notice and leave batch tail unexecuted
            else First-command done
                Run->>Run: Apply single advisory completion review if not already used
                Run->>Memory: Retain unresolved work when finishing
            else Deferred done behind actions
                Run->>Memory: Retain actual batch path for a new decision
            else Device action
                Run->>Device: Execute selected action and capture outcome
                Device-->>Run: Actual outcome and masked observation
                Run->>Memory: Record action, transition and repetition facts
                opt Repetition detected after execution
                    Run->>Memory: Open recovery notice and leave pending commands unexecuted
                    Note over Run,Agent: Next normal request includes fresh evidence; no semantic acknowledgement gate
                end
            end
        end
        Run->>Report: Publish decisions, ordered results, evidence, recovery and usage
    end
    Run->>Report: Finalize outcome, stopping reason and remaining work
    Report-->>User: HTML report
```

## OpenAI guidance used in review

- [Context management](https://developers.openai.com/cookbook/examples/agents_sdk/session_memory): balance useful continuity, context size and summarisation risks.
- [Compaction](https://developers.openai.com/api/docs/guides/compaction): reduce long-running context while carrying forward working state.
- [Tool design](https://developers.openai.com/api/docs/guides/function-calling): keep mechanical work in code and tool contracts clear.
- [Prompt caching](https://developers.openai.com/api/docs/guides/prompt-caching): use eligible stable prefixes and measure actual reuse.
- [Agent evaluation](https://developers.openai.com/api/docs/guides/agent-evals): compare workflow traces and representative outcomes.

Exclusive AI ownership of relevance is TestPilot's approved product choice, not an OpenAI requirement or a claim of certified conformance.

## Requirement-to-implementation mapping

| Requirement | Implementation | Existing-suite validation |
| --- | --- | --- |
| FR-88: AI relevance ownership | ContextMemory, TestPlanner, ActionPromptBuilder | ContextSelectionTests, MappingPromptTests |
| FR-89: every detected loop recovers | LoopRecovery, AiInteraction, ScenarioRunner | ScenarioTests: repeated recovery, AI-detected loops, recall, blocking and cancellation |
| FR-90: efficient recoverable context | ContextMemory paging/retain, ScenarioEvidence, Agent | HistoricalImageTests, scenario screenshot selection |
| FR-91: stable task/check identity | TestPlan, CheckRecorder, typed redactors | PlanningRegressionTests, redaction suites |
| FR-92: mapping/progress corrections | screen_model, ApplicationMap, ExplorationMemory | PlanningRegressionTests, existing map/control tests |
| FR-93: reports and usage | PlanningHtmlRenderer, RunDiagnosticsRenderer, Budget | PlanningReportTests, RequestUsageTests, existing policy/CLI suites |
| FR-94: evidence-based qualification | Offline suites and retained request metrics | Offline validation passed; live comparison remains pending |

FR-99 adds ordered command batches in execution, outside the input-only layer. The commands collection makes unexecuted work retrievable using the same AI-owned selection rules. An unexecutable command cancels the remaining batch and supplies its actual issue on the next normal AI request. Successful batches add no acknowledgement call. Recovery can defer its remaining commands to a fresh AI decision instead of silently resuming them. See [command queue](command-queue.md).

FR-101 makes new batch execution results mandatory resources in the next normal decision request, including unchanged steps, intermediate observations, warnings/errors and cancelled commands. The AI still exclusively chooses older context relevance; complete historical batches are retrievable through batches. A finish behind commands hands results back instead of evaluating future outcomes. No separate acknowledgement request or extra model is added. See [batch feedback](batch-feedback.md).
