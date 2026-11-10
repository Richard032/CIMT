# Dependencies and compatible version selection

Reviewed: 10 November 2026. This describes selection and ownership, not a permanent single-version installation manifest.

Choose the newest compatible release for the host, application and CIMT checkout. Restore the dependencies declared by that checkout. Updating a library is a source change with its own API, platform and regression checks; an installation how-to must not silently upgrade the application or replace its dependency constraints.

| Component | Version authority | Selection and verification |
| --- | --- | --- |
| CIMT .NET SDK | Root `global.json` and project `TargetFramework` values | Install a supported SDK satisfying the checkout's selection policy. Check `dotnet --version` inside the checkout. The present SDK selector is not a promise that all later feature bands work. |
| Application SDK and MAUI workloads | Application project/SDK settings, selected workload release and Xcode | Select the newest mutually compatible combination. Check from the application directory and build its actual platform targets. Do not impose CIMT's example SDK pin on the tested repository. |
| .NET libraries | PackageReference entries in `src/`, `tools/` and existing test projects | Restore declared versions. The command host uses YamlDotNet; tests use their existing xUnit tooling. Do not copy version numbers from a historical installation table into project files. |
| Python and Python libraries | `scripts/install-cimt-runtime.sh` and `runtime/requirements.txt` | Use a compatible interpreter meeting the script's minimum. Install the declared Pillow/truststore versions in the isolated environment, not system Python. |
| Node | Selected Mobile MCP package's engines and native architecture | Choose a supported release and verify `node -p process.arch` in the execution environment. |
| pnpm and adapter packages | Selected compatible Mobile MCP release and the local pnpm manifest/lockfile | Use pnpm and retain the lockfile. Check server discovery, native helper lookup and required operations before adopting an upgrade. |
| Mobile MCP / mobilecli | CIMT's adapter contract and the selected package's native helper | The source is not patched. New package versions need capability and integration checks, including credential replacement and timed gestures where used. |
| Xcode | Apple's host/SDK requirements and the .NET iOS workload's release notes | Select the newest supported intersection, complete first launch and verify the active developer directory. |
| JDK and Android SDK | Application target and .NET Android workload requirements | Choose compatible native components. Android Studio version alone does not select every platform/build-tools package. |
| Private NuGet packages | Application PackageReference values and approved feed/package availability | Configure accessible sources explicitly; a local feed may replace an unavailable service without changing package versions. |
| AI model and pricing | Effective test settings and the profiles implemented in `runtime/budget.py` | Use a supported explicit profile. No fallback or automatic model/pricing discovery exists; provider changes need a reviewed profile update before claiming a reliable bound. |

## Concrete observed example

The Apple Silicon setup used Python 3.15.2, Node 26.13.0, pnpm 12.18.0, Temurin JDK 21, Mobile MCP 1.0.14 and mobilecli 1.0.21. The application later built with SDK 10.0.403, Xcode 26.5 and its compatible workload set; CIMT's source checkout retains its own SDK selector. The [installation how-to](installation.md) shows the commands we used and how to substitute another compatible choice.

These observations establish specific evidence, not support for every combination. The [Intel pilot YAML](installed-prerequisites-macos-intel.yaml) and [installation notes](installation-notes.md) are historical receipts. They are not consumed as a general installer manifest. The old Intel bootstrap and adapter-evaluation helpers contain fixed versions and older package-manager commands; they are not the recommended generic installation path.

## Updating and diagnosing

Record source revision, architecture, SDK/workload information and adapter versions before an update. Preserve the environment file and local lockfiles. Change one dependency group deliberately, use the existing offline checks, then qualify the affected real build/device path separately. Do not install into a running CIMT installation.

A source restore can be corrected without changing library versions. During this Mac setup, stale test-project NuGet metadata incorrectly marked a single-target project as multi-targeted and omitted NUnit adapter copy items. A normal restore with the project's declared target regenerated the correct imports. This NUnit example concerns the tested application; CIMT uses its existing xUnit suite. Global target-framework overrides can affect project references; avoid them as a workaround for a platform-specific build. Select the application's actual framework with the build command and use the project's normal restore graph.

Do not disable TLS verification, signing, masking or application pre-build targets to hide dependency errors. Fix the selected version/source/profile or provide an explicit application-owned compatibility preparation. Keep machine paths, packages, credentials and test evidence outside published source.
