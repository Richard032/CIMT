namespace Cimt.Build;

/// <summary>Builds argument lists. Values are never joined into a shell command.</summary>
public static class BuildCommands
{
    public static string[] Publish(BuildRequest request, string output) =>
        new[] { request.IsIosSimulator ? "build" : "publish", request.Project, "-c", request.Configuration, "-f", request.Framework, "--output", output }
            .Concat(PropertyArguments(request)).ToArray();

    public static string[] Metadata(BuildRequest request) =>
        new[] { "msbuild", request.Project, "-p:Configuration=" + request.Configuration,
            "-p:TargetFramework=" + request.Framework, "-getProperty:ApplicationId" }
            .Concat(PropertyArguments(request)).ToArray();

    private static IEnumerable<string> PropertyArguments(BuildRequest request) =>
        // Missing values belong to the selected project and SDK, not to CIMT defaults.
        request.Properties.Select(property => "-p:" + property.Key + "=" + property.Value);
}
