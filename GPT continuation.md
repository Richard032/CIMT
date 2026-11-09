# GPT continuation

This document is a handover for an AI agent continuing work on CIMT. It is a snapshot from 9 November 2026. Check the current repository, branch, requirements and user instructions before acting. The user's current instructions take priority over this snapshot.

## Start here

1. Read [AGENTS.md](AGENTS.md), this document and the documentation relevant to the requested work.
2. Inspect the current branch and changes before editing. Do not assume a pull request has been merged or that a particular version is installed.
3. Explain meaningful progress to the user. After each requested step, state what is done and what remains. Identify any differences between requirements, design and implementation so the user can decide how to resolve them.
4. Use [installation.md](docs/installation.md) for computer setup. Keep setup instructions there, not in this handover.

## How to continue a request

- Read the relevant requirements, architecture and implementation first. Treat a requirement, a design and existing behavior as separate facts. If they differ, tell the user what differs and discuss the correction; do not silently redefine the product.
- Work on the branch and scope requested by the user. Check the status of related pull requests and existing changes before modifying or publishing anything. Preserve unrelated work. Do not merge a pull request unless the user asks.
- Make the requested change, update affected requirements and design, review the result and run relevant existing checks. Report what passed, what could not be checked and why. Do not claim a run or test succeeded without evidence.
- Keep the user informed in simple English. After a step, explain what was completed, the result and the next outstanding step. If the user asks for an explanation or tells you to stop, respect that instruction.
- For a report review, identify the exact run and use recorded evidence. Separate confirmed observations from possible causes. Check all configured platforms and devices, cancellation and stopping reasons, and whether the report is complete. Never invent a crash, action or result.
- Do not expose API keys, login credentials or private configuration in chat, logs, commits or reports. Do not ask the user to paste a secret into chat. Follow the project's redaction and screenshot-masking rules.
- Do not start a device test, replay or paid AI request merely to investigate a documentation task. When requested to run, use the configured user-facing workflow, report progress and respect the user's stop or cancellation request.

## Product and decisions

CIMT means Curtis Intelligent Mobile Test. It is intended to test .NET MAUI applications independently of the application, using plain-text testing instructions and requirements. A developer starts it from a terminal; Jenkins can run it on a Mac. Configuration defines the application repository, branch, build targets, devices, model, budget and other run settings. Both iOS and Android, physical devices and emulators are in scope. Up to two devices run simultaneously. Every configured target is tested on every selected device. The initial release focuses on one branch; comparing two branches is future work.

Instructions take priority when they conflict with requirements; report the conflict and interpretation. Report ambiguous instructions and the interpretation while continuing where possible. The user wants clear, useful HTML reports with screenshots, chronological activity, failures and stopping reasons. CIMT creates output under the input folder, including a separate report folder for every run and replay. Keep private credentials, personal configuration, unmasked screenshots and private test data out of Git.

The planning and exploration layer supplies instructions, requirements, screen controls and retained context to AI. It gathers human-interface elements from the current screen through Mobile MCP. It is an information and instruction layer, not a judge of whether the AI's testing decision is correct. Every detected unproductive loop triggers AI-directed recovery. The host may execute mechanics and enforce existing stopping, privacy and budget limits.

The AI is the testing decision maker. CIMT provides the instructions, requirements, screen observations, available controls, history and device operations. The AI chooses what to explore, how to recover from loops, and what historical information to retain. Do not add host-side rules that decide the meaning or relevance of observations or reject AI decisions merely for semantic reasons. Mechanical execution, privacy, budget and stopping rules remain necessary. Do not modify Mobile MCP source code; it is the selected device adapter.

Execute commands in their received order. If a command cannot be executed, cancel the remaining queued commands and report the failure and cancellations. A successful batch does not itself complete the objective. Send the complete ordered result of each command batch in the next normal AI decision request. Record the initial state once, then each command and its resulting observation. Include unchanged steps, unavailable observations, independent changes, warnings, errors and commands cancelled after a failure. Preserve intermediate transitions even when the final screen matches the starting screen. Reuse evidence references rather than duplicating unchanged evidence. AI decides what the results mean. Android ANR events are warnings, not automatic crashes or stopping reasons. Permission prompts are not errors and should only be accepted when testing instructions authorize that action.

CIMT uses the configured OpenAI model and enforces a strict run budget. Do not silently substitute another model. Account for actual usage and report budget or time limits clearly. A device failure should be isolated so other devices can continue when the applicable stopping rules allow it. If an app repeatedly crashes at the same point, stop the affected scenario after three attempts, subject to the current documented rules.

Replay uses the retained application build and creates a new report; do not silently rebuild. The working clone is retained after a run and is cleared before a new clone. A replay is not necessarily a saved-action playback: check the documented implementation and its current limitations. Runs may reset app data and incur API costs. Run or replay when the user requests it, and follow the configured checkpoints.

