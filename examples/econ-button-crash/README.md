# Main-branch button/crash example

This is the user-facing test example for the supplied ECON MAUI repository.
All run configuration, text inputs, and application-specific build integration
live in this folder. CIMT and its Mac prerequisites must first be installed.

The initial single-objective run engine is implemented and its policy/contract
checks pass. This example has not yet completed a real application test. Its
live run is waiting for the existing API key to be configured locally; no crash
finding or application pass has been claimed.

## Configure once

Copy default.example.yaml to default.private.yaml and fill the existing OpenAI key
locally. Keep private YAML readable/writable by its owner only. Real login
credentials, if needed, belong in the private YAML as named credentials; do not
put them in the tracked text files. default.private.yaml, work, and reports are
ignored by Git. No key is bundled.

An owner-only default.private.yaml was prepared on the development Mac without a
key. On a fresh checkout:

```bash
cp examples/econ-button-crash/default.example.yaml examples/econ-button-crash/default.private.yaml
chmod 600 examples/econ-button-crash/default.private.yaml
```

Fill the key in the local editor. Do not paste it into chat or commit it. The API
key needs model-read access for the preflight and Responses access for inference.

The example uses the explicit GPT-5.4 Mini snapshot, USD 5 whole-run budget, and
60-minute whole-run limit. Change these before a run when appropriate; supported
pricing profiles must have conservative reservation bounds. The snapshot and
published pricing were checked on 28 October 2026 in the
[official model documentation](https://developers.openai.com/api/docs/models/gpt-5.4-mini).

## Start as a user

From the CIMT source folder:

```bash
source /Users/Shared/CIMT/environment.sh
cimt validate --config examples/econ-button-crash/default.private.yaml --run-config examples/econ-button-crash/application.example.yaml
cimt run --config examples/econ-button-crash/default.private.yaml --run-config examples/econ-button-crash/application.example.yaml
```

The application example enables execution.interactive-pauses. CIMT displays the
next operation and waits for Enter before OpenAI preflight, repository access/builds,
and AI testing after any successful build. Messages are generic and contain no
network-change instructions. Complete your own preparation, then press Enter.
Waiting counts toward the 60-minute run limit. The key value is never shown;
configuration is still loaded at startup.

Jenkins runs the same command under an account with Git, signing, and device access.
Use execution.interactive-pauses: false in its per-run configuration. Omitted also
means false; enabled pauses with redirected input fail explicitly. See the
[interactive-pause walkthrough](../../docs/product-guide.md#interactive-pauses).

Keep both phones unlocked. Locked devices are reported as incomplete and receive
no application actions. The native automation daemon is isolated per CIMT run.

## Build integration

Both Release_Generic and Release_Pride are configured for Android and iOS. CIMT
clones main and its recorded submodule revisions, builds every compatible
target/device combination, and records the source commit in the report.

The application project and selected build configuration own CuRMiT and other tool
integration. The example adapter does not add tool calls. It replaces only the
known Windows resource-copy Exec with portable MSBuild Copy inside the disposable
clone, then delegates to CIMT's installed defaults. Other target steps, imports,
conditions, and configured properties are preserved. If that exact command is
absent or appears more than once, the project stays unchanged. The build log
states whether a replacement was made. Application IDs remain explicit branding
properties.

The earlier adapter incorrectly forced the legacy CuRMiTagger.exe through Mono,
even on a branch that removed that call. Its macos.targets/prebuild.targets
files have been removed. Update build/build.sh and remove those obsolete local
files when updating a separate copy of this example. Project-defined tool
integration continues to work through normal MSBuild evaluation.

Four small MSBuild fixture tests verify resource copying without a tagger,
project-configured tool/property preservation, unrelated pre-build steps, and
conditions. The default-worker contract checks also pass. These fixtures do not
establish a successful real MAUI build, signing, installation, or test run.

## Output and limits

Run this installed command from any folder; configuration and inputs need not live
in the CIMT source checkout. The folder containing --run-config is the input folder,
or --config when no override is supplied. Users supply inputs only. CIMT creates
CIMT output/reports/report_<date-time> and CIMT output/work/work_<date-time>
under that input folder. Work and publish output remain after execution and are
replaced only immediately before a new clone for these inputs. Screenshots, actions,
interpretations, crashes, blocked paths, and coverage must be described in HTML.
All reachable buttons is an exploration objective; hidden/equipment-dependent
states and exhausted limits must be reported honestly.

Exit codes: 0 passed, 1 test failure/crash, 2 incomplete, 3 configuration,
infrastructure, or build error. Final adapter and full-product acceptance remain
separate from this example.

The first runtime supports this explicit GPT-5.4 Mini snapshot and USD accounting.
Unknown model/currency pricing is rejected before inference. Maximum output is
bounded and each request reserves its full context cost before being sent; API
timeouts retain the worst-case reservation. This is conservative accounting rather
than an exact provider invoice. Local host code, not the model, owns these limits.

iOS uninstall/reinstall verifies the app container, not Keychain or remote backend
state. Supply reset.command/reset.verify-command when application state requires
additional reset. Named credential entry requires a stable element identifier so
screenshots can be masked reliably; unavailable masking stops the run.

## Replay the retained app

After a completed build stage with a successful app, run the same inputs without cloning/building:

```bash
cimt replay --config ./default.private.yaml --run-config ./application.example.yaml
```

Replay uses the latest published app set for this input folder, current text inputs and credentials, and a new report. It verifies original build identity, branch/profile compatibility, paths, and artifact digests. Earlier work remains. No retained build means an explicit error, not an automatic build. Saved-action-history replay with --scenario is not implemented. The default worker now preserves project/default properties; explicitly configure APK/IPA output when the project needs it. See [retention and replay](../../docs/work-retention-and-replay.md).
