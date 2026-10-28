# CIMT — Curtis Intelligent Mobile Test

CIMT is a planned command-line product for autonomous everyday testing of .NET MAUI applications on connected Android and iOS devices.

Developers supply a Git repository, configurable build targets, plain-text testing instructions, and requirements. CIMT will build the application, operate it on the devices, and produce a local HTML report with observations and evidence. Jenkins will invoke the same command through its pipelines.

**Status: approved design with prerequisite bootstrap scripts. The CIMT CLI and autonomous testing engine are not implemented yet.**

## Documentation

- [Requirements](docs/requirements.md): confirmed product requirements, outcome rules, and acceptance criteria.
- [Architecture](docs/architecture.md): approved structure and policies, technology evaluation, and unresolved engineering decisions.
- [Product documentation](docs/product-guide.md): intended user workflow, configuration concepts, reporting, and Mac setup plan.
- [Installation and setup guide](docs/installation.md): repeatable Mac preparation, verification steps, and findings maintained during implementation.

All three documents are version 0.3, dated 27 October 2026, based on the product-owner interview and reviews. Requirements, main architecture policies, and reviewed CLI/YAML contracts are confirmed. Adapter selection, supported toolchain versions, full schema constraints, and implementation proofs remain open.

## Initial release

- Intel Mac host; .NET command-line application, shell setup script, one installation and one active run per Mac.
- Single Git branch; private repositories supported through existing Git credentials.
- All supported physical devices connected at startup; at most two tested simultaneously.
- Every configured build target on every compatible device.
- OpenAI-driven testing; strict per-run AI budget and configurable whole-run time limit.
- Local HTML reports with screenshots for every test step and saved actions for adaptive replay.
- Repository clones removed after execution; reports retained.

Two-branch comparison is planned for a later release. Device-control technology remains to be selected after evaluation.

## Review order

Start with the requirements, review the architecture against them, then review the proposed operator experience in the product guide. Open decisions are collected in the architecture document.

## Approved command and configuration design

The planned commands are setup, validate, run, and replay. Configuration uses setup.yaml, default.yaml, and an app.yaml per-run override, with separate ai-model and ai-budget sections.

CIMT will supply default Android/iOS build scripts. User replacements/custom copies are supported. All commands and script integrations require examples and runnable demos using a user-supplied app; no demo MAUI application will be bundled.

See the [product guide](docs/product-guide.md) for approved command invocations, YAML examples, path rules, and script contracts. These describe the approved design. The CIMT CLI and application build scripts remain to be implemented; prerequisite helpers are available below.

## Prerequisite bootstrap

For the validated first-Mac prerequisite profile (Intel, Xcode 26.5):

```bash
bash scripts/setup-prerequisites-macos.sh
source /Users/Shared/CIMT/environment.sh
```

The helper installs isolated runtimes, MAUI Android/iOS workloads, Android tools, and both adapter candidates. It is not the completed YAML-driven cimt setup command. Read the [installation guide](docs/installation.md#8-prerequisite-installation-performed--28-october-2026) for exact versions, checks, limitations, Git authentication, and remaining device/application validation.

[Installed prerequisite profile](docs/installed-prerequisites-macos-intel.yaml) records observed versions; it is not yet an enforced installer manifest.

## Repository locations

The first application to test is [ag-econ-mobile on Subgit](https://subgit.curtis.ch/ECON/ag-econ-mobile.git). Noninteractive read access from the current Mac was verified; the test branch remains to be explicitly selected.

CIMT's product code and documentation remain in this GitHub repository for now. The product owner plans to move CIMT to Subgit later; that migration has not been performed. Application repository URLs remain configurable.
