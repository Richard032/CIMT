# Run engine

Updated: 10 November 2026. This document describes the current execution path, not full release acceptance. [Earlier run-engine notes](run-engine-history.md) preserve dated observations. See [release readiness](release-1.0.md) for remaining qualification.

## Host and device lifecycle

The launcher discovers the installation, loads its local `environment.sh` automatically and adds installed command directories to child PATH. The .NET host allocates paired work/report identity under the selected input folder, holds the Mac-wide lock, merges YAML, snapshots text/catalogue inputs and checks runtime/device prerequisites. `validate` performs readiness checks without paid inference or application execution. `run`/`replay` also perform the configured model-access check before testing.

The fresh-run path clones the selected remote branch and recorded submodules only after preflight. Immediately before cloning, it removes older verified owned work for those same inputs. It builds configured applicable targets, retains successful artifacts in the report and publishes one successful build set for reuse. Build failures remain errors even when another target succeeds. A custom script follows the same request/result contract and project authority as the defaults.

Replay validates the retained source/profile metadata and artifact hashes, copies matching binaries into a new report and follows the normal testing path. It has no Git/restore/build fallback. It preserves previous work. See [retention and replay](work-retention-and-replay.md).

The Python worker schedules the selected startup devices, with at most two active workers and sequential targets per device. Each target/device currently receives one objective based on supplied text. It reinstalls/resets, executes optional reset/verification hooks, provisions and hashes external fixtures, launches the app and applies the implemented settling delay. iOS reinstall verifies the container but does not promise Keychain/backend reset. Reset/provisioning/privacy failure stops setup. Model-directed exploration is not automatic decomposition into independently reset semantic scenarios.

## Decision loop

AI Instruction and Context supplies original sources, current masked screenshot/UI data, credential aliases and AI-selected working context. Device Adapter owns tool I/O; Test Planning and Exploration retains AI plans/map/context; Execution Stopping Policy owns typed failure scope and aggregation. None is another testing agent. See [architecture](architecture.md) and [development](development.md).

Execution decodes complete replies into FIFO command objects and records them before dispatch. It checks mechanical arguments and limits, performs the selected operation, records actual outcomes and gathers normal masked evidence. Unexecutable commands cancel the pending tail. The next normal decision receives complete ordered batch results and current warnings, even if optional historical context is deferred. A queued `done` after actions hands their results back for a fresh decision; a first-command `done` may end the objective. No separate success-acknowledgement request is added. [Command resources](ai-resource-exchange.md), [queue](command-queue.md) and [batch feedback](batch-feedback.md) define exact boundaries.

AI chooses targets, desired values and recovery. The host does not replace missing controls or rank history for relevance. It reports malformed command shapes, unavailable resources and actual tool errors with generic guidance. Swipe coordinates are absolute device coordinates; refs are mechanically resolved to current bounds, with original and exact dispatched arguments retained. Credential replacement is locally resolved/masked and idempotent. Permission authorization, geometry, platform capabilities and privacy remain enforced.

## Budget, deadline and stopping

The configured model is used without fallback. Implemented profiles and conservative rates live in `runtime/budget.py`; use that revision rather than copying historical prices from a document. Before a paid request the shared ledger reserves the configured profile's maximum input-context cost plus the response cap. Valid usage settles unused reservation; missing/uncertain usage retains it. Both workers share the same budget. This can stop below the nominal cap and is not an exact provider invoice or account-wide spending limit.

The deadline begins at CLI entry and includes preparation, builds, interactive waits and inference. An app launch failure stops the affected device; other devices may continue. Three matching crash attempts stop the affected objective. Shared infrastructure/privacy/reset errors and time/budget/cancellation follow the [stopping contract](execution-stopping.md). Known findings and unfinished work survive later errors. Final reporting needs no paid call.

Exit precedence is infrastructure/configuration/build error (3), test failure (1), incomplete (2), pass (0). Verdict and completion are independent. Successful navigation, tool calls and application builds do not establish requirement acceptance. See [requirement mapping](requirement-mapping.md).

## Persistence and evidence

Lossless PNG screenshots and UI text are masked before storage/submission. Unreliable required masking stops execution. Records retain original redacted replies, queued command states, actual actions, requirement checks, usage, diagnostics and stopping reasons. Reports are portable using their relative evidence links, subject to missing evidence being explicitly reported. Historical reports are not rewritten by runtime updates.

Finalization stops the owned helper, saves redacted diagnostics, retains work/artifacts and releases the lock. A failed helper stop retains verified ownership information for later recovery. No unrelated checkout is adopted or deleted. Interim reports can show provisional incomplete status; hard termination cannot guarantee finalization. [Run identity](run-identity.md), [diagnostic reporting](diagnostic-reporting.md), [redaction](redaction.md) and [screenshot masking](screenshot-masking.md) supply detailed contracts.

## Verification boundary

Run the existing offline bundle with `bash scripts/check-development.sh` from a prepared checkout. The [current implementation status](implementation-status.md) records executed results and the output-layout fixture blocker. Simulated checks establish protocol behavior, not live navigation quality, complete device qualification or measured AI cost savings. Real application builds on this Apple Silicon Mac are recorded separately from functional acceptance.
