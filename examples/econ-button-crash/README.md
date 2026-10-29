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

The source project's pre-build invokes a Windows executable and Windows copy
command. The example's replacement scripts call CIMT's default build scripts with
a late MSBuild target import. It runs the same tagger through the installed Mono
runtime and uses MSBuild Copy. It does not bypass tagging or edit the developer's
checkout. Generated version/resource changes remain in the disposable clone.
Application IDs are explicit build properties matching the selected branding.

The adapter's MSBuild import has been fixture-tested to invoke the tagger and
copy resources while preserving unrelated project targets. Actual ECON builds
through this integration still need the first configured run; fixture success is
not a real application build result.

## Output and limits

Run this installed command from any folder; configuration and inputs need not live
in the CIMT source checkout. The folder containing --run-config is the input folder,
or --config when no override is supplied. Users supply inputs only. CIMT creates
CIMT output/reports/report_<date-time> and CIMT output/work/work_<date-time>
under that input folder. Temporary source is removed after the run. Screenshots, actions,
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
