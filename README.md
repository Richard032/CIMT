# CIMT — Curtis Intelligent Mobile Test

CIMT is a command-line product in development for autonomous everyday testing of .NET MAUI applications on connected Android and iOS devices.

Developers supply a Git repository, configurable build targets, plain-text testing instructions, and requirements. CIMT will build the application, operate it on the devices, and produce a local HTML report with observations and evidence. Jenkins will invoke the same command through its pipelines.

**Status: CLI validation, default build workers, an initial single-objective run engine, and complete source requirement mapping are implemented. The real application run, final adapter qualification, and release acceptance remain pending.**

## Documentation

- [Requirements](docs/requirements.md): confirmed product requirements, outcome rules, and acceptance criteria.
- [Architecture](docs/architecture.md): approved structure and policies, technology evaluation, and unresolved engineering decisions.
- [Product documentation](docs/product-guide.md): intended user workflow, configuration concepts, reporting, and Mac setup plan.
- [Installation and setup guide](docs/installation.md): repeatable Mac preparation, verification steps, and findings maintained during implementation.

The requirements baseline is version 0.10 and architecture version 0.16, updated 29 October 2026. Product and installation guides include current implementation findings. Requirements, main architecture policies, and reviewed CLI/YAML contracts are confirmed. Final adapter selection, the supported compatibility matrix, full schema constraints, and end-to-end acceptance remain open.

## Initial release

- Intel Mac host; .NET command-line application, shell setup script, one installation and one active run per Mac.
- Single Git branch; private repositories supported through existing Git credentials.
- All supported physical devices connected at startup; at most two tested simultaneously.
- Every configured build target on every compatible device.
- OpenAI-driven testing; strict per-run AI budget and configurable whole-run time limit.
- Local HTML reports with screenshots for every test step and saved actions for adaptive replay.
- Repository clones removed after execution; reports retained.
- Launch installed CIMT from any folder; supply inputs only. CIMT creates generated work and reports under the input folder's CIMT output subfolder.

Two-branch comparison is planned for a later release. Device-control technology remains to be selected after evaluation.

## Review order

Start with the requirements, review the architecture against them, then review the proposed operator experience in the product guide. Open decisions are collected in the architecture document.

## Approved command and configuration design

The planned commands are setup, validate, run, and replay. Configuration uses setup.yaml, default.yaml, and an app.yaml per-run override, with separate ai-model and ai-budget sections.

CIMT will supply default Android/iOS build scripts. User replacements/custom copies are supported. All commands and script integrations require examples and runnable demos using a user-supplied app; no demo MAUI application will be bundled.

See the [product guide](docs/product-guide.md) for approved command invocations, YAML examples, path rules, and script contracts. The [main-branch button/crash example](examples/econ-button-crash/README.md) supplies the public validate/run commands and all application-specific inputs. The [run-engine notes](docs/run-engine.md) distinguish the current implementation from the complete approved design.

## Prerequisite bootstrap

For the validated first-Mac prerequisite profile (Intel, Xcode 26.5):

```bash
bash scripts/setup-prerequisites-macos.sh
source /Users/Shared/CIMT/environment.sh
```

The helper installs isolated runtimes, MAUI Android/iOS workloads, Android tools, and both adapter candidates. It is not the completed YAML-driven cimt setup command. Read the [installation guide](docs/installation.md#8-prerequisite-installation-performed--28-october-2026) for exact versions, checks, limitations, Git authentication, and remaining device/application validation.

[Installed prerequisite profile](docs/installed-prerequisites-macos-intel.yaml) records observed versions; it is not yet an enforced installer manifest.

## Repository locations

The first application to test is [ag-econ-mobile on Subgit](https://subgit.curtis.ch/ECON/ag-econ-mobile.git). Noninteractive read access and initial build validation of main were performed on this Mac. Each run still requires an explicit configured branch.

CIMT's product code and documentation remain in this GitHub repository for now. The product owner plans to move CIMT to Subgit later; that migration has not been performed. Application repository URLs remain configurable.

## Current implementation

Read the [reviewed implementation status](docs/implementation-status.md) for done, remaining, and blocked work after each increment. The installed cimt validate command produces configuration/readiness reports. cimt run now owns cloning, builds, device scheduling, bounded AI exploration, evidence, and cleanup for one objective per target/device. setup and replay remain explicitly unimplemented. No real application pass is claimed from implementation fixtures.

- [Adapter evaluation](docs/adapter-evaluation.md): both candidates exercised on Android and iPhone; Appium passed 11 iPhone checks and Mobile MCP passed 8 guarded iPhone smoke checks. Final application qualification remains open.
- [Default build-script contract](docs/build-script-contract.md): installed scripts and verification results.

Run development checks with bash scripts/check-development.sh. The [development guide](docs/development.md) explains the small services, unit-test boundaries, and simple English comment rules from [AGENTS.md](AGENTS.md). Private configuration, run evidence, and temporary work stay local.

- [Complete requirement mapping](docs/requirement-mapping.md): source catalogue, five statuses, evidence, and every applicable target/device combination.
- [Offline mapping demonstration](examples/requirement-mapping/README.md): runnable synthetic report; no API key or phone needed.

- [Shared run identity](docs/run-identity.md): identical UTC timestamps for work/report names, safe collisions, retained metadata, and cleanup/portability checks.
