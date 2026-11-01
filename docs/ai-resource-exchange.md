# AI command resources and replies

Updated: 1 November 2026. Describes FR-96/AC-66 execution resources; FR-97 defines the input-only layer. This is a source change with offline checks; installation and live acceptance are separate.

## Responsibility

FR-97 supersedes the former reply-reading layer responsibility. [AI Instruction and Context](ai-instruction-context.md) now owns inputs and retained information only, in runtime/ai_instructions/. It queries the confirmed Mobile MCP adapter for fresh masked screen/control information before each instruction request. It does not receive or evaluate replies.

This document describes the separate execution command protocol. runtime/command_reply.py binds explicit commands; Agent owns transport/accounting; AiInteraction coordinates requests and feedback; ActionExecutor executes. Test Planning and Exploration and the evidence store retain information for future instructions. No response approval is delegated to the input layer.

## Resources given to AI

Each request provides the original testing instructions, setup and execution scope, current masked screenshot and UI data, credential aliases, command argument descriptions, and the AI-selected context. The full requirement catalogue and stored history remain available through exact record addresses. The AI can retain its previous context selection, choose another selection, or request records without acting on the app.

CIMT returns actual resource outcomes, including unavailable record addresses and adapter interaction errors. If the selected context exceeds the technical payload allowance, CIMT reports that the entire selected package was deferred. The AI decides what to request next; that notice does not veto a command based on the current evidence. CIMT never chooses a relevant subset.

## Command decoding

The current transport remains the Responses API with text output. This change does not migrate to function calling or add a new service. No strict response schema is requested from the provider.

To execute a command, the reply supplies one readable JSON object containing action and its needed arguments. For example:

```json
{"action":"tap","ref":"@previously-seen-control"}
```

Plan updates, checks, context selections and recovery acknowledgements are optional. Missing fields receive mechanical defaults for the existing dispatcher. Unknown or differently shaped fields remain in the complete original reply even when they cannot be bound to a typed record. A sparse or inconsistent report does not discard an executable command.

A reply containing prose, multiple concatenated objects or no readable command is retained as an AI note. CIMT reports “No single executable command was supplied. No device action was dispatched.” The next request receives this resource feedback. CIMT does not guess a target, select one of several commands or claim that a proposed action ran. There is no three-response correction limit and no response-format exhaustion stop. Normal shared time, spending and cancellation limits still apply to every request.

Supported-command arguments, platform capabilities, coordinate bounds, credential destinations and privacy are mechanical execution constraints. Provider refusals, incomplete provider responses and transport failures keep their existing infrastructure policy. Removing response evaluation does not make an unavailable resource usable or permit an unmasked image or secret to reach AI.

## Planning, findings and recovery

AI task, path and requirement references are stored without semantic approval. Known IDs link records mechanically. An unavailable reference remains unbound and must not update an unrelated catalogue item or become proof of an observed control. Missing local numeric task IDs receive distinct storage IDs. Original AI text remains available for review.

CIMT reports the AI's findings and keeps known failures, crashes and unresolved work visible. It does not judge whether an explanation or quotation is correct. An unfamiliar result cannot manufacture a passed verdict. AI may finish when it chooses; the report still shows any recorded unresolved work and marks completion incomplete. No host-selected reconsideration call is added merely because a finish conflicts with the plan.

Repetition facts recorded after execution are supplied as AI-directed recovery information with fresh masked evidence in the next instruction. They do not veto a chosen command. The AI chooses its next approach. A command does not need a matching structured recovery acknowledgement. Notes and recall requests leave recovery pending; they are not recorded as device actions or completed recovery commands.

## Evidence and report

Each decision retains the full reply under modelResponse after secret redaction. HTML exposes it in “AI replies and resource feedback”, escaped as text. Optional typed planning and check records remain separately readable. AI prose is not proof of execution: only actual dispatcher outcomes add device actions and observed transitions.

Older reports may contain Unaccepted AI responses from the removed correction policy. They are historical evidence and are not rewritten. New execution does not produce that evaluation or its rejection/exhaustion events. Instructions, requirements, screenshots and runtime outcomes continue through the existing privacy and evidence boundaries.

## Verification

The existing Python suites cover minimal commands, optional records, unbound IDs, unavailable context addresses, more than three note replies followed by a command, shared limits, fresh evidence after an actual action and privacy. The existing .NET report tests verify escaped and redacted full replies and resource feedback. CLI and build fixtures remain offline. These checks do not establish live model compliance, exploration quality, latency or cost savings.

```mermaid
sequenceDiagram
    participant Run as Execution
    participant Resources as Command Decoding
    participant AI as Configured Model
    participant Device as Device Adapter
    participant Records as Local Records and HTML
    loop Until AI finishes or an execution limit stops the run
        Run->>AI: Instructions, requirements, masked evidence and AI-selected context
        AI-->>Resources: Complete reply
        Resources-->>Run: Decoded command or note, optional records, original text
        Run->>Records: Redacted reply and available records
        alt No executable command
            Run->>AI: Resource feedback, no device action dispatched
        else Supported command
            Run->>Device: Execute AI-selected command
            Device-->>Run: Actual outcome or interaction error
            Run->>Records: Outcome and masked evidence
        end
    end
```
