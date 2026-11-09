# iOS build comparison: Visual Studio and CIMT

Date: 30 October 2026, Europe/Zurich.

## Scope and evidence

The product owner confirms that Visual Studio 2026 runs Debug_Pride from testing/curmitAndNugets on the same iPhone. The CIMT evidence is report_2026-10-30_11-53-25-302, built from debc686e00cb8b98c1d32cd287625e422919c289. This review reads saved artifacts, source, installed build targets, and local Visual Studio caches. It does not build, install, launch, or change an application.

No current Visual Studio 2026 binary build log or matching generated app was available. The complete cached Visual Studio app found on this Mac is an older net9.0-ios Debug_Pride build. It supplies useful manifest evidence, but it is not proof of every setting in the current Visual Studio build. The newer Pair to Mac cache contains dependency resources but no complete app or binary log.

## Main finding: missing generated iOS manifest

The retained clean CIMT checkout contains EconMobile.Common/Platforms/iOS/Info.Template.plist, but not Platforms/iOS/Info.plist. The repository ignores Info.plist. CuRMiT-project.xml lists this file as generated output. The testing branch removed the legacy generator call, and the actual CIMT build did not produce its expected manifest.

The template contains the Bluetooth usage description, icon selection, external accessory protocols, background settings, document types, transport settings, and generated version/tagging metadata. The packaged CIMT app lacks these application-specific values. Its Info.plist instead contains basic generated application metadata, including version 1.0 / build 1.

The cached Visual Studio source manifest contains the Bluetooth description and XSAppIconAssets=Assets.xcassets/appicon.appiconset. Its packaged app contains compiled icons and the Bluetooth description. This supports the explanation that the Windows development workspace has generated, ignored inputs that are absent from the clean CIMT checkout. The exact current Visual Studio generation step still needs its build log or Windows source-manifest comparison.

## Comparison

| Area | Visual Studio path | CIMT path |
| --- | --- | --- |
| Source | Existing Windows workspace, with generated/untracked files potentially present | Fresh clone and recorded submodule revisions |
| Native compilation | Apple build tools on the paired Mac | Apple build tools on the local Mac |
| Build operation | IDE build, deployment, and debugger launch; exact current command not captured | dotnet publish of EconMobile.Common.csproj, Debug_Pride, net10.0-ios, ApplicationId=ch.curtis.econ-i |
| Runtime architecture | Exact current invocation not captured | ios-arm64, verified from output and evaluation |
| Tool installation | Pair to Mac root contains SDK 10.0.400 and Apple pack 26.5.10301; its Build agent log identifies this root | Isolated CIMT SDK 10.0.300; separate installed Apple packs |
| Application manifest | Generated manifest exists in the historical VS cache | Source manifest absent; packaged application-specific settings missing |
| Icon | Historical VS app has CFBundleIcons and Assets.car | No CFBundleIcons, icon selection, or Assets.car in the IPA |
| Bluetooth permission description | Present in historical VS manifest and repository template | Missing from the IPA |
| Launch | IDE-managed deployment and debugger connection | IPA installation and launch through Mobile MCP/mobilecli |

The installed Pair to Mac SDK is not proof that the current Visual Studio project selected that version. SDK/tool differences should be aligned when reproducing, but they do not explain away the confirmed missing manifest.

## Icon investigation

The Pride project declares its iOS MauiIcon. The saved Common-project mauiimage.inputs also contains the imported Pride icon with IsAppIcon=True. Therefore, the icon was found by MAUI resource collection; it was not simply absent from the referenced library.

The expected source manifest supplies XSAppIconAssets. That manifest is absent in the clean build, and the IPA has neither compiled icon metadata nor its asset catalogue. This is strong evidence that the missing generated manifest explains the placeholder icon. Microsoft documents the iOS icon selection in Info.plist for SVG/PNG icons.

## Startup crash investigation

The product owner observes a crash after startup. The saved CIMT report contains no matching crash diagnostic, so it does not establish the native termination reason.

The IPA lacks NSBluetoothAlwaysUsageDescription. The application uses Bluetooth, and the repository template contains that required description. This is a strong candidate for termination when startup first accesses Bluetooth. Apple requires the purpose string for Bluetooth access. Confirm the actual termination with the iPhone crash report or device console before calling it the proven crash cause.

Other missing manifest settings can also change application behavior. The repair should restore the intended complete generated manifest, not only add an icon or a single permission key.

## Build versus publish

Read-only MSBuild evaluation used the same project, Debug_Pride, net10.0-ios, ios-arm64, and ApplicationId for both local build and publish contexts. Both evaluated to:

- MtouchDebug=True.
- UseInterpreter=true and MtouchInterpreter=all.
- MtouchLink=SdkOnly and TrimMode=partial.
- DefineConstants=__IOS__;__MOBILE__;__UNIFIED__;TRACE;DEBUG_PRIDE.

This is not a captured Visual Studio invocation. It shows that changing only the local publish operation to build does not restore the absent source manifest or change these evaluated settings. No full build was performed for this comparison.

## Next work

1. Identify the intended project-controlled generation of Info.plist on a clean Mac. Preserve its real version/tagging policy; the template still contains placeholders.
2. Make the application build supply that complete manifest before iOS manifest compilation. Keep the logic in the application project/tool integration, not an implicit CIMT source rewrite.
3. Check the newly packaged IPA for the icon, Bluetooth description, and other expected manifest settings.
4. Capture an iPhone startup diagnostic and verify launch before autonomous UI exploration.
5. Compare the current Visual Studio binary log if toolchain, signing, trimming, or debugger differences remain after the manifest repair.

CIMT's separate wrong-app identity/foreground defect remains open. This comparison does not change that behavior.

## Sources

- Repository: .gitignore line 370; CuRMiT-project.xml line 18; EconMobile.Common/Platforms/iOS/Info.Template.plist lines 5 and 38.
- Retained run: /Users/sumkar/Development/Testing/TestRun_SingleDevice_SingleTarget/CIMT output/reports/report_2026-10-30_11-53-25-302.
- Historical VS app: /Users/sumkar/Library/Caches/Xamarin/mtbs/builds/EconMobile.Common/286a04a3a12ed1aad7e9e85117ea6d80070815a45077277b3c91bc5aca6965b1/bin/Debug_Pride/net9.0-ios/ios-arm64/device-builds/iphone14.7-26.6/ECON-M.app.
- [Microsoft: command-line iOS publishing and the VS2026 remote SDK path](https://learn.microsoft.com/en-us/dotnet/maui/ios/deployment/publish-cli?view=net-maui-10.0).
- [Microsoft: MAUI app icons and platform configuration](https://learn.microsoft.com/en-us/dotnet/maui/user-interface/images/app-icons?view=net-maui-10.0).
- [Apple: NSBluetoothAlwaysUsageDescription](https://developer.apple.com/documentation/bundleresources/information-property-list/nsbluetoothalwaysusagedescription).

No application source, private configuration, CIMT execution code, saved report, or device state was changed. Only this investigation document was added.
