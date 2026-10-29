# Shared run identity

Implemented: 28 October 2026; input-local placement updated 29 October 2026 under FR-08, FR-30, FR-52/FR-53, and AC-22/AC-25/AC-26.

## Folder contract

Each invocation captures its start time once. One identity selects the temporary and retained folder pair:

```text
<input-folder>/CIMT output/work/work_2026-10-28_14-30-00-123/
<input-folder>/CIMT output/reports/report_2026-10-28_14-30-00-123/
```

The date-time portion is identical. Neither name has an independent counter or random suffix. OutputLayout chooses the folder containing --run-config, or --config when used alone, and places all run-owned output under its CIMT output subfolder. Launch location and source checkout do not select output. Legacy root settings are ignored with a notice. Users do not create any output folders.

The design left the precise timestamp format, timezone, and collision handling open. The implementation uses UTC and yyyy-MM-dd_HH-mm-ss-fff with invariant digits and millisecond precision. These complete the open engineering details; they do not replace the required prefixes or shared timestamp.

If either candidate path is occupied by a folder, file, or symbolic link, both names advance together by one millisecond. An existing report or work folder is never adopted or overwritten. A short-lived exclusive reservation also prevents competing error reports from selecting the same report name. An old reservation is treated as occupied rather than deleted as somebody else's data.

The identity records both the actual invocation start and the selected folder timestamp. A collision can advance the folder timestamp; it does not change the actual start or extend the run deadline. The deadline still starts at invocation, including configuration and preparation time.

## Creation and ownership

The command acquires the Mac lock before configuration/execution and keeps it through normal finalization and error reporting. A rejected invocation does not build, create clone work, or clean up the active run. Its own error report receives a separate identity and cannot overwrite the active report.

RunFolderAllocator creates the retained report first and selects the work path. WorkDirectoryManager later creates precisely that work folder when preparation needs it. It receives the selected pair and never reads another clock or generates another folder name. Validation and early-error reports can therefore have an identity without creating a temporary clone folder.

Reports must remain outside temporary cleanup folders. The checks resolve filesystem aliases, reject reports below CIMT-owned work ancestors, and protect a retained report before removing interrupted work. If an allocated work path becomes occupied before creation, CIMT stops instead of adopting it. Ownership tokens still protect deletion; their internal random values are not folder-name suffixes.

Legacy ownership records remain readable, so an earlier interrupted work folder can be removed after its path/token are verified. Existing retained reports are not renamed. Full interruption history and graceful cancellation remain separate release work.

## Retained identity and propagation

run-identity.json is saved beside index.html and uses report-relative folder names. It retains the identity, actual start, UTC folder timestamp, timezone, and paired names. It remains after clone deletion and after copying the report folder.

The same identity is included in final run results, validation/error results, HTML, progress.json, the runtime request, and worker ui-results.json. Build/reset/helper processes receive CIMT_RUN_ID. The shared identity is ordinary host metadata; no model call is needed to create it.

Keep the whole report folder when copying it. Evidence links remain relative. Cleanup removes only verified owned work, and never the retained report or its screenshots/actions.

## Verification and use

Command syntax is unchanged. New YAML templates omit workspace.root/reports.root; older values still load but no longer relocate output. Continue to use cimt validate and cimt run as documented. New folders use the UTC format above; older retained report folders remain unchanged.

Run the offline development checks from the source folder:

```bash
bash scripts/check-development.sh
```

The focused cases cover UTC formatting, the single clock read, paired names, collisions on either root, reservation/file/link collisions, original deadlines, metadata, report retention/copying, declaring-file roots, nested/aliased report rejection, interrupted-cleanup protection, and command lock/error paths. The public-command regression captures the actual work name before cleanup and checks it against the retained report and runtime identity afterward.

The [offline mapping demonstration](../examples/requirement-mapping/README.md) also uses the shared allocator and includes run-identity.json in its synthetic report. It does not create a real application clone or use a phone/API. Its expected failure/incomplete result is unrelated to identity allocation.

First-Mac verification: 119 .NET unit tests, 88 Python unit tests, and 23 regression/contract checks passed: 230 checks total. No live API, real MAUI build, or physical device was used. Jenkins and second-Mac execution acceptance remain separate; the same CLI and declaring-file path rules apply.
