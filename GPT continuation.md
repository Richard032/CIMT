# GPT continuation

Updated: 10 November 2026. This is an agent handover, not an installation log or a new user request. Current user instructions and the actual checkout take priority.

## Start here

1. Read [AGENTS.md](AGENTS.md), the portable coding instructions below and the relevant [documentation](docs/README.md).
2. Inspect branch, working tree, installed revision and remote state. Preserve unrelated/private work. Never assume a historical PR is still open or a source change is installed.
3. Distinguish approved [requirements](docs/requirements.md), architecture, implementation and observed evidence. Report differences honestly.
4. Use the [installation how-to](docs/installation.md) and [dependency selection](docs/dependencies.md) for setup. Select the newest compatible tools; concrete versions are examples from the Mac installation.

## Current handover

The documentation review targets existing `feature/external_file`; no merge, release tag or new paid/device test is authorized by it. The source baseline before the documentation revision is `c54ea32`. The earlier automatic shared app-learning feature was reverted. App knowledge is maintained through explicit reviewed setup text, not automatic learning or publishing.

[Implementation status](docs/implementation-status.md) records current scope and executed evidence. On 10 November, 349 .NET unit tests, 512 Python unit tests, 22 runtime-policy checks, 22 CLI/lifecycle checks, four build-contract checks and four example checks passed. The final output-layout fixture failed because its isolated Mobile MCP module was missing. Do not call the full bundle green or change an unrelated test merely to hide the failure.

The Apple Silicon installation has Android/iOS discovery and application build evidence. The latest recorded two-platform application run built both artifacts but ended incomplete/inconclusive, exit 2. Private reports, fixtures and settings remain local. Manual app feedback and successful builds do not establish automated two-platform acceptance. [1.0 readiness](docs/release-1.0.md) lists open gates, including unfinished approved features, Jenkins and another host. Verify current evidence before making a new claim.

## Product and operating boundaries

CIMT means Curtis Intelligent Mobile Test. A terminal command (also intended for Jenkins) tests configured .NET MAUI targets with AI through Mobile MCP. Mobile MCP is a device-tool adapter, not a second agent. Physical and virtual devices are separate run kinds, selected at startup, with at most two active device workers.

AI chooses tests, actions, targets, history relevance and recovery. CIMT provides original inputs, masked current evidence, exact selected history, mechanical execution and feedback. Do not add application-specific semantic gates or host-selected replacement actions. Command syntax/capabilities, geometry, privacy, permission authorization, budget and stopping rules remain necessary. Do not patch third-party adapter source.

Execute commands FIFO and cancel pending tail commands after an unexecutable command. Supply actual complete batch results to the next normal decision request; a tool call succeeding does not prove the desired UI state or requirement passed. AI owns desired app values. Shared context is scenario-local; reviewed navigation knowledge belongs in test inputs, separate from issue descriptions.

Instructions take priority over conflicting requirements; retain the conflict and interpretation. Keep observed failures and unresolved work visible. The configured model has no fallback and shares a conservative budget/deadline across workers. Device launch failure is local; three matching crashes stop the objective; shared infrastructure/privacy failures follow the [stopping policy](docs/execution-stopping.md).

`run` clones the configured remote branch and builds. `replay` uses one matching retained build set with current inputs, without Git/restore/build; saved-action replay is unfinished. A manually copied checkout is not a retained build. A new commit or missing platform needs `run`. Project pre-build commands, including CuRMiTagger, remain project-owned. Do not skip/inject application build steps without explicit need and authorization.

The launcher automatically discovers the installation and loads its `environment.sh`. Keep host, worker, runtime and scripts consistent. Do not modify an installation or test inputs while a run uses them. CIMT's source SDK selection and the tested application's SDK selection may differ; inspect each checkout rather than applying historical versions universally.

## Working and reporting rules

- Keep private YAML, keys, login credentials, device IDs, packages, fixtures, unmasked data and generated outputs out of Git/chat. Use credential aliases and existing masking/redaction boundaries.
- Do not start a run/replay or paid request for a documentation/review task. When authorized, use the public workflow and respect cancellation and configured checkpoints.
- Report reviews must identify the exact run, commit, devices, final/interim state, findings and stopping reasons. Separate confirmed observations from hypotheses. Inspect all configured platforms, not only the first visible result.
- Follow the requested branch/scope. Commit/push only authorized changes and preserve unrelated local overrides. Do not merge a PR unless asked. Current CIMT Git identity is Richard032; application-only author preferences are separate.
- Run relevant existing checks and report blockers exactly. Do not claim tests/builds passed unless executed. Keep the user informed with concise meaningful updates.

## References

[Documentation index](docs/README.md), [requirements](docs/requirements.md), [architecture](docs/architecture.md), [product guide](docs/product-guide.md), [test inputs](docs/test-inputs.md), [development](docs/development.md), [implementation status](docs/implementation-status.md) and [release readiness](docs/release-1.0.md) are the current entry points. Dated working records and reviews are linked from the index and must not be mistaken for current instructions.

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