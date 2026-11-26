# Current TestPilot architecture diagrams

Reviewed: 26 November 2026 against `main` at `b2b9ced`, with the documentation corrections in this PR. These diagrams describe implemented responsibilities and flows, not future acceptance claims. [Architecture decisions](architecture.md) preserve design history; later approved [requirements](requirements.md) supersede earlier increments. The [alignment review](reviews/2026-11-26-uml-alignment.md) links requirements, source and validation.

## Layers and dependencies

```mermaid
flowchart TD
    CLI["CLI, settings and machine lock<br/>src/TestPilot/Cli and Settings"]
    Host["Run orchestration<br/>RunEngine and Execution"]
    Build["Application build worker<br/>tools/TestPilot.BuildWorker"]
    Worker["Device scheduling and scenario execution<br/>runtime/run_ui.py and scenario.py"]
    Inputs["AI instruction and context<br/>runtime/ai_instructions"]
    Plan["Test planning and exploration<br/>runtime/test_planning"]
    Device["Device adapter and masking<br/>runtime/device_adapter"]
    Stop["Stopping policy<br/>runtime/stopping_policy"]
    Tools["Mobile MCP and unmodified native helper"]
    Agent["DecisionAgent contract<br/>runtime/decision_agent.py"]
    Default["Default Agent and tool translation<br/>runtime/agent.py and agent_tools.py"]
    Review["Evidence ledger, completion review and instruction proposals<br/>runtime/result_review"]
    Provider["Provider transport, journal and accounting<br/>runtime/ai_services.py and budget.py"]
    Knowledge["App knowledge, proposals and approval<br/>runtime/knowledge"]
    Editor["Local knowledge server<br/>Report review and standalone editor"]
    Files["Masked evidence and worker files<br/>Results, batch paths, requests and usage"]
    Finish["Outcome finalization<br/>Execution/RunFinalization.cs"]
    Report["JSON and HTML rendering<br/>src/TestPilot/Reporting"]

    CLI --> Host
    Host --> Build
    Host -->|Versioned worker request| Worker
    Host -->|Discovery and owned-helper cleanup| Tools
    Device -->|Device communication| Tools
    Worker --> Inputs
    Inputs --> Plan
    Inputs -->|Fresh masked observation| Device
    Worker -->|Queue and action execution| Device
    Worker --> Stop
    Worker --> Agent
    Default -.->|Implements| Agent
    Default --> Provider
    Default -->|Optional read-only lookup| Knowledge
    Worker --> Review
    Review -->|Default AI implementations| Provider
    Worker -->|Post-run knowledge proposal| Knowledge
    Knowledge -->|Default proposal generator| Provider
    Worker --> Files
    Host --> Finish
    Files -->|Validated execution snapshot| Finish
    Finish -->|RunReportData| Report
    Files -->|Latest usage and retained evidence| Report
    Host -->|Register finalized report| Editor
    Editor -->|User-approved writes and direct edits| Knowledge
```

Execution owns the queue, device actions, scenario state and stopping. The four dedicated runtime layers keep their separate folders under DR-01. Planning stores supplied observations and AI-owned plans/selections; it does not choose tests. The input layer queries fresh masked observations and assembles context; it does not decode replies or dispatch actions. Device Adapter owns device I/O and readiness, while Stopping Policy owns failure scope. The other boxes are components and contracts, not additional layers.

