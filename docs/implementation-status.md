# Current implementation status

Updated: 10 November 2026. Scope: source baseline `c54ea32` on `feature/external_file`, before this documentation-only revision. Verify the current checkout and installed revision before applying this snapshot elsewhere. [Implementation history](implementation-history.md) preserves the earlier dated working log.

## Implemented scope

- Public `validate`, fresh-clone/build `run`, and retained-build `replay`; merged YAML with source-relative paths, explicit branch override, input snapshots and requirement catalogue.
- Automatic installation/environment discovery, executable adapter preflight and local reports under each input folder.
- Configurable build scripts/properties, preservation of project pre-build authority, per-platform artifact handling and one retained build set with hashes/source identity.
- Physical/virtual device selection as separate kinds, optional exact IDs, startup snapshot and maximum two active workers.
- Reset hooks and declared external-file provisioning/verification before launch, including replay.
- Mobile MCP device adapter, masked screenshots/UI text, local credential replacement, absolute-coordinate/targeted-swipe forwarding and actual argument feedback.
- AI-owned planning, scenario-local context and loop recovery; FIFO commands, failed-tail cancellation, complete ordered batch feedback and ANR warnings.
- Shared conservative model budget/deadline, typed stopping scope, partial/final HTML reporting and retained owned work.

Implementation does not imply every platform, capability or failure path has been accepted live. [Product guide](product-guide.md) explains current use; [release readiness](release-1.0.md) separates remaining product and qualification work.

## Offline checks executed for this review

On 10 November 2026, `bash scripts/check-development.sh` ran on the prepared Apple Silicon Mac. It returned **exit 1**, with these preceding groups passing:

| Group | Result |
| --- | --- |
| Existing .NET xUnit suite | 349 passed, 0 failed/skipped |
| Runtime-policy checks | 22 passed |
| Existing Python unit suite | 512 passed |
| Fake-tool public CLI/lifecycle checks | 22 passed |
| Simulated build-contract checks | 4 passed |
| Example build checks | 4 passed |

The final `tests/check-output-layout.py` fixture failed during discovery because its isolated installation lacks `tools/node-packages/lib/node_modules/@mobilenext/mobile-mcp/lib/mobilecli.js` (`MODULE_NOT_FOUND`). The full bundle is **not green**. This documentation task did not modify that unrelated fixture or bypass readiness checks. Repair and rerun are an open release check; passing other suites does not close it.

These are offline checks using fixtures, not paid AI tests, real application builds or device acceptance. No paid test was started for this documentation review.

## Observed Mac/application evidence

The installation work used a native Apple Silicon toolchain and confirmed Android/iOS discovery. The latest recorded application run on 10 November cloned source `2481daa` from the keyboard-regression branch and built both Android and iOS artifacts. Its final outcome was **incomplete / inconclusive, exit 2**; build success is not a functional pass. Private reports/configuration/fixtures remain local.

Earlier manual iPhone-simulator feedback confirmed visible fields and repeated switching/unchanged OK for the final candidate. That is useful application evidence, but it does not establish automated two-platform acceptance, every simulator, physical-device qualification or Jenkins readiness.

The [installation how-to](installation.md) captures reusable steps; [installation notes](installation-notes.md) preserve the troubleshooting chronology and historical limitations. Neither a dated successful command nor an installed package establishes compatibility with every later version.

## Still open

YAML-driven setup/toolchain manifest, semantic scenario decomposition and saved-action/adaptive scenario replay remain unfinished. Configured input/script paths are checked, but the complete authored folder layout is not strictly enforced. Automatic shared app learning was reverted; reviewed knowledge is supplied through explicit text inputs. Jenkins, a second host, comprehensive platform/reset/login/masking/crash/limits qualification and representative automated app acceptance remain release work. Do not mark the complete approved requirements accepted based on documentation cleanup or offline suites.
