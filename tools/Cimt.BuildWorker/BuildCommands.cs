namespace Cimt.Build;

/// <summary>Builds argument lists. Values are never joined into a shell command.</summary>
public static class BuildCommands
{
    public static string[] Publish(BuildRequest request, string output) =>
        new[] { "publish", request.Project, "-c", request.Configuration, "-f", request.Framework, "--output", output }
            .Concat(PropertyArguments(request)).ToArray();

    public static string[] Metadata(BuildRequest request) =>
        new[] { "msbuild", request.Project, "-p:Configuration=" + request.Configuration,
            "-p:TargetFramework=" + request.Framework, "-getProperty:ApplicationId" }
            .Concat(PropertyArguments(request)).ToArray();

    private static IEnumerable<string> PropertyArguments(BuildRequest request) =>
        EffectiveProperties(request).Select(property => "-p:" + property.Key + "=" + property.Value);

    public static Dictionary<string, string> EffectiveProperties(BuildRequest request)
    {
        var properties = new Dictionary<string, string>(request.Properties);
        if (request.Platform == "android")
            properties["AndroidPackageFormats"] = "apk";
        else
        {
            properties["RuntimeIdentifier"] = "ios-arm64";
            properties["BuildIpa"] = "true";
            properties["ArchiveOnBuild"] = "true";
        }
        return properties;
    }
}
