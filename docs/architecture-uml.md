# Current CIMT architecture diagrams

These diagrams describe the source implementation. [Architecture decisions](architecture.md) preserve the design history. The [worker protocol](worker-protocol.md) specifies the host and worker handoff.

## Layers and dependencies

```mermaid
flowchart TD
    CLI["CLI and settings<br/>src/Cimt/Cli and Settings"]
    Run["Run orchestration<br/>src/Cimt/Execution"]
    Build["Application build worker<br/>tools/Cimt.BuildWorker"]
    Worker["Device scheduling and scenario execution<br/>runtime/run_ui.py and scenario.py"]
    Inputs["AI instruction and context<br/>runtime/ai_instructions"]
    Plan["Test planning and exploration<br/>runtime/test_planning"]
    Device["Device adapter and masking<br/>runtime/device_adapter"]
    Stop["Stopping policy<br/>runtime/stopping_policy"]
    Agent["Decision agent<br/>runtime/decision_agent.py"]
    Review["Evidence ledger, completion review and proposals<br/>runtime/result_review"]
    Provider["OpenAI request accounting and transport<br/>runtime/ai_services.py"]
    Knowledge["App knowledge and approval<br/>runtime/knowledge"]
    Editor["Local HTML editor and report review"]
    Journal["Masked evidence and worker journal<br/>runtime/evidence.py"]
    Finish["Run finalization<br/>src/Cimt/Execution/RunFinalization.cs"]
    Report["JSON and HTML rendering<br/>src/Cimt/Reporting"]

    CLI --> Run
    Run --> Build
    Run -->|Worker request JSON| Worker
    Worker --> Inputs
    Inputs --> Plan
    Inputs --> Device
    Worker --> Device
    Worker --> Stop
    Worker --> Agent
    Worker --> Review
    Worker -->|App-scoped lookup and post-run proposals| Knowledge
    Knowledge -->|Default proposal generator| Provider
    Editor -->|User-approved writes and direct edits| Knowledge
    Agent -->|Default OpenAI implementation| Provider
    Review -->|Default OpenAI implementations| Provider
    Worker --> Journal
    Run --> Finish
    Journal -->|Worker results and budget JSON| Finish
    Finish -->|RunReportData| Report
```

Execution owns the device, action queue, scenario state and stopping. Planning interprets supplied records as retained AI plans and exploration history. Instruction preparation pulls in that history and a fresh masked observation. The decision agent returns commands. The reviewer can advise reconsideration once. The proposal generator drafts guidance after device execution. The default AI implementations share request accounting and the run budget. The host also uses the Mobile MCP helper for discovery and cleanup. The [device adapter review](device-adapter.md#replacement-boundaries) identifies both replacement boundaries.

## Class and interface diagram

```mermaid
classDiagram
    class DecisionAgent {
        <<interface>>
        +check_access()
        +decide(DecisionRequest) dict
    }
    class CompletionReviewer {
        <<interface>>
        +review(EvidenceRequest) CompletionReview
    }
    class ProposalGenerator {
        <<interface>>
        +propose(EvidenceRequest) ProposalResult
    }
    class IRunReportWriter {
        <<interface>>
        +Write(RunState, RunReportData)
    }
    class KnowledgeLookup {
        <<interface>>
        +lookup(query, entry_id)
    }
    DecisionRequest --> KnowledgeLookup : optional read-only capability
    DecisionAgent <|.. Agent
    CompletionReviewer <|.. CompletionCritic
    ProposalGenerator <|.. OpenAiProposal
    IRunReportWriter <|.. RunReportWriter
    AiInteraction --> DecisionAgent
    ScenarioRunner --> CompletionReviewer
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

DecisionRequest carries copied context plus shared execution hooks. EvidenceRequest carries redacted evidence, the request observer and a cancellation check for in-run review. ProposalResult and CompletionReview define the expected reply fields. AiServices records requests and accounts for usage. Each default AI implementation supplies the prompt and handles its own reply. The proposal worker restores the persisted run budget. When Learning is enabled, the decision request also exposes app-scoped knowledge lookup through a read-only capability. The knowledge layer owns the local database, report review transactions, and standalone editor. Approval and direct edits never pass through the decision agent.

## Run, replay and finalization sequence

```mermaid
sequenceDiagram
    participant CLI as CLI
    participant Host as RunCoordinator
    participant Build as Build workflow
    participant Worker as Python worker
    participant Files as Worker result and budget files
    participant Final as RunFinalization
    participant Report as RunReportWriter

    CLI->>Host: Start run or replay under host lock
    Host->>Host: Load inputs and check installed runtime
    opt Replay
        Host->>Build: Load and verify retained builds
    end
    Host->>Worker: Preflight request
    Host->>Host: Discover startup devices
    opt Run
        Host->>Build: Clone, build and retain artifacts
    end
    Host->>Worker: Execute eligible builds on startup devices
    Worker->>Files: Publish masked results incrementally
    opt Interim update
        Host->>Final: Calculate provisional outcome from saved results
        Final->>Report: Write snapshot
    end
    Worker-->>Host: Device exit code
    Host->>Host: Clean up owned helper and logs
    opt Proposal can run
        Host->>Worker: Proposal request with run status
        Worker->>Files: Read saved results and restore spending
        Worker-->>Host: Return after saving proposal or unavailable status
    end
    Host->>Final: Determine final outcome and completion
    Final->>Files: Read result and latest budget
    Final->>Report: Write final JSON and HTML with calculated outcome
    Final-->>Host: Return calculated exit code
    Host-->>CLI: Return run exit code
```

On a stopped or failed run, the host proceeds to cleanup and finalization with the evidence available. See [run engine](run-engine.md) for eligibility and exit rules.

## Decision sequence

```mermaid
sequenceDiagram
    participant Run as ScenarioRunner
    participant Context as AiInteraction and InstructionContext
    participant Device as Mobile adapter
    participant Agent as DecisionAgent
    participant AI as OpenAI request service
    participant Critic as CompletionReviewer
    participant Queue as CommandQueue

    Run->>Context: Request next decision when queue is empty
    Context->>Device: Capture fresh masked UI and image
    Context->>Agent: Decide from copied context
    opt Default agent
        Agent->>Agent: Prepare prompt and check selected history capacity
        Agent->>AI: Journal, count input and reserve estimate before inference
        AI-->>Agent: Provider reply and usage settlement
    end
    Agent-->>Run: Normalized commands
    Run->>Queue: Append batch in order
    opt First command proposes done and review has not run
        Run->>Critic: Review redacted evidence with request observer
        Critic-->>Run: Agree or advise reconsideration
    end
    opt Device command
        Run->>Device: Dispatch selected command
        Device-->>Run: Outcome and masked evidence
        Run->>Run: Save result for next decision
    end
```

See [command queue](command-queue.md) for deferred finish, failure and recovery handling. See [decision agent](decision-agent.md) for replacement limits.
