# Complete ordered batch feedback

Implements FR-101 / AC-71. The source is verified offline; installation and live qualification are separate. No public command, configuration field, dependency, provider or third-party tool change is required.

## Execution contract

Before the next testing decision, CIMT supplies every result of the previous batch through the normal AI request. Successful batches receive the same complete path feedback as unsuccessful batches, without an acknowledgement-only inference call. AI decides the meaning of observations and whether to continue, recover or finish.

The sequence is:

```text
Initial observation → Command 1 → Result 1 → Command 2 → Result 2
```

Each result becomes the previous observation for the next event. A batch has one initialObservation reference, followed by ordered path records. There is no separate before image/UI payload per command. A path such as A → B → C → A retains B and C even though its final screen matches its initial screen.

Command results include the action and requested target, actual execution status, resulting observation reference, UI change classification, warnings and errors. The observed target label is included when known. No credential value or typed text is copied into the compact target. Complete original commands remain in the existing redacted command records.

The classifications are changed, no observed change and observation unavailable. Comparing complete masked UI/image identities records an observed difference; it does not prove the command caused it, that it is relevant, or that behavior is correct. Structural screen identities and existing repetition signals remain separate. Controls such as recall or deferred finish are marked not applicable for UI change. Cancelled/unexecuted commands have no manufactured after-observation. A successful dispatch does not pass a requirement.

An independent change found during a fresh observation or existing recovery capture is a separate path event in its actual position. CIMT does not add a new polling loop to guess unseen transitions. Every registered intermediate UI remains available through its full observation ID in the existing catalogue.

## References and delivery

BatchFeedback stores scenario-local ordered data without provider, device or filesystem calls. ObservationRecorder registers verified masked frames and factual system warnings. ScenarioEvidence owns contained local files and reuses identical image bytes and masked UI records. Different observations cannot overwrite an earlier UI file when a name is reused. Registered evidence is checked before reuse; altered/unavailable evidence raises an actual resource failure. All events remain present even when their evidence references are identical.

Each resolved batch contains its initial reference, ordered path, referenced observation metadata and warning records. Observation metadata points to the registered screenshot and full masked UI record rather than embedding pixels or full UI trees. New paths appear in top-level batchFeedback, and currentWarnings supplies present system warnings, including before the first batch. These resources remain present when optional history is omitted or exceeds its separate capacity allowance.

A completed reply marks pending feedback supplied to AI. If a run stops before another request is allowed, results remain local with explicit unsupplied delivery status. Shared time, spending, cancellation, provider/privacy and infrastructure rules remain authoritative; they are not bypassed to send feedback. Actual requests retain normal budget reservation/accounting. Whole provider limits still apply; CIMT does not trim path steps to make them fit.

Older batches remain available through the batches collection and exact AI-selected IDs/ranges. Their full UI and registered historical pixels remain available through the existing observation/screenshot resources. AI exclusively selects historical relevance; new execution feedback is a required resource frame, not a host-selected history summary.

## Batch finish and objective finish

An action batch ends by returning its commands. Execution then supplies actual results for the next AI decision. A done command behind other commands is retained as deferred batch handoff. Its predicted final checks, plan and completion are not applied. Later commands remain not executed, and the next normal request provides the full actual path.

AI can end an objective by returning done first in a new reply after reviewing actual feedback. Later commands in that reply remain unexecuted. This is mechanical sequencing, not semantic response approval or a host choice of test strategy. AI must not append a blocked finish merely because results of proposed commands have not arrived yet.

If a command cannot execute, existing whole-queue cancellation remains. The failed command and every cancelled command appear in path feedback with their actual states/reasons. No cancelled command resumes automatically. Existing crash/repetition recovery can defer pending commands for another AI decision; its full results remain visible too.

## Android ANR warnings

Device Adapter recognizes the Android system ANR Wait resource identifier, android:id/aerr_wait. It does not classify ordinary app text or a crash-close button alone as ANR, and does not require an English dialog label. Recognition depends on accessible system metadata; no OCR or AI classifier is added.

On first observation of an episode, record a warning with device, UTC time, target and execution step in the terminal, saved activity log and HTML. A persistent dialog references that warning in each affected result instead of flooding the log; after it clears, a later occurrence gets a new warning. Only the fixed warning description is logged, not raw screen text.

An ANR warning alone does not set a failed verdict, manufacture a crash, choose Wait/Close, or stop testing. Fresh verified Android system ANR UI remains inside the permitted observation workflow. AI decides any app action under the original instructions. Independent process termination, genuine crash diagnostics, device failures, privacy errors and limits retain their existing policies.

## Report and privacy

BatchFeedbackHtmlRenderer shows warnings and complete ordered paths in each device scenario, independently of optional details. Initial state, command/target, execution status, UI result, resulting observation, evidence and warning/error information are distinct. A pending plan is not a performed action. Unsupplied results remain distinguishable from results supplied to AI. Links use the existing contained report evidence helpers; text is redacted and HTML-escaped.

Python RecordRedactor and .NET ExecutionRedactor preserve generated identities, typed statuses, observation references and warning codes while scrubbing free text. Historical reports are unchanged. Install matching .NET/Python files together; the existing installer includes the new modules and full Device Adapter package. Operational installation/replay notes are recorded in installation.md and implementation-status.md; the owner approved publishing them with this documentation.

## Existing-suite verification

Python unit tests cover full cycles, unchanged/missing observations, separate independent events, exact historical retrieval, cancelled tails, delivery/limits, deferred versus first-command finish, ANR identifiers/episodes, warning logs, evidence reuse and tamper rejection. Existing xUnit tests cover complete paths, mandatory warnings, redaction/escaping and contained links. Runtime-policy and fake-tool CLI/lifecycle checks retain the public execution boundaries. No new test project or alternative harness is introduced. Offline checks do not prove live ANR handling, all-path coverage, model compliance, latency or savings.

```mermaid
sequenceDiagram
    participant AI as Configured Model
    participant Inputs as AI Instruction and Context
    participant Run as Execution
    participant Queue as Scenario Queue
    participant Device as Device Adapter
    participant Facts as Batch Feedback and Evidence
    participant Report as Local Log and HTML

    Run->>Inputs: Sources, current masked observation and pending complete batch results
    Inputs->>AI: Normal decision request; optional history chosen by AI
    AI-->>Run: Ordered command objects
    Run->>Queue: Store batch
    Run->>Facts: Register initial observation once
    loop Until batch ends, recovery or execution stop
        Queue-->>Run: Next command
        Run->>Device: Execute under existing limits/privacy
        Device-->>Run: Actual outcome and verified masked observation
        Run->>Facts: Command, status, result reference and warnings/errors
        opt Independent change detected by an existing observation
            Run->>Facts: Separate ordered observation event
        end
        opt Android system ANR observed
            Facts->>Report: Warning with device, time and step
        end
        opt Command cannot execute
            Run->>Queue: Cancel every pending command
            Run->>Facts: Retain failure and cancelled command results
        end
        opt Done follows other commands
            Run->>Facts: Defer finish; do not apply predicted checks
        end
    end
    Run->>Report: Save complete path and evidence references
    alt Another decision is allowed
        Run->>Inputs: Complete new path and current evidence
        Inputs->>AI: Next normal request, including success/unchanged results
        AI-->>Run: Continue, recover or first-command done using actual results
    else Stopping/privacy rule prevents another request
        Run->>Report: Retain unsupplied results and stopping reason
    end
```
