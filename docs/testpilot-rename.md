# TestPilot rename and migration

Approved: 26 November 2026. The former CIMT product is now **TestPilot**. This is a naming change, not a change to testing decisions, configuration precedence, limits or reporting policy.

## Names and commands

| Area | Previous name | New name |
| --- | --- | --- |
| Product | CIMT | TestPilot |
| Terminal command | `cimt` | `testpilot` |
| Debug launcher | `scripts/cimt-debug` | `scripts/testpilot-debug` |
| Runtime installer | `scripts/install-cimt-runtime.sh` | `scripts/install-testpilot-runtime.sh` |
| Solution/workspace | `CIMT.slnx`, `CIMT.code-workspace` | `TestPilot.slnx`, `TestPilot.code-workspace` |
| Source namespace/project | `Cimt` | `TestPilot` |
| Environment prefix | `CIMT_*` | `TESTPILOT_*` |
| Standard installation root | `/Users/Shared/CIMT` | `/Users/Shared/TestPilot` |
| Generated output | `CIMT output` | `TestPilot output` |
| Host/runtime/build worker | `cimt`, `cimt-runtime`, `cimt-build` | `testpilot`, `testpilot-runtime`, `testpilot-build` |

```bash
testpilot validate --config ./default.private.yaml --run-config ./application.yaml
testpilot run --config ./default.private.yaml --run-config ./application.yaml
testpilot replay --config ./default.private.yaml --run-config ./application.yaml
testpilot knowledge
```

## Existing installations and test folders

1. Finish or cancel active tests before updating. Do not run old and new installations concurrently on one Mac. Their renamed lock and ownership files do not coordinate with each other.
2. Follow the [installation guide](installation.md) to publish/install the matching TestPilot host, runtime, build worker and launchers together. Update shell PATH and `environment.sh` to expose `testpilot` and `TESTPILOT_INSTALL_ROOT`. The old command and old environment variable names are not aliases.
3. Keep existing private YAML and text inputs. Update explicit installation/output paths and custom build/reset scripts where present. The new build/reset environment uses `TESTPILOT_TARGET`, `TESTPILOT_DEVICE`, `TESTPILOT_APP_ID`, `TESTPILOT_REPOSITORY_ROOT`, `TESTPILOT_BUILD_REQUEST` and `TESTPILOT_BUILD_RESULT`. YAML field names and test instructions do not otherwise change.
4. Existing output folders and reports remain as they were. A TestPilot invocation creates `TestPilot output` and does not move old reports or retained-build metadata. Old replay state is not automatically migrated; use a new `testpilot run` to establish a retained build set.
5. Approved knowledge is installation-local. For a different installation directory, preserve the complete `data/knowledge` directory while its local viewer is stopped. Do not copy a live SQLite database or assume old report registrations and absolute paths work on a different computer. No automatic data migration is performed by the rename.

The GitHub repository has also been renamed to [Richard032/TestPilot](https://github.com/Richard032/TestPilot). Update existing clone remotes with `git remote set-url origin https://github.com/Richard032/TestPilot.git`. Git history and pull requests are preserved; the main-branch rename is applied separately from development-only features.

Historical prose and example paths elsewhere in this repository use the new spelling for consistency. This does not relocate old machine files, rename actual devices or rewrite existing reports. Commit IDs, external service names and historical GitHub URLs remain identifiers of the original evidence.