The default agent translates registered tool calls or text replies into commands. Tool translation does not operate the device. Completion review is advisory and runs at most once per scenario. Instruction and optional knowledge proposals run after cleanup using retained evidence. All default AI services use the configured model and shared ledger; post-run proposals have separate bounded time windows and may exceed the testing budget under FR-24. See [device replacement boundaries](device-adapter.md#replacement-boundaries).

## Class and interface diagram

```mermaid
classDiagram
    class DecisionAgent {
        <<interface>>
        +check_access() None
        +decide(DecisionRequest request) dict
    }
    class KnowledgeLookup {
        <<interface>>
        +__call__(query, entry_id) list_or_dict_or_None
    }
    class CompletionReviewer {
        <<interface>>
        +review(EvidenceRequest request) CompletionReview
    }
    class ProposalGenerator {
        <<interface>>
        +propose(EvidenceRequest request) ProposalResult
    }
    class IRunReportWriter {
        <<interface>>
        +Write(RunState state, RunReportData data) void
    }
    DecisionRequest --> KnowledgeLookup : optional read-only callback
    DecisionAgent <|.. Agent
    CompletionReviewer <|.. CompletionCritic
    ProposalGenerator <|.. OpenAiProposal
    IRunReportWriter <|.. RunReportWriter
    AiInteraction --> DecisionAgent
    AiInteraction --> DecisionRequest : copied inputs and shared service hooks
    ScenarioRunner --> CompletionReviewer
    CompletionReviewer ..> EvidenceRequest
    ProposalGenerator ..> EvidenceRequest
    InstructionProposal --> ProposalGenerator
    Agent --> AiServices
    CompletionCritic --> AiServices
    OpenAiProposal --> AiServices
    AiServices --> Budget
    RunCoordinator --> RunFinalization
    RunFinalization --> RuntimeResults
    RunFinalization --> RunOutcomePolicy
    RunFinalization --> IRunReportWriter
```

These Python interfaces are structural `Protocol` contracts. `KnowledgeLookup` is callable, not an object with a `lookup` method: its keyword-only arguments default to empty strings and its return type is `list | dict | None`. `DecisionRequest` carries copied context plus shared recording, budget, deadline and cancellation hooks. `EvidenceRequest` carries redacted evidence, an optional request observer and cancellation check. `CompletionReview` and `ProposalResult` specify the independent review/proposal replies. Knowledge proposal generation is a separate implementation in `runtime/knowledge/proposals.py`; it is not an implementation of `ProposalGenerator`.

## Run, replay and finalization sequence

```mermaid
sequenceDiagram
    participant CLI as CommandApplication
    participant Engine as RunEngine
    participant Host as RunCoordinator
    participant Build as Build workflow
    participant Worker as Python worker
    participant Files as Retained results and usage
    participant Final as RunFinalization
    participant Report as RunReportWriter
    participant Web as KnowledgeReports and local server

    CLI->>CLI: Acquire machine lock, validate settings, allocate run/report
    CLI->>Engine: Start run or retained-build replay
    Engine->>Host: Execute ordered steps
    Host->>Host: Load text inputs and check installed runtime
    opt Replay
        Host->>Build: Load and verify matching retained builds
    end
    Host->>Host: Prepare work, optional OpenAI preflight checkpoint
    Host->>Worker: Preflight without inference
    Host->>Host: Discover startup devices
    opt Run
        Host->>Host: Optional repository/build checkpoint
        Host->>Build: Clone selected branch, initialize submodules, build targets
        Build-->>Host: Build outcomes and retained artifact metadata
    end
    Host->>Host: Optional AI-testing checkpoint when builds are usable
    Host->>Worker: Execute eligible pairs, at most two device workers
    Worker->>Files: Save masked results, batch paths and usage incrementally
    opt Interim update
        Host->>Final: Read current results and calculate provisional outcome
        Final->>Report: Write snapshot
    end
    Worker-->>Host: Device execution exit code
    Host->>Host: Clean up owned helper and retain logs
    Host->>Worker: Authorized post-run proposal request with independent timeout
    Worker->>Files: Read partial results and restore shared usage ledger
    Worker->>Files: Save instruction proposal or unavailable status
    opt Learning enabled
        Worker->>Files: Save independent knowledge proposals or unavailable status
    end
    Worker-->>Host: Proposal worker finished
    Note over Host,Worker: Proposal failure keeps the test verdict, host saves a fallback if needed
    Host->>Final: Finalize run
    Final->>Files: Read and validate execution snapshot
    Final->>Final: Calculate coverage, outcome and exit code
    Final->>Report: Write final JSON and HTML with RunReportData
    Report->>Files: Read latest usage ledger and retained diagnostics
    Final-->>Host: Calculated exit code
    Host-->>Engine: Final result
    Engine->>Web: Register finalized report when viewer is installed
    opt Learning enabled and viewer available
        Web-->>Engine: Interactive local report URL
    end
    opt Interactive macOS terminal
        Engine->>Engine: Open interactive URL or static report
    end
    Engine-->>CLI: Return exit code, release machine lock
```

Exceptions skip later execution steps but still reach cleanup, proposal/fallback and finalization where possible. A configured interactive checkpoint can prevent proposal inference if AI testing was never authorized. Hard process termination or storage failure cannot guarantee finalization. Viewer registration/browser failures do not change the calculated test outcome. Replay reuses retained artifacts and runs current instructions; saved-action adaptation remains unfinished. See [run engine](run-engine.md) and [worker protocol](worker-protocol.md).

## Decision sequence

```mermaid
sequenceDiagram
    participant Run as ScenarioRunner and AiInteraction
    participant Inputs as InstructionContext
    participant Device as Device Adapter
    participant Agent as Default Agent
    participant Service as AiServices and Budget
    participant Knowledge as Read-only app knowledge
    participant Queue as CommandQueue
    participant Critic as CompletionReviewer
    participant Records as Scenario evidence and batch feedback

    Run->>Inputs: Prepare next decision only when queue is empty
    Inputs->>Device: Capture fresh verified masked UI and image
    Device-->>Inputs: Current observation
    Inputs-->>Run: Sources, exact selected history and complete pending batch paths
    Run->>Agent: DecisionRequest with copied inputs and shared hooks
    Agent->>Service: Journal, count exact input, admit counted input cost, infer
    Service-->>Agent: Reply and usage settlement
    opt Learning enabled and AI requests knowledge
        loop At most five read-only lookups
            Agent->>Knowledge: Search or retrieve app entry
            Knowledge-->>Agent: Approved records or unavailable feedback
            Agent->>Service: Counted and accounted lookup follow-up request
            Service-->>Agent: Next reply
        end
    end
    Agent-->>Run: Translated tool call or fully decoded text batch
    Run->>Records: Mark previously pending feedback delivered
    Run->>Queue: Append commands in received order
    Run->>Records: Save received batch and initial observation once
    loop Each queued command under shared limits and foreground checks
        Run->>Queue: Take next command
        alt Done behind earlier commands
            Run->>Records: Defer finish without predicted checks, retain unexecuted tail
        else First-command done
            opt No earlier completion review
                Run->>Critic: Review redacted evidence under shared budget/deadline
                Critic-->>Run: Agree, advise reconsideration or unavailable
            end
            Run->>Records: Finish or record advisory reconsideration
        else Device action
            Run->>Device: Execute AI-selected command
            Device-->>Run: Dispatch outcome and post-action observation
            Run->>Records: Ordered result, evidence, warnings and repetition facts
            opt Command failed or recovery requested
                Run->>Queue: Cancel failed batch tail or mark recovery tail unexecuted
            end
        else Note, recall or recover
            Run->>Records: Handle without device action, retain context/recovery information
        end
    end
    Note over Run,Records: Next normal decision receives every pending path, including successful and unchanged steps
```

The loop ends on batch handoff, recovery, AI finish or an execution stop; it does not run an unexecuted tail. A malformed text reply becomes a retained note with mechanical feedback; no prefix is dispatched. Output-limit replies allow one separately accounted shorter retry. The SDK stops at the first registered tool call and execution owns its command. There is no local history-size gate, relevance filter or semantic approval of an action. See [command queue](command-queue.md), [batch feedback](batch-feedback.md) and [decision agent](decision-agent.md).

## Knowledge review and persistence sequence

```mermaid
sequenceDiagram
    actor User
    participant Host as RunEngine
    participant Worker as Post-run proposal worker
    participant Files as Private report files
    participant Web as Local knowledge server
    participant Store as KnowledgeStore

    opt Learning enabled and post-run inference authorized
        Host->>Worker: Request proposals using retained evidence
        Worker->>Store: Read approved entries for tested app identities
        Store-->>Worker: Approved catalogue
        Worker->>Files: Save proposed changes, not approved database writes
    end
    Host->>Web: Register finalized run/replay report
    User->>Web: Open report review page
    Web->>Store: Check latest finalized report and saved decisions
    Web-->>User: Editable latest proposals or read-only older report
    User->>Web: Accept reviewed change, decline or reopen
    Web->>Store: Validate latest-report status and review generation
    alt Acceptance is current and valid
        Store->>Store: Check entry revision, atomically apply change and save decision
    else Decline or reopen
        Store->>Store: Save review decision without changing approved entries
    else Stale report or revision conflict
        Store-->>Web: Refuse write without changing approved entry
    end
    Web-->>User: Current decision or conflict with latest-report link when applicable
    opt Standalone editor, independent of testing and Learning
        User->>Web: Save a direct app-knowledge edit
        Web->>Store: Apply explicit user edit
    end
```

Static report files retain proposals and links. Only the local server handles writes; opening static HTML does not approve anything. The installation-local database persists across test folders. Declining/reopening preserves approved entries; acceptance alone applies a proposed change. Current test instructions remain authoritative over stored knowledge.
