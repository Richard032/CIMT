using System.Text.RegularExpressions;

namespace Cimt;

/// <summary>Stores validated metadata without doing any file operations.</summary>
public sealed record ResolvedBuildResult(string Artifact, string AppId);

/// <summary>Resolves each metadata field using the script first and YAML second.</summary>
public static class BuildResultResolver
{
    /// <summary>Choose each field, then reject unusable values before saving an artifact.</summary>
    public static ResolvedBuildResult Resolve(IReadOnlyDictionary<string, string> script,
        string repositoryRoot, string? artifactFallback, string? appIdFallback)
    {
        var artifact = ResolveArtifact(script, repositoryRoot, artifactFallback);
        var appId = script.TryGetValue("app-id", out var value) ? value : appIdFallback;
        if (string.IsNullOrWhiteSpace(appId) || !Regex.IsMatch(appId, "^[A-Za-z0-9_.-]+$"))
            throw new ConfigurationException("Build result has no valid app-id.");
        return new(artifact, appId);
    }

    private static string ResolveArtifact(IReadOnlyDictionary<string, string> script,
        string repositoryRoot, string? fallback)
    {
        if (script.TryGetValue("artifact", out var value))
        {
            // A returned value is authoritative; invalid values must not be hidden by YAML.
            if (string.IsNullOrWhiteSpace(value) || !Path.IsPathRooted(value))
                throw new ConfigurationException("A script artifact path must be absolute.");
            return FullPath(value, repositoryRoot);
        }
        if (string.IsNullOrWhiteSpace(fallback))
            throw new ConfigurationException("Build result has no artifact path.");
        return FullPath(fallback, repositoryRoot);
    }

    private static string FullPath(string path, string repositoryRoot)
    {
        try
        {
            return Path.GetFullPath(path, repositoryRoot);
        }
        catch (ArgumentException)
        {
            throw new ConfigurationException("Build artifact path is invalid.");
        }
    }
}
