# 1.0 release readiness

Updated: 10 November 2026. Documentation baseline: 1.0. This is a release checklist, not a declaration that all approved requirements are accepted. Merging documentation alone does not qualify the product, publish a release or close outstanding behavior.

## What this documentation revision prepares

The documentation now separates a practical Mac installation how-to, current command/input guides, dependency selection, implementation status, design contracts and dated working records. Installation examples come from our Apple Silicon setup. Select the newest compatible tools using the checkout/application metadata; concrete commands show the versions actually used without making them permanent requirements.

See the [documentation index](README.md), [installation](installation.md), [product guide](product-guide.md), [test inputs](test-inputs.md) and [implementation status](implementation-status.md).

## Open gates

| Gate | Current evidence / required next step |
| --- | --- |
| Offline regression bundle | 349 .NET and 512 Python unit tests, 22 runtime-policy, 22 CLI/lifecycle, 4 build-contract and 4 example checks passed. The final output-layout fixture fails because its isolated Mobile MCP module is absent. Repair the fixture and rerun the bundle before calling it green. |
| Android and iOS app acceptance | Both artifacts built on the Apple Silicon Mac. The latest recorded automated run ended incomplete/inconclusive, exit 2. Complete per-platform keyboard regression and exploratory scenarios with retained evidence. |
| Device/privacy/failure qualification | Basic control/masking evidence and offline cases exist. Qualify representative reset/login, external files, masking transitions, crashes, disconnects, concurrency and shared limits on the supported device matrix. |
| Installation repeatability | Verify the how-to on a second host and record the tested architecture/toolchain combination. Intel pilot records are historical, not a generic cross-architecture installer. |
| Jenkins | Exercise installation-account access, unattended configuration, build/signing, limits and report retention under the actual service account. |
| Test-folder enforcement | Configured paths/fixture containment are checked; the full authored README/three-wrapper layout is guidance, not a strict folder-schema validator. Resolve the earlier requirement for stricter enforcement explicitly. |
| Approved scope | YAML-driven setup/toolchain manifest, semantic scenario decomposition and saved-action/adaptive scenario replay remain unfinished. Implement/accept them, or obtain an explicit product-owner scope decision before claiming complete approved-scope 1.0. |

Retained-build replay is implemented and must not be confused with unfinished saved-action replay. Scenario-local AI context is implemented; automatic cross-run knowledge learning/publication is not.

## Before release approval

Review the requirement IDs and acceptance criteria in [requirements](requirements.md), including later decisions, against current implementation and actual evidence. Record each unresolved item rather than marking an older design proposal as implemented. Confirm the installed host, build worker, Python packages, launcher and scripts come from the intended source revision. Check that no private YAML, key, login, device ID, package archive, fixture or report is staged.

Merge, release tagging and additional paid/device tests require their own user instruction. This documentation work only prepares and pushes the existing working branch; it does not authorize those actions.
