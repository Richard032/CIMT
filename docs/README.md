# Documentation index

Updated: 10 November 2026. Start with the guide matching your task. Current user instructions take priority over document snapshots. Examples and historical commands are explanatory material, not new requests to execute them.

## Install and operate

| Document | Purpose |
| --- | --- |
| [Installation](installation.md) | Mac how-to with selection rules and concrete commands from the Apple Silicon setup. |
| [Dependencies](dependencies.md) | Version authority, compatibility and updating installed libraries/tools. |
| [Product guide](product-guide.md) | Implemented CLI/YAML, devices, builds, fixtures, reports and troubleshooting. |
| [Test inputs](test-inputs.md) | Real-life folder layout; separate navigation knowledge, regression scenarios and acceptance criteria. |
| [Build-script contract](build-script-contract.md) | Default/replacement script environment and JSON handoff. |
| [Virtual devices](virtual-devices.md) | Simulator/emulator prerequisites, build profiles and capture boundaries. |
| [Work retention and replay](work-retention-and-replay.md) | Clone lifecycle, retained build integrity and current-input replay. |

## Product, development and release

- [Requirements](requirements.md): approved product and numbered acceptance criteria; later decisions can supersede earlier wording.
- [Architecture](architecture.md): responsibilities and evolution; distinguish approved design from implemented increments.
- [Development](development.md): source boundaries, conventions and existing verification commands.
- [Current implementation status](implementation-status.md): dated evidence, limitations and executed check results.
- [1.0 readiness](release-1.0.md): open acceptance/release gates.
- [Agent handover](../GPT%20continuation.md) and [repository rules](../AGENTS.md): working instructions and continuation context.

## Detailed contracts

- [AI instruction context](ai-instruction-context.md), [AI context and recovery](ai-context-and-recovery.md), [AI command resources](ai-resource-exchange.md).
- [Command queue](command-queue.md), [batch feedback](batch-feedback.md), [device adapter](device-adapter.md), [execution stopping](execution-stopping.md), [run engine](run-engine.md).
- [Requirement mapping](requirement-mapping.md), [diagnostic reporting](diagnostic-reporting.md), [run identity](run-identity.md).
- [Redaction](redaction.md), [screenshot masking](screenshot-masking.md), [performance](performance.md).

## Examples

- [Input-folder/output demonstration](../examples/input-folder/README.md).
- [ECON button/crash example](../examples/econ-button-crash/README.md): concrete application settings and replaceable build wrappers; private values are not bundled.
- [Planning example](../examples/test-planning/README.md).
- [Offline requirement-mapping example](../examples/requirement-mapping/README.md).

Examples need adaptation to the actual application and installed profile. An offline fixture or historical smoke check is not a real app test pass.

## Historical working records

[Installation notes](installation-notes.md), [implementation history](implementation-history.md), [product-guide history](product-guide-history.md) and [run-engine history](run-engine-history.md) preserve the previous mixed documents without losing troubleshooting evidence. Their dated status, fixed versions and commands are historical. Use the current guides above for instructions.

[Adapter evaluation](adapter-evaluation.md) preserves the earlier comparison; Mobile MCP is the selected current adapter. The dated files under [reviews](reviews/README.md) retain findings/proposals as recorded, not a current approval or an instruction to repeat probes. Their historical links can point to historical notes deliberately.
