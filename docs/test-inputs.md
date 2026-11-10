# Prepare a test folder

Updated: 10 November 2026. Use this workflow after [installation](installation.md); the complete YAML/command reference is in the [product guide](product-guide.md).

## Keep the inputs together

Our keyboard regression used this structure:

```text
CE1-I560/
  README.md
  default.private.yaml
  application.yaml
  setup.txt
  instructions.txt
  requirements.txt
  test.xpa
  build/
    build.sh
    android.sh
    ios.sh
  CIMT output/                  # CIMT creates this, including clone and reports
```

`README.md` explains the purpose, tested branch, prerequisites, commands and expected result. `application.yaml` references the local text inputs, fixture and wrappers. The source repository belongs to CIMT's generated work folder after cloning; do not put a second manual checkout among the authored inputs. A manually copied checkout or standalone app build does not establish replay availability.

This is the recommended complete authoring layout. The current validator checks configured inputs and script paths; it does **not** require the literal README filename or all three wrappers when defaults are used. Relative fixture containment is enforced. Do not interpret this documentation as claiming a stricter folder validator exists.

Copy the build wrappers from the installed templates, keeping all three together:

```bash
mkdir -p build
cp "$CIMT_INSTALL_ROOT/templates/test-run/build/"*.sh build/
```

Reference `./build/android.sh` and `./build/ios.sh` in the appropriate target. Both delegate through adjacent `build.sh`. Keep the fixture alongside the YAML, and use `external-files` to let CIMT copy/verify it after reset. No operator simulator-copy step is required.

## Separate app knowledge from the issue

| Input | Purpose | Example from this case |
| --- | --- | --- |
| `setup.txt` | How to reach the test state, approved permissions, credential aliases and navigation facts. | Open XPA Manager using the XPA icon on Home; select the supplied XPA and press **Open XPA**. |
| `instructions.txt` | What to exercise, reproduction steps, expected observations and permitted exploration. | Edit the lowest string field, confirm unchanged text, switch fields and repeat. |
| `requirements.txt` | Observable acceptance criteria. | The selected input remains visible above the keyboard; switching/OK remains responsive. |
| `application.yaml` | Repository/branch, builds, devices, fixtures and input references. | Select virtual devices and the issue branch; provision `test.xpa`. |

Keep navigation facts in setup rather than repeating them in every scenario. Keep issue history and previous unsuccessful fixes out of AI instructions unless they change what must be tested. CIMT treats text files as test inputs, not permission for a developer agent to execute unrelated actions. Fixture bytes are not instructions.

For reusable knowledge, maintain a reviewed setup file in Git and point `inputs.setup` to it, or copy the relevant reviewed text into this test folder. Update it deliberately when the UI changes. There is no automatic learning/publishing feature. Never add passwords, API keys, private XPA data or personal device IDs to shared knowledge.

## Real-life setup example

The following navigation came from the ECON regression. Adapt labels to the version under test; do not invent a missing item:

```text
Open XPA Manager from the XPA icon on the Home screen.
Select test.xpa and press Open XPA. Verify it opened.
In Settings, open Access Level, choose OEM and confirm the displayed value.
In Settings, enable Show All parameters and verify it is active.
Open Parameter Settings. Scroll within its parameter list to Seat.
Open Seat, scroll to Memory 1 and open it.
Locate Memory text line 1 and Memory text line 2; scroll within this list as needed.
Use configured credential aliases if authentication is requested.
If a required state cannot be reached, record the screen and blocker.
```

Do not substitute Seat Configuration for Parameter Settings. The lowest text parameter can be offscreen: scroll the correct list and observe before selecting it. Do not treat a successful picker swipe as proof of OEM access. The AI must inspect the selected value before continuing. Desired app values belong here; generic gesture syntax belongs in CIMT's command guidance.

## iOS and Android regression example

Run the same acceptance criteria on each selected platform. State the scope explicitly in `instructions.txt`, for example:

```text
Objective: verify the keyboard visibility and unchanged-text freeze fix.
For each tested platform/device:
1. Open Memory text line 2 near the bottom. Verify the active input is visible
   above the software keyboard. Press OK without changing text.
2. Repeat the same field at least three times. Verify responsiveness after each OK.
3. Alternate Memory text line 1 and 2, including switching while the keyboard is open.
   Verify the selected input remains visible; confirm unchanged text repeatedly.
4. Change text, confirm and reopen it. Check the displayed value against the save behavior.
5. Dismiss/reopen the keyboard and navigate away/back. Repeat the lowest-field test.
Try at least three additional relevant variations, such as scrolling before selection,
rapid but deliberate field changes, cancel/reopen, or a different reachable string field.
Do not alter unrelated configuration or external equipment.
After every suspected freeze, record the last action and test responsiveness with
an appropriate normal control. Distinguish an unresponsive app, slow response,
missing navigation and unavailable automation. Preserve evidence and stopping reasons.
```

Requirements can be short and independent:

```text
R1: The active string input is visible above the software keyboard.
R2: Confirming unchanged text does not freeze the app, including repeated use.
R3: Switching between string fields remains responsive with the keyboard open.
R4: Confirmed edits follow the application's stated save behavior.
R5: Each configured platform has its own evidence and unresolved work is explicit.
```

These are illustrative inputs, not a claim this test passed on both platforms. Start with `validate`; a successful validation does not prove navigation, login or application requirements. Select an iPhone simulator explicitly for an iOS-only first test; configure both virtual devices when both platforms are in scope. Use the actual device IDs only in private settings.

## Choose clone/build or replay

From the prepared folder, validation is:

```bash
cimt validate --config ./default.private.yaml --run-config ./application.yaml
```

For a new source commit, new platform artifact or changed compiled settings:

```bash
cimt run --config ./default.private.yaml --run-config ./application.yaml
```

After CIMT has retained the matching successful builds, to change only instructions/setup/fixtures and test again:

```bash
cimt replay --config ./default.private.yaml --run-config ./application.yaml
```

Run clones the configured remote branch, so commit/push required application changes first. Replay does not clone **or build**. Check its retained-build manifest rather than assuming the current application checkout is used. Current input files are reread; reset/fixture provisioning, model/budget and normal testing still apply.

## Keep shared material safe

Share reviewed instructions, requirements, templates and sanitized setup knowledge through Git. Keep private defaults, credentials, package archives, real fixtures, generated work/reports and local installation settings excluded. A missing private NuGet feed must be configured before building; our Mac used packages copied from ADATA into a local feed, as described in [installation](installation.md#9-prepare-private-git-and-nuget-access). Do not publish a working folder wholesale.
