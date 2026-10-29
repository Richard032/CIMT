# Retained work, build properties, and replay

Updated: 29 October 2026. This policy supersedes deletion after execution and automatic deletion on the next startup.

## Working files

CIMT creates paired work_<UTC-date-time> and report_<same-date-time> folders under the selected input folder's CIMT output. Users still supply only YAML, referenced text inputs, and optional custom scripts.

After a run succeeds, fails, or stops, CIMT keeps the checkout, publish folders, intermediates, and diagnostics that remain in its work folder. It stops its owned helper, redacts/saves its helper log, and releases the short helper link only after a successful stop. A failed stop keeps the verified link for recovery. Reports and copied app artifacts remain separate from work.

A new normal run first performs configuration/input/runtime preparation, OpenAI preflight, device discovery, and any configured acknowledgement. Only immediately before Git clone does CIMT remove earlier verified owned work for that same input folder. The new run's work, other input folders' work, unrelated files, and reports are preserved. A failure before clone, validate, or replay does not remove previous work. Interrupted helper recovery stops/releases the owned helper without deleting its work. The ownership registry supports the earlier single-record format and tracks retained work across input folders.

Work stays owner-only. Private build requests keep their existing owner-only permissions. Retention is not a promise that build tools never create/delete their own temporary files; CIMT finalization no longer clears the checkout or publish directories.

## Build properties

The default worker forwards the YAML project, configuration, target framework, and properties. Missing properties are evaluated by that project and SDK. CIMT does not inject AndroidPackageFormats, RuntimeIdentifier, BuildIpa, or ArchiveOnBuild, and does not silently replace explicit values.

The selected physical-device adapter needs installable APK/IPA files. If the project produces no supported artifact, CIMT reports that clearly; it does not rewrite the build settings or automatically rebuild with another profile. Artifact ambiguity still requires an explicit fallback or replacement script. Existing FirstRun properties have not been changed.

For a project that needs them, these are optional explicit YAML properties; choose them for the actual project rather than assuming every application needs them:

```yaml
android:
  framework: net10.0-android
  properties:
    AndroidPackageFormats: apk
ios:
  framework: net10.0-ios
  properties:
    RuntimeIdentifier: ios-arm64
    BuildIpa: true
    ArchiveOnBuild: true
```

## Reuse built apps

A completed build stage with at least one successful artifact writes CIMT output/retained-builds.json automatically before device testing. It describes that build run's successful apps, original repository/branch/commit, target/project/configuration/framework, report-relative artifact paths, and SHA-256 digests. It contains no API key, credentials, or signing properties. A stage with no successful apps leaves the prior successful record unchanged. A build stage interrupted before publication also leaves the prior record unchanged; its report/work may still contain partial output.

Normal execution remains:

```bash
cimt run --config ./default.private.yaml --run-config ./application.yaml
```

To execute the current input instructions using the latest published successful builds from this input folder:

```bash
cimt replay --config ./default.private.yaml --run-config ./application.yaml
```

Replay performs no Git clone, submodule update, package restore, or application build. It preserves existing work, verifies retained metadata and artifact digests, copies the already built app into its new report, and uses normal device reset/setup, current credentials, OpenAI model/budget, time limit, masking, and observation rules. The new report records command=replay, the original build run and commit, and the new replay identity.

The cached repository/branch must match the selected configuration. Matching target names also require the same project/configuration/framework. Missing, changed, unsafe, or incompatible retained artifacts stop explicitly; replay never silently rebuilds. Targets without a matching retained artifact remain unexecuted/incomplete. The original artifact's identity and compiled properties remain unchanged: editing YAML build properties cannot change an already built binary. Use run for a new application build. Current test instructions/requirements/setup are read anew.

The manifest selects one build run's available apps, not a mixture from different commits. Apps are copied to the replay report so that report remains independent and portable. Work deletion before a later clone cannot delete these report artifacts. Manually deleting the source report/artifact makes the corresponding retained app unavailable.

This increment supports rerunning current text instructions against retained apps. Saved-action-history/adaptive scenario replay under FR-22 remains unfinished; --scenario is explicitly rejected rather than ignored. No successful real application build or device replay is claimed by the offline tests.
