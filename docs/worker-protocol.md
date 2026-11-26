# Private host and worker protocol

The .NET host starts the Python worker with one JSON object on standard input. The worker exits with a status and publishes redacted files in the allocated report folder. The host and worker emit protocolVersion 1. Readers also accept a missing version for existing installations and saved snapshots. Readers reject explicit unsupported versions with an installation mismatch error. Unknown additional fields can be ignored. Install matching host and worker versions together.

## Request

| Field | Execution and preflight | Proposal |
| --- | --- | --- |
| protocolVersion | Integer 1 | Integer 1 |
| config | Effective YAML mapped to a JSON object | Same |
| report | Path to the allocated report folder | Same |
| deadline | Finite UTC epoch seconds for testing | New post-run deadline, independent of the expired testing deadline |
| proposalRequestSeconds | — | Per-request bound: currently 60 seconds |
| learning | Boolean enabling optional app-knowledge resources | Same; controls the independent knowledge proposal |
| inputs | Object with original instructions, requirements and setup when supplied | Same |
| runId, work | Host run identity and working path | — |
| devices, builds | Arrays for startup devices and prepared builds. May be empty at preflight. | builds supplies tested application identities; devices is not needed |
| nativeHome, nativeBinary | Adapter storage path and native helper path, when discovered | — |
| requirements | Array of structured requirements | — |
| resetDirectories, externalFiles | Reset script origins and resolved fixture mappings | — |
| outcome | — | Command, exitCode, deviceExitCode, cancelled, errors and stoppingReasons |

Preflight is selected by --preflight and proposal by --proposal. No flag selects device execution. Readiness checks use preflight without inference. The worker validates the envelope, mode-specific field types and deadline before constructing services. Device and build entries include platform. Device entries include id. Prepared build entries include target, artifact and app-id. Treat config as private because it carries provider credentials and local settings. Do not persist or log the raw request.

## Results

During device execution, RunJournal atomically replaces ui-results.json. The envelope contains protocolVersion, runId, devices and budget. Each device result carries index, device identity, error, stoppingReason and scenarios. A scenario records target, completion, verdict, crashes, steps and available planning, checks, request and evidence fields. Reports may read the snapshot at any time. A missing snapshot means there is no device evidence yet. File paths inside the report refer to masked evidence or redacted artifacts.

The separate atomic ai-budget.json ledger provides the latest usage, including proposal usage. RunFinalization validates the worker snapshot and calculates coverage, verdict, completion and exit code. It supplies these in RunReportData to the report writer; the reporting diagnostics read the latest usage ledger separately. Proposal budget overruns are reported without changing the test verdict. The worker exit code is a device-level result. The host applies overall precedence with build and infrastructure failures, cancellation and requirement coverage. Invalid result envelopes and malformed device or scenario outcome records are reported as infrastructure errors at finalization. The original snapshot stays available for diagnosis. instruction-setup-proposal.md records the instruction/setup draft or unavailable status. With Learning enabled, knowledge-proposals.json records independent pending changes or unavailable status; generation does not write approved knowledge. Post-run requests restore the shared ledger and use new bounded windows even after testing time or budget has expired. The current host allows 60 seconds per proposal request and an outer worker timeout of 65 seconds, or 125 seconds with Learning. Interactive AI-testing authorization still applies. These timeouts do not extend device execution.

The existing Python tests cover current and unversioned request envelopes and rejection of an unknown version. The fake-worker CLI fixture verifies that preflight, execution and proposal receive version 1 and that the host consumes versioned results. Existing report tests cover legacy snapshots and a final report for an unsupported result version.
