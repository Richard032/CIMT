using System.Text.Json;
using System.Text.RegularExpressions;

namespace Cimt.Build;

/// <summary>Finds one installable artifact; ambiguous results require a fallback.</summary>
public static class BuildArtifacts
{
    public static string Resolve(BuildRequest request, string output)
    {
        var pattern = request.Platform == "android" ? "*.apk" : "*.ipa";
        var candidates = Directory.GetFiles(output, pattern, SearchOption.AllDirectories);
        if (request.Platform == "android")
            candidates = PreferSigned(candidates);
        if (candidates.Length == 1)
            return candidates[0];
        if (request.ArtifactFallback.Length > 0)
        {
            var fallback = Path.GetFullPath(request.ArtifactFallback, request.Repository);
            if (File.Exists(fallback))
                return fallback;
        }
        throw new InvalidOperationException("Publish did not produce one unambiguous installable artifact; configure artifact fallback or a replacement script.");
    }

    private static string[] PreferSigned(string[] candidates)
    {
        var signed = candidates.Where(path => path.EndsWith("-Signed.apk", StringComparison.OrdinalIgnoreCase)).ToArray();
        return signed.Length > 0 ? signed : candidates;
    }
}

/// <summary>Uses MSBuild's app identifier first, then the configured fallback.</summary>
public static class AppIdResolver
{
    public static string Resolve(BuildProcessResult query, string fallback)
    {
        var value = query.Exit == 0 ? query.Output.Trim() : "";
        if (!IsValid(value))
            value = fallback;
        if (!IsValid(value))
            throw new InvalidOperationException("Could not resolve app-id from MSBuild or configured fallback.");
        return value;
    }

    private static bool IsValid(string value) => Regex.IsMatch(value, "^[A-Za-z0-9_.-]+$");
}

/// <summary>Publishes result metadata only after a successful build.</summary>
public static class BuildResultWriter
{
    public static async Task Write(string file, string artifact, string appId)
    {
        var result = new Dictionary<string, string> { ["artifact"] = Path.GetFullPath(artifact), ["app-id"] = appId };
        await File.WriteAllTextAsync(file + ".partial", JsonSerializer.Serialize(result, new JsonSerializerOptions { WriteIndented = true }));
        File.Move(file + ".partial", file, overwrite: true);
    }
}
