# Default build scripts

Date: 28 October 2026  
Status: scripts implemented and contract-tested; real application artifact validation blocked

## Installed locations

- /Users/Shared/CIMT/scripts/build/android.sh
- /Users/Shared/CIMT/scripts/build/ios.sh
- Shared .NET worker: /Users/Shared/CIMT/lib/cimt-build/cimt-build.dll

Source lives in scripts/build and tools/Cimt.BuildWorker. User replacements remain supported. Supplied defaults may be replaced on update; separate custom copies must be preserved.

## Environment contract

| Variable | Meaning |
| --- | --- |
| CIMT_REPOSITORY_ROOT | Absolute path to the temporary application clone. |
| CIMT_BUILD_REQUEST | Absolute path to the JSON request file. |
| CIMT_BUILD_RESULT | Absolute path where successful artifact/app-id JSON is written. |
| CIMT_BUILD_WORKER | Optional explicit worker assembly path. |
| CIMT_DOTNET_EXECUTABLE | Optional explicit dotnet executable, for a selected toolchain or contract testing. |

No secret values need to be supplied as shell-script arguments. MSBuild properties are passed as separate arguments to dotnet; configured sensitive property values are redacted from captured build output. Further evidence/credential protection belongs to the full run engine.

Request example:

```json
{
  "project": "EconMobile.Common/EconMobile.Common.csproj",
  "configuration": "Release_Generic",
  "framework": "net10.0-android36.0",
  "properties": {},
  "artifact": "optional/fallback.apk",
  "app-id": "optional.fallback.identifier"
}
```

Project paths remain relative to the clone root. Properties are application-specific scalar MSBuild values. Android defaults request APK output. iOS defaults request physical ios-arm64 IPA output. The scripts do not automatically alter source code or skip repository build targets.

Success writes absolute artifact and app-id JSON to CIMT_BUILD_RESULT, separately from build logs. MSBuild-derived values take precedence over configured fallbacks. Multiple signed artifacts are rejected unless an explicit fallback resolves the choice. A previous result file is removed before building so failure cannot reuse stale metadata.

## Invocation example

After creating a real request file outside source control:

```bash
source /Users/Shared/CIMT/environment.sh
export CIMT_REPOSITORY_ROOT="/absolute/path/to/temporary-clone"
export CIMT_BUILD_REQUEST="/absolute/path/to/request.json"
export CIMT_BUILD_RESULT="/absolute/path/to/result.json"
bash /Users/Shared/CIMT/scripts/build/android.sh
```

For iOS, set an iOS framework in the request and invoke ios.sh. A failed publish returns its nonzero exit status and produces no successful result. CIMT's initial run engine translates build failures into final exit code 3 while continuing other targets, including when a script returns unusable metadata.

## Verification

The worker builds with zero warnings/errors. Four simulated contract checks cover Android/iOS success metadata, build-failure status propagation and stale-result removal, ambiguous artifact rejection, and configured signing-value redaction. These fixtures do not compile or install a demo application.

Run from the source checkout:

```bash
dotnet build tools/Cimt.BuildWorker/Cimt.BuildWorker.csproj -c Release
python3 tests/check-build-contract.py
```

Real source validation used the supplied Subgit repository, main at commit 7443429841616783225238c92b3dc4699a65e9f3, with its declared submodules.

- Android: the application pre-build invokes the Windows CuRMiTagger.exe directly and runs copy /Y. Execution stops at the .exe with code 126 on macOS.
- iOS: no usable provisioning profile is available for ECON-M.
- Neither attempt produced installable artifact metadata.
- A separate branding-library build succeeded; it is not an installable app result.
- The SDK warns that the installed JDK's four-part version is not recognized by its older version parser. This warning is recorded; it was not suppressed.

A test-only global OutputType override initially affected referenced projects and was removed. The reported real-build blockers above are from attempts using the application's own project settings.

The original developer checkout was unchanged. The temporary clone is removed after recording results; diagnostic evidence remains outside it.

## Remaining

Resolve or explicitly configure the application's macOS pre-build compatibility and iOS signing, then rerun artifact/install checks. The scripts do not bypass these prerequisites, and their present status must not be described as successful end-to-end MAUI builds.

## Main-branch example integration

The [button/crash example](../examples/econ-button-crash/README.md) supplies replacement scripts that delegate to these installed defaults. A late MSBuild import runs the same CuRMiT tagger through Mono and replaces Windows copy with MSBuild Copy, only in the executable app project. Branding application IDs are explicit build properties. Source changes and generated resources stay in the disposable clone.

One MSBuild fixture check verifies tagger invocation, resource copying, and isolation from unrelated projects. It does not prove that the real tagger, signed MAUI builds, or app installation succeed. The first configured public run must verify those paths; refreshed iOS profiles also need revalidation.

## Replacement-script result resolution

The public run path resolves artifact and app-id separately. Returned script fields take priority; YAML supplies only missing fields. A successful script may omit its result file if YAML supplies both fields. Script artifact paths must be absolute. YAML artifact paths resolve from the temporary clone root. An invalid returned field, malformed JSON, missing resolved field, or absent artifact is a failure for that target; later targets are still attempted.

Small policy tests cover both sources and invalid values. Temporary-file integration tests cover no result file, partial results, and an invalid result followed by another successful target. They do not compile the real application.
