# Shared application knowledge

CIMT keeps reusable, AI-authored app guidance here, separately from issue instructions, requirements and test results. Guides are keyed by verified application ID and platform:

`knowledge/apps/<ios|android>/<appId>.json`

```json
{
  "schemaVersion": 1,
  "appId": "org.example.app",
  "platform": "ios",
  "guide": "Open Settings from the menu. Verify the displayed value after changing a selection.",
  "source": {
    "runId": "example-run",
    "appCommit": "application-commit",
    "target": "Debug",
    "observedStepCount": 12
  }
}
```

This example describes the format; it is not an observation from an actual run. CIMT supplies identity and provenance. AI supplies the guide based on observed behavior, using stable UI identifiers, labels, navigation and relevant conditions. Exclude credentials, credential aliases, private paths, fixture filenames, issue IDs, test verdicts, temporary refs and screen coordinates. Known configured secrets are redacted before storage; review the remaining text before merging.

## Learning and reuse

During normal decisions, AI can return `learnedAppKnowledge` as a complete updated guide. Omitted/null keeps the last proposal; invalid metadata returns resource feedback without discarding the selected device action. AI should consolidate observed knowledge in its final standalone `done` reply. A finish queued behind device actions cannot contribute predicted results. No separate summarization request is made. Current test instructions and supplied manual setup take priority, and AI must check guidance against current UI evidence.

Each run fetches its configured shared Git branch and loads only that branch's guide for the current app ID/platform. Unmerged PRs and local unstaged guide edits are not reused. After a PR is merged, later runs automatically receive the guide. Git history retains previous versions. Guidance can become stale after app changes; it is not proof of current behavior.

Per-device/target drafts remain in the report under `app-knowledge-proposals/`, with their source run, application commit, target and observed step count. If multiple devices/targets update the same app/platform, all drafts remain in the report and the last completed snapshot is proposed. CIMT does not semantically merge competing guides. Different apps/platforms share one run PR.

## PR publication

After device workers finish, CIMT creates a commit containing only guide files, pushes a unique `knowledge/app-guide-<run hash>` branch and opens a GitHub PR against the configured shared branch. It never merges the PR, pushes to the shared branch, switches the developer's branch or changes the working tree/index. Publication uses a temporary Git index and refuses to overwrite an existing proposal branch.

Explicit interruption skips publication and keeps drafts. Time limits bound Git/HTTP operations; expired runs retain drafts. Authentication, fetch, push and PR failures are reported as knowledge-publication status independently of the application test verdict. `branch-pushed` means PR creation failed after push; inspect the recorded branch before opening a PR manually. CIMT does not claim `pr-created` until GitHub returns a valid PR URL.

The local installation setting `state/app-knowledge-settings.json` selects the Git checkout, remote and shared branch. The source installer creates it from the installing checkout's branch if absent and preserves it on later installs. A detached checkout needs `CIMT_KNOWLEDGE_BASE_BRANCH`. A missing marker disables the feature for older installations; malformed settings are a configuration error. The checkout must remain available to the runtime.

```json
{
  "repository": "/absolute/path/to/CIMT",
  "remote": "origin",
  "baseBranch": "your-shared-branch"
}
```

Initial publication supports GitHub remotes. Configure Git author name/email in that checkout and provide `GH_TOKEN`/`GITHUB_TOKEN` or a noninteractive Git HTTPS credential helper. The token needs repository Contents and Pull requests write permissions. Keep tokens in the private installation environment or a credential manager, never in Git or test instructions. A desktop connector session is not runtime authentication. With an SSH remote, Git fetch/push also requires working noninteractive SSH authentication. See [GitHub create-PR documentation](https://docs.github.com/en/rest/pulls/pulls#create-a-pull-request).

Offline unit tests cover guide matching, redaction, proposal retention, normal-request reuse, deferred finishes, isolated Git commits and PR protocol/failures. Actual AI learning quality and authenticated end-to-end publication require a user-started run and configured runtime credentials.
