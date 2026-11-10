# Install CIMT on a Mac

Documentation baseline: 1.0. Updated: 10 November 2026.

This is the installation how-to. It covers a developer Mac and the additional checks needed for a Jenkins account. The examples come from the Apple Silicon installation we performed together. Select the newest **compatible** tools for your checkout and application; example version numbers are observations, not permanent requirements. [Dependencies and version selection](dependencies.md) explains the sources of truth. [Installation notes](installation-notes.md) preserve the dated working log.

Installation does not start a paid test. The current `cimt setup` command is not implemented; use the steps below. Do not use the old Intel pilot bootstrap as a general installer: its downloads and workload set are fixed to that historical profile.

## 1. Choose the host, account and compatible toolchain

Use the account that will run CIMT. Check its architecture, developer tools and available storage:

```bash
uname -m
sw_vers
df -h /
xcode-select -p
xcodebuild -version
dotnet --list-sdks
```

Choose native ARM64 packages for `arm64` and x64 packages for `x86_64`. Select the newest supported Xcode that works with the chosen .NET iOS workload, application and macOS. Check the [.NET MAUI installation guidance](https://learn.microsoft.com/dotnet/maui/get-started/installation), [.NET iOS releases](https://github.com/dotnet/macios/releases), and [Apple's Xcode requirements](https://developer.apple.com/xcode/system-requirements) together. Installing the newest component independently can create an incompatible combination.

Read CIMT's `global.json`, project target frameworks and the tested application's own SDK settings before choosing an SDK. A source checkout may require a different SDK selection from the application. Do not create or overwrite an application `global.json` just to follow this guide. Current source selection is recorded in the repository, not enforced by an example command in this document.

Example used on our Apple M4 Mac: Xcode 26.5, native .NET SDKs 10.0.300 and 10.0.403, with the compatible workload set 10.0.300.3. CIMT's checkout selects the former SDK; the application, after removal of its SDK pin, selected the latter. This combination built the application; it does not establish compatibility for every later SDK/Xcode pair. A separate Debug_Pride iOS Simulator build succeeded with the project’s restored CuRMiTagger pre-build invocation; it reported 701 warnings and explicitly allowed the existing NU1701 warning. The [dated follow-up](installation-notes.md#54-general-sdkworkload-installation-follow-up--9-november-2026) records the conditions and limits.

## 2. Obtain CIMT and choose an installation folder

Choose a release or branch deliberately. This example uses the checkout location from our setup; another writable location is fine:

```bash
mkdir -p "$HOME/Development"
git clone https://github.com/Richard032/CIMT.git "$HOME/Development/CIMT"
cd "$HOME/Development/CIMT"
export CIMT_INSTALL_ROOT="$HOME/Development/CIMT/.local/install"
mkdir -p "$CIMT_INSTALL_ROOT"
```

When using an existing checkout, fetch and switch only after preserving local changes. Keep private test folders and credentials outside tracked source. A shared installation such as `/Users/Shared/CIMT` is also possible if its execution account has the required access. Routine testing must not require `sudo`.

## 3. Install Xcode and compatible .NET workloads

Install the selected full Xcode through Apple, open it, and complete its licence and first-launch steps. Select its developer directory if needed, then verify:

```bash
xcode-select -p
xcodebuild -version
xcodebuild -checkFirstLaunchStatus
xcrun --sdk iphoneos --show-sdk-version
dotnet --info
```

Install the newest SDK allowed by the relevant checkout and supported by the selected workload/Xcode release. Choose the macOS installer for the host architecture from [Microsoft's download page](https://dotnet.microsoft.com/download/dotnet). If the executable is missing from PATH, inspect the installation before reinstalling it. Our native installation was at `/usr/local/share/dotnet/dotnet`:

```bash
export PATH="/usr/local/share/dotnet:$PATH"
dotnet --version
```

MAUI workloads belong to the application's selected SDK. If its documented default workload set matches Xcode, install the required workloads normally:

```bash
dotnet workload install maui-android maui-ios --source https://api.nuget.org/v3/index.json
dotnet workload --info
```

If the .NET iOS release specifies a workload-set version, use that release's `--version` value instead. A system SDK installation may require the user to run workload installation with administrator privileges. Do not send an administrator password to CIMT or put it in a script.

Concrete example used for our Xcode installation, rather than a requirement for future installations:

```bash
sudo /usr/local/share/dotnet/dotnet workload install maui-android maui-ios --version 10.0.300.3 --source https://api.nuget.org/v3/index.json
```

Run SDK/workload verification from both the CIMT checkout and the application checkout when they select different SDKs. Keep the existing application build targets and pre-build commands. A successful CIMT CLI build alone does not prove an application can build.

## 4. Install Java and Android SDK components

Select the newest JDK supported by the application's .NET Android workload. Install the native package from your approved vendor. Our example used Temurin JDK 21 for Apple Silicon; this is not a rule to use JDK 21 for every future workload.

Install [Android Studio](https://developer.android.com/studio), open it and complete its setup wizard. In SDK Manager install the platform, build-tools, platform-tools and command-line tools required by the application's Android target. An installed Android Studio application does not by itself prove these components exist. Accept licences locally. A newer platform package is not always a substitute for the exact platform required by the workload.

Example from our Mac:

```bash
export JAVA_HOME="$(/usr/libexec/java_home -v 21 -a arm64)"
export ANDROID_HOME="$HOME/Library/Android/sdk"
export PATH="$JAVA_HOME/bin:$ANDROID_HOME/platform-tools:$ANDROID_HOME/cmdline-tools/latest/bin:$ANDROID_HOME/emulator:$PATH"
java -version
javac -version
adb version
```

Our application required Android platform 36 and build-tools 36.0.0. The selected emulator used a newer ARM64 system image. On another setup choose components from the application's target and the workload's documented requirements. If `sdkmanager` reports a CLI replacement or deprecation, use the supported SDK Manager UI or current official CLI instructions; do not assume an old bootstrap command is still appropriate.

## 5. Install the Python support runtime

Use a supported native/universal Python, at least the minimum checked by `scripts/install-cimt-runtime.sh`. Select the newest interpreter compatible with the dependencies in `runtime/requirements.txt`. Leave macOS system Python unchanged.

Our concrete example used Python 3.15.2 from [python.org](https://www.python.org/downloads/macos/):

```bash
/usr/local/bin/python3.15 --version
/usr/local/bin/python3.15 -c 'import platform; print(platform.machine())'
export CIMT_PYTHON_BOOTSTRAP=/usr/local/bin/python3.15
bash scripts/install-cimt-runtime.sh
"$CIMT_INSTALL_ROOT/tools/python/bin/python" -c 'import PIL, truststore; print(PIL.__version__, truststore.__version__)'
```

Substitute the interpreter actually selected on your Mac. The script creates an isolated environment, installs the checkout's declared requirements, copies the complete runtime packages and supplies test-folder build templates. It does not publish the .NET host or build worker; do that in step 8.

## 6. Install Node, pnpm and Mobile MCP

Install a native Node release supported by the selected Mobile MCP package. Use [Node's downloads](https://nodejs.org/en/download) and [pnpm's installation instructions](https://pnpm.io/installation). Use pnpm for Node package installation; preserve its generated lockfile. Mobile MCP is the selected adapter; Appium is not required for the normal CIMT path.

Commands used during our setup:

```bash
node --version
node -p 'process.arch'
curl -fsSL https://get.pnpm.io/install.sh -o /tmp/cimt-install-pnpm.sh
sh /tmp/cimt-install-pnpm.sh
```

Open a new shell, or load the changes made by pnpm's installer, before verifying `pnpm --version`. Choose the newest Mobile MCP version that is compatible with this CIMT checkout and verify its native helper capabilities. The following is the tested installation example, not an instruction to retain these versions forever:

```bash
mkdir -p "$CIMT_INSTALL_ROOT/tools/node-packages/lib"
pnpm --dir "$CIMT_INSTALL_ROOT/tools/node-packages/lib" add --save-exact @mobilenext/mobile-mcp@1.0.14
export PATH="$CIMT_INSTALL_ROOT/tools/node-packages/lib/node_modules/.bin:$PATH"
command -v mcp-server-mobile
```

With pnpm, the helper can be installed in a nested package directory that Mobile MCP does not discover automatically. Locate the native binary and use the supported `MOBILECLI_PATH` override rather than patching the dependency:

```bash
find "$CIMT_INSTALL_ROOT/tools/node-packages/lib/node_modules" -type f -name 'mobilecli-darwin-*'
```

Our Apple Silicon example used:

```bash
export MOBILECLI_PATH="$CIMT_INSTALL_ROOT/tools/node-packages/lib/node_modules/.pnpm/@mobilenext+mobilecli-darwin-arm64@1.0.21/node_modules/@mobilenext/mobilecli-darwin-arm64/mobilecli-darwin-arm64"
"$MOBILECLI_PATH" --version
```

Use the path returned by your installation, with the correct architecture and helper version. Device discovery can load the adapter module directly, while later execution starts `mcp-server-mobile`; verify both paths. A successful inventory query alone does not prove the server command is on PATH.

## 7. Persist the local environment

Create `$CIMT_INSTALL_ROOT/environment.sh`. If it already exists, back it up and merge the settings; do not replace user configuration wholesale. For our checkout-local installation its contents included:

```bash
export CIMT_INSTALL_ROOT="$HOME/Development/CIMT/.local/install"
export PATH="/usr/local/share/dotnet:/usr/local/bin:$CIMT_INSTALL_ROOT/bin:$CIMT_INSTALL_ROOT/tools/node-packages/lib/node_modules/.bin:$PATH"
export JAVA_HOME="$(/usr/libexec/java_home -v 21 -a arm64)"
export ANDROID_HOME="$HOME/Library/Android/sdk"
export PATH="$JAVA_HOME/bin:$ANDROID_HOME/platform-tools:$ANDROID_HOME/cmdline-tools/latest/bin:$ANDROID_HOME/emulator:$PATH"
export MOBILECLI_PATH="$CIMT_INSTALL_ROOT/tools/node-packages/lib/node_modules/.pnpm/@mobilenext+mobilecli-darwin-arm64@1.0.21/node_modules/@mobilenext/mobilecli-darwin-arm64/mobilecli-darwin-arm64"
```

Replace example architecture, Java selection, paths and helper version with the values verified above. Keep secrets out of this public example. For setup commands in the current shell, load the file:

```bash
source "$CIMT_INSTALL_ROOT/environment.sh"
```

The installed launcher loads this environment automatically. Users should not need to source it manually before every `cimt` invocation. The source launcher also discovers `.local/install/environment.sh` beside its checkout. An explicit `CIMT_INSTALL_ROOT` selects another installation. Keep the `.bin` directory for `mcp-server-mobile` in the saved environment; setting only `MOBILECLI_PATH` is insufficient.

## 8. Publish the command host and build worker

From the CIMT source checkout, with the chosen environment loaded:

```bash
dotnet publish src/Cimt/Cimt.csproj -c Release -o "$CIMT_INSTALL_ROOT/lib/cimt" --source https://api.nuget.org/v3/index.json
dotnet publish tools/Cimt.BuildWorker/Cimt.BuildWorker.csproj -c Release -o "$CIMT_INSTALL_ROOT/lib/cimt-build" --source https://api.nuget.org/v3/index.json
mkdir -p "$CIMT_INSTALL_ROOT/bin" "$CIMT_INSTALL_ROOT/scripts/build"
cp scripts/cimt "$CIMT_INSTALL_ROOT/bin/cimt"
cp scripts/build/android.sh scripts/build/ios.sh "$CIMT_INSTALL_ROOT/scripts/build/"
chmod +x "$CIMT_INSTALL_ROOT/bin/cimt" "$CIMT_INSTALL_ROOT/scripts/build/"*.sh
git rev-parse HEAD > "$CIMT_INSTALL_ROOT/source-revision.txt"
"$CIMT_INSTALL_ROOT/bin/cimt" --help
```

`source-revision.txt` is an operator receipt, not a file CIMT uses to select builds. Install host, worker and Python runtime from the same source revision. Add the installation's `bin` directory to the account's normal shell PATH if you want the short `cimt` command; otherwise use the absolute launcher path. Verify it from outside the checkout without manually sourcing the environment.

Updates use these same source-based steps while no CIMT run owns the installation. Preserve `environment.sh`, tools, private settings, test inputs and reports. Back up first and run the existing development checks before replacing the installed files. Do not copy a few newer runtime modules into an older host installation.

## 9. Prepare private Git and NuGet access

Use the execution account's normal Git credentials. Authenticate interactively in your own Terminal if necessary, then prove noninteractive access to the selected branch and required submodules. Do not embed credentials in URLs.

Example used for the application in our setup:

```bash
GIT_TERMINAL_PROMPT=0 GCM_INTERACTIVE=never git ls-remote --exit-code https://subgit.curtis.ch/ECON/ag-econ-mobile.git refs/heads/issue/CE1-I560_string_parameter_hidden_by_keyboard
```

CIMT clones the configured branch into its own work folder. Editing a separate developer checkout or `build/` snapshot does not change that clone. Supply necessary application-specific preparation through the selected branch or an explicit test-folder build wrapper, preserving the project's other build steps.

For an unavailable private NuGet service, obtain the required packages from an approved source and copy them into a persistent local feed. Our setup used four packages copied from ADATA into `$CIMT_INSTALL_ROOT/nuget-feed`; the disk did not need to remain mounted afterward. macOS removable-volume permission must be granted to the execution account before copying. Public packages still need nuget.org or an existing cache.

Example local `ag-econ-mobile.NuGet.Config`:

```xml
<?xml version="1.0" encoding="utf-8"?>
<configuration>
  <packageSources>
    <clear />
    <add key="local-private" value="/Users/your-account/Development/CIMT/.local/install/nuget-feed" />
    <add key="nuget.org" value="https://api.nuget.org/v3/index.json" />
  </packageSources>
</configuration>
```

Replace the local path. After locating the approved package folder on ADATA, copy the required `.nupkg` files into the persistent local feed. For example, replace `/Volumes/ADATA SE880/path/to/packages` with the actual folder you verified in Finder:

```bash
mkdir -p "$CIMT_INSTALL_ROOT/nuget-feed"
cp "/Volumes/ADATA SE880/path/to/packages/"*.nupkg "$CIMT_INSTALL_ROOT/nuget-feed/"
```

This source path illustrates the disk workflow; it is not a recorded package directory. Copy only the application's required approved packages. Save the XML above locally as `$CIMT_INSTALL_ROOT/ag-econ-mobile.NuGet.Config`, then pass it to **both** application platforms. Concrete example from this Mac's checkout-local installation:

```yaml
android:
  framework: net10.0-android36.0
  properties:
    RestoreConfigFile: /Users/richardsumka/Development/CIMT/.local/install/ag-econ-mobile.NuGet.Config
ios:
  framework: net10.0-ios
  properties:
    RestoreConfigFile: /Users/richardsumka/Development/CIMT/.local/install/ag-econ-mobile.NuGet.Config
```

These are fragments of an existing build target, not a complete runnable configuration. Merge them with its script, runtime, packaging and signing properties. Substitute your account/installation path. YAML build-property strings do not expand `$HOME`. In our setup this excluded the unavailable `ag-baget.eu` source. Do not commit private packages, credentials or machine-specific configuration. A NuGet error belongs to application build preparation, not AI navigation.

## 10. Prepare virtual or physical devices

Choose one device kind per run. Boot intended virtual devices before starting CIMT; it does not create or boot them for you. On Apple Silicon choose a compatible ARM64 Android image and `iossimulator-arm64` for an iOS simulator build. Intel simulator builds use their compatible x64 RIDs. Physical iOS uses its own device build/signing profile.

For Android, use Android Studio Device Manager, then verify:

```bash
adb devices -l
adb -s emulator-5554 emu avd name
adb -s emulator-5554 shell getprop sys.boot_completed
```

Use the actual serial for the ADB commands. CIMT's Android virtual-device ID is the AVD name, not the ADB serial. Our running example was `Medium_Phone_API_37.0`; another Mac can use another compatible AVD.

For iOS:

```bash
open -a Simulator
xcrun simctl list devices available
```

Choose and boot a simulator in Simulator, or use `simctl boot` and `bootstatus` with its actual UUID. In our setup the first target was iPhone 17 Pro. Ensure the software keyboard can appear on both platforms. [Virtual-device settings](virtual-devices.md) cover identifiers and build differences.

For physical Android, enable USB debugging, accept authorization and require `adb` state `device`. For physical iOS, pair/trust/unlock the phone, enable Developer Mode where required and verify it in `xcrun devicectl list devices`. Configure signing under the same execution account. Pairing history or an unavailable device is not readiness.

Simulator apps still need a signature accepted by their runtime. Our iOS simulator target explicitly used `EnableCodeSigning: true`. A phone IPA cannot be replayed on a simulator. For Android, produce an installable APK; a debug build installed outside IDE fast deployment must contain its required assemblies, for example with `EmbedAssembliesIntoApk: true` when the project needs it.

## 11. Create inputs, validate, then authorize testing

Follow the [product guide](product-guide.md) and [test-input how-to](test-inputs.md). Keep navigation knowledge, test procedure and observable requirements separate. Put required fixture files beside the YAML and declare `external-files`; CIMT copies them after reset and before launch. App setup such as OEM access and Show All Parameters belongs in the test inputs, not CIMT source.

From a prepared test folder:

```bash
cimt validate --config ./default.private.yaml --run-config ./application.yaml
```

Expected: readable inputs, required tools, noninteractive branch access, selected device inventory and a new readiness report. This makes no paid AI request and does not clone, build, install, reset or test the app. It does not prove login, signing, every NuGet dependency, a build wrapper's behavior or AI acceptance.

Only when testing and its budget/reset effects are authorized:

```bash
cimt run --config ./default.private.yaml --run-config ./application.yaml
```

`run` performs preparation/checkpoints, then clones and builds, then tests. Clone output may already have completed by the time the UI-testing stage appears. Work is under the input folder's `CIMT output/work`, not the test folder's `build/` script directory.

Use `replay` only after checking that the retained artifacts contain the required fix and platforms:

```bash
cimt replay --config ./default.private.yaml --run-config ./application.yaml
```

Replay reads current instructions but does not clone, restore or rebuild. A new branch commit or a newly added Android target needs a fresh `run`. See [retained builds](work-retention-and-replay.md). A run/replay can reset app data and incur configured AI costs; installation and readiness checks do not authorize it.

## 12. Verify results and unattended use

Open the exact dated `index.html` path printed by the command. Check command, source commit, platforms, verdict, completion and stopping reasons. `inProgress: true` means an interim report; its provisional exit code is not a final result. A successful build or visible app is not a completed functional test.

Run the [offline development checks](development.md#run-the-checks) for the checkout. They do not establish live-device acceptance. Known release gaps and observed installation profiles are in [release readiness](release-1.0.md) and [working notes](installation-notes.md).

For Jenkins, repeat readiness and a separately authorized run as the actual Jenkins account with access to the GUI session/devices, Git credentials, signing and private configuration. Omit interactive pauses or set them to `false`. Do not assume developer-account success proves unattended operation. Second-host and physical-device qualification remain separate acceptance work.
