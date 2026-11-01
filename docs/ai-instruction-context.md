# AI Instruction and Context

Updated: 1 November 2026. Implements FR-97 and AC-67. The product owner confirmed that CIMT keeps Mobile MCP; this change does not introduce Appium.

## Responsibility

The layer only prepares AI instructions and keeps information available for future instructions. It supplies the testing objective, requirements, setup, execution scope, current UI information, masked screenshots, credential aliases, command descriptions and the AI's selected history. The AI decides what to test, which control to use, how to interpret a result, and which information to retain or retrieve.

The layer lives in runtime/ai_instructions/. InstructionContext assembles the sources and retained scenario information. ActionPromptBuilder constructs the request. controls.py describes the human-interface controls declared by the device adapter. The layer has no reply decoder, response validator, device-action dispatcher or OpenAI transport.

Complete records remain in the existing scenario evidence and Test Planning and Exploration stores. The input layer uses those stores instead of keeping another copy of the plan. It applies the AI's exact context selection without deciding relevance, reducing history itself or replacing requirements with a summary. A selection that cannot fit returns capacity information for the AI to handle; records are retained.

## Current screen information

Before each AI instruction request, InstructionContext asks the active device adapter for a fresh masked screen observation. Mobile MCP remains the source. ScreenCapture keeps its existing readiness, before/after UI, dimensions, lossless-image and masking checks. No raw screen text or image is saved or sent before that privacy boundary succeeds.

The request contains both the full masked elements and a humanInterface catalogue. The catalogue uses adapter-provided control types and clickable, editable or scrollable metadata. Each entry keeps its ref, label, bounds, input kind and available state flags. Disabled or hidden controls remain information for the AI; this catalogue is not an action whitelist. A generic view without input metadata remains in the full elements rather than being silently declared a button. The AI can identify additional inputs from the evidence.

Refreshing before a new request also covers note-only and recall turns, when the app may have changed by itself. This adds observation work compared with reusing the previous screenshot. It does not remove the separate post-action crash and evidence capture. Live latency has not been measured for this increment.

## Replies and execution

Agent and AiInteraction are execution-side coordinators outside this layer. Agent owns the provider request and shared accounting. runtime/command_reply.py reads the command protocol. ActionExecutor performs the AI-selected supported command. ScenarioRunner retains the reply and actual execution outcome for subsequent instructions and the report. These components do not ask the instruction layer to approve a reply, plan, quote or action target.

The text-command transport remains. Under FR-99, execution decodes explicit JSON objects into a FIFO queue and performs each in received order. It returns actual resource errors and retains unreadable text as a note without guessing commands from prose. The queue belongs outside this layer. An unexecutable command cancels the remaining queue; execution supplies the actual issue on the next normal decision request. Successful batches add no separate acknowledgement call. Queue records are available as the commands context collection, selected only by AI. No semantic response evaluation or migration to function calling is introduced. See [command queue](command-queue.md).

Time, spending, cancellation, credential destinations, masking and platform capability checks remain execution constraints. AI claims about future actions are not records of performed actions. Findings and plan updates remain AI-owned data, independently of dispatch.

## Repetition information

The old pre-action repetition gate is removed. CIMT executes the selected command first. After observing its real outcome, repeated unchanged attempts or navigation without discovery create a recovery notice for the next AI request. The AI may revise its approach, recall history, explain intentional repetition, continue with its chosen command or finish.

No replacement action is selected by CIMT, and no structured recovery acknowledgement is required before a command. Every renewed repetition signal is supplied to AI; there is no fixed recovery-episode stop. Budget, time, cancellation and independent crash/infrastructure policies still apply. An explicit AI recover request can ask for a fresh observation without an app action.

## Packaging and verification

Install the full ai_instructions/, test_planning/ and stopping_policy/ packages with the matching top-level runtime files. command_reply.py replaces ai_exchange/replies.py; ai_interaction.py replaces decision_recovery.py. The installer removes those obsolete source modules. action_prompt.py remains a compatibility import for existing callers; instruction and decoding implementations are separate.

Existing offline tests cover input sources, credential aliases, control metadata, disabled controls, full static evidence, fresh information after a note, AI-owned context, no reply/execution imports in the layer, and execution of a fourth AI-selected tap after repetition feedback. Tests also retain masking, cancellation and shared-limit coverage. No installation, new mobile run or paid OpenAI request is part of this implementation task.

```mermaid
sequenceDiagram
    participant Run as Execution
    participant Inputs as AI Instruction and Context
    participant Device as Mobile MCP and Masking
    participant Store as Retained Context and Evidence
    participant AI as Configured Model
    participant Commands as Command Execution

    loop Until AI finishes or an execution rule stops the run
        Run->>Inputs: Prepare next instructions
        Inputs->>Device: Query current screen and human-interface metadata
        Device-->>Inputs: Verified masked UI and screenshot
        Inputs->>Store: Retain observation and retrieve AI-selected context
        Store-->>Inputs: Requested information and resource feedback
        Inputs-->>Run: Sources, current controls, context and command descriptions
        Run->>AI: Instruction request
        AI-->>Run: Ordered command objects and optional records
        Run->>Commands: Queue objects; take each in FIFO order without input-layer approval
        Commands->>Device: Execute AI choice
        Device-->>Commands: Actual outcome
        Commands-->>Run: Execution result and evidence
        Run->>Store: Save outcome and repetition facts for future instructions
    end
```
