# CIMT — Curtis Intelligent Mobile Test

CIMT builds a configured .NET MAUI application and uses AI to test it on Android and iOS through Mobile MCP. It produces local HTML reports with observations, screenshots, requirement coverage and stopping reasons. The same command-line interface is intended for developer Macs and Jenkins.

Current commands are `validate`, `run` and retained-build `replay`. Physical and virtual devices are supported as separate run kinds; at most two device workers run simultaneously. AI chooses tests, actions and recovery. CIMT owns execution, privacy, shared limits and reporting. Mobile MCP supplies device tools and is not a second testing agent.

## Start here

1. [Install on a Mac](docs/installation.md): a step-by-step how-to, including commands from our Apple Silicon setup and rules for selecting newer compatible tools.
2. [Configure and run](docs/product-guide.md): public commands, YAML, output and troubleshooting.
3. [Write test inputs](docs/test-inputs.md): separate app knowledge, scenarios and acceptance requirements; provide fixtures through settings.
4. [Check 1.0 readiness](docs/release-1.0.md): implemented scope, known gaps and the evidence required before release approval.

The [documentation index](docs/README.md) separates operator guides, design contracts and historical working notes. Exact observed tool versions are examples, not permanent requirements; see [dependency selection](docs/dependencies.md).

## Commands

After preparing a private configuration and application inputs:

```bash
cimt validate --config ./default.private.yaml --run-config ./application.yaml
```

Validation checks readiness without a paid AI request or application reset/build/test. A separately authorized fresh test uses:

```bash
cimt run --config ./default.private.yaml --run-config ./application.yaml
```

A later test against the retained binaries uses current text inputs:

```bash
cimt replay --config ./default.private.yaml --run-config ./application.yaml
```

`run` clones and builds; `replay` does neither. A changed source commit requires `run` to test the changed application. Replay is not saved-action playback. YAML-driven `setup`, saved-action/adaptive replay via `--scenario`, and a rebuild-existing-clone command are not implemented.

Each invocation writes its own `<input-folder>/CIMT output/reports/report_<UTC-time>/index.html`. Open the exact path printed by that invocation. A live report is explicitly incomplete until finalization. Build success does not establish functional acceptance.

## Status and development

The [current implementation status](docs/implementation-status.md) is the release-facing summary. Dated [installation notes](docs/installation-notes.md), [implementation history](docs/implementation-history.md) and [reviews](docs/README.md#historical-working-records) retain earlier observations without turning old failures or proposed commands into current instructions.

The latest recorded Apple Silicon application run cloned its configured issue branch and built both Android and iOS. Its functional result remained inconclusive/incomplete. Offline checks and individual manual app checks do not establish full CIMT release acceptance. Jenkins, second-host and remaining physical-device gates must be qualified explicitly.

Use [AGENTS.md](AGENTS.md), [the continuation handover](GPT%20continuation.md) and [the development guide](docs/development.md) for source work. Run `bash scripts/check-development.sh` with the selected CIMT environment for existing offline checks. Private keys, credentials, fixtures, local feeds, test folders and generated reports stay out of Git.

CIMT remains in this GitHub repository. Application repository URLs and branches are configurable. No application-specific code, credential or hardware is required by the generic orchestration contract.