Each named architectural layer has a separate source folder and clear responsibilities. Favor the existing architecture and simple focused code. Never add application-specific build modifications or injected commands without an explicit need and authorization. User-provided build scripts are replaceable; report any changes to the application project separately.

## Current handover state

At the time of writing, [PR #6](https://github.com/Richard032/CIMT/pull/6) is open on `issue/TestPlanningAndExploration` against `main`. Verify its current status before continuing. The installed implementation was previously recorded at commit `f8ad72dc19b3bfde90d9f132fe9c8d094fe2cb3d`; later branch commits include documentation. Installation on another computer may differ.

The latest available historical replay report was `report_2026-11-01_13-41-13-086`. The run reached its whole-run time limit and ended incomplete with exit 3; the user's later cancellation requests arrived after it had ended. The iOS simulator experienced startup or helper relaunch problems, while Android continued independently and performed actions. The report recorded two crash or termination findings; these alone do not establish confirmed application defects. The report and its private evidence are local and may not exist on another computer.

That replay exercised a failed batch: remaining commands were cancelled and feedback was supplied to the next AI request. The final batch was still pending delivery when the run timed out. No ANR was recorded, so this run does not validate live ANR reporting. Historical offline checks reported 426 Python unit tests, 315 xUnit tests, 22 runtime-policy checks and 22 fake-tool CLI/lifecycle checks; these were not rerun for this handover. Verify current behavior before claiming a fix or a passing run.

The user has raised prompt size, cost and speed as open questions. Investigate with measurements and current documentation when asked. Preserve complete new batch feedback and user instructions, and leave history relevance decisions to AI. Do not assume caching or training will solve the issue, or change budget enforcement without authorization.

## Project references

Some design documents below are part of the still-open PR #6 and may not exist on `main` until that PR is merged. Their links point to the PR branch for this snapshot. Verify the PR state and use the current version when continuing work.

- [README](README.md): overview and entry points.
- [Requirements](docs/requirements.md) and [requirement mapping](docs/requirement-mapping.md): product requirements and coverage.
- [Architecture](docs/architecture.md), [device adapter](https://github.com/Richard032/CIMT/blob/issue/TestPlanningAndExploration/docs/device-adapter.md), and [execution stopping](https://github.com/Richard032/CIMT/blob/issue/TestPlanningAndExploration/docs/execution-stopping.md): responsibilities and constraints.
- [Product guide](docs/product-guide.md), [installation](docs/installation.md), and [development](docs/development.md): usage, setup and development.
- [Implementation status](docs/implementation-status.md): history and known gaps; verify older entries against current code.
- [Batch feedback](https://github.com/Richard032/CIMT/blob/issue/TestPlanningAndExploration/docs/batch-feedback.md), [command queue](https://github.com/Richard032/CIMT/blob/issue/TestPlanningAndExploration/docs/command-queue.md), [AI instruction context](https://github.com/Richard032/CIMT/blob/issue/TestPlanningAndExploration/docs/ai-instruction-context.md), and [AI context and recovery](https://github.com/Richard032/CIMT/blob/issue/TestPlanningAndExploration/docs/ai-context-and-recovery.md): AI interaction and execution details.
- [Work retention and replay](docs/work-retention-and-replay.md), [redaction](docs/redaction.md), and [screenshot masking](docs/screenshot-masking.md): persistence and privacy.

## User coding instructions

The following are the user's portable coding instructions, copied from their agent configuration. Apply them alongside the repository's AGENTS.md and any newer instructions from the user.

# Coding Instructions

## 1. Core Principles

Prioritize **simplicity, readability, maintainability, and testability** over clever or advanced solutions.

- Implement the simplest solution that fully meets the requirements.
- Follow KISS, DRY, and separation of concerns.
- Prefer small, focused classes and methods with clear responsibilities.
- Each class should have one main responsibility. Each method should perform one clear task.
- Avoid unnecessary abstractions, interfaces, inheritance, generic frameworks, and architectural layers.
- Use simple, established design patterns only when they provide clear value.
- **Never use the Proxy design pattern.**
- Do not overengineer or add functionality that was not requested.
- Follow the existing project's architecture, naming conventions, and coding style.
- Prefer minimal, focused changes over large rewrites.
- Do not change unrelated code or existing behavior unless required.

**Important:** Do not split code into smaller pieces simply to reduce line counts. Extract classes or methods only when doing so improves readability, responsibility separation, reuse, or testability.

## 2. Code Structure and Readability

- Use descriptive, self-explanatory names for classes, methods, variables, and parameters.
- Keep control flow straightforward and easy to follow.
- Prefer early returns over deeply nested conditions.
- Avoid unnecessary indirection and complex dependency chains.
- Keep business logic separate from UI, database, file system, and external service interactions where practical.
- Prefer dependency injection when it genuinely simplifies dependencies and testing.
- Do not introduce interfaces for every class. Create an interface only when it serves a real purpose.

### Comments

- Write comments in **simple, clear English**, understandable to non-native English speakers.
- Explain why something is done when the reason is not obvious.
- Explain non-obvious business rules, assumptions, and important constraints.
- Avoid comments that merely repeat what the code already says.
- Keep comments short and accurate.
- Update or remove outdated comments when changing code.

## 3. Unit Testing

**Use the existing unit-test project and its current testing framework.**

Never create a new test project, custom test harness, or alternative testing infrastructure unless explicitly requested.

### Test Design

- Write small, independent, readable unit tests.
- Each test should verify one meaningful behavior.
- Keep test setup minimal and easy to understand.
- Use clear test names describing the expected behavior.
- Test observable behavior rather than internal implementation details.
- Cover important success cases, edge cases, and error handling relevant to the change.
- Use the project's existing testing and mocking conventions.
- Avoid complex fixtures, large mock dependency graphs, reflection, and advanced test infrastructure.
- Never copy or link production source files into test projects merely to make them testable.
- Do not introduce production-only abstractions solely to support a test unless they also improve the design.

### When Tests Become Complicated

**Complex unit tests are a warning sign.**

Follow this order:

1. First, check whether the production code has too many responsibilities or tightly coupled dependencies.
2. If necessary, refactor the affected production code into smaller, focused, independently testable classes or methods.
3. Preserve existing behavior during refactoring.
4. Write simple tests against the improved design.
5. If a test is still complicated, split the scenario into several smaller, independent test cases.
6. If complexity remains unavoidable, explain the reason instead of introducing an advanced testing workaround.

Prefer several simple tests over one large, complicated test.

### Test Execution

- Add or update relevant unit tests for changed behavior.
- Run existing relevant tests whenever possible.
- Do not modify unrelated tests simply to make a failing test suite pass.
- If existing build errors prevent tests from running, report the exact blockers.
- **Never create another test project or workaround test harness to bypass build failures.**

## 4. Asynchronous Programming

- Use `async/await` for asynchronous operations.
- In JavaScript and TypeScript, never use `.then()` or `.catch()` promise chaining. Use `async/await` with `try/catch` instead.
- Keep synchronous operations synchronous. Do not introduce asynchronous methods unnecessarily.
- Do not block asynchronous operations with synchronous waiting.
- Follow the project's existing error-handling and cancellation conventions.

## 5. Project-Specific Tools and Conventions

Apply these rules when the relevant technology is used:

### Package Management
- Use **pnpm**.
- Never use npm or yarn for installing packages or running package scripts.
- Respect the existing lockfile and dependency versions.
- Do not add dependencies unless necessary.

### Database Migrations
- Use `make migrate-local` for local database migrations.
- Do not replace the project's custom migration process with another tool or command.
- If the required command is unavailable, report the issue instead of inventing a workaround.

### Styling
- Use **Tailwind CSS utility classes**.
- Do not write custom CSS.
- Reuse existing components, utilities, and styling conventions.
- Avoid adding new styling dependencies.

Do not apply JavaScript, Tailwind, or database-specific rules to projects that do not use those technologies.

## 6. Git Submodule Rules

When updating Git submodules:

- Preserve each submodule's currently configured or explicitly established target branch.
- Update only to the latest commit available on that same branch.
- Never switch a submodule to another branch, including the remote default branch, unless explicitly requested.
- Do not assume that `main` or `master` is the correct target branch.
- If the target branch cannot be determined reliably, do not guess or update that submodule. Report the ambiguity.
- Avoid changing unrelated submodules.

## 7. Implementation Workflow

For every coding task:

1. **Understand:** Inspect the relevant existing code, architecture, conventions, and tests before making changes.
2. **Plan:** Identify the smallest change that meets the requirements.
3. **Implement:** Write straightforward, readable code with clear responsibilities.
4. **Review:** Remove unnecessary complexity, duplication, and abstractions.
5. **Test:** Add or update simple tests using the existing test project.
6. **Validate:** Run relevant tests and build checks where possible.
7. **Report:** Briefly summarize the changes, test results, and any unresolved issues.

Do not claim that code builds or tests pass unless they were actually executed successfully.

## 8. Priority Rules

When choosing between multiple solutions:

1. Correctness and preservation of required behavior.
2. Simplicity and readability.
3. Maintainability and clear responsibilities.
4. Testability.
5. Consistency with the existing codebase.
6. Performance optimization only when necessary or requested.

**Final rule:** Choose the simplest correct implementation that another developer can easily understand, maintain, and test. Avoid clever solutions when straightforward code is sufficient.