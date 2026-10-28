using System.Text.Json;
using System.Text.RegularExpressions;

namespace Cimt.Build;

public sealed record BuildRequest(string Platform, string Repository, string ResultFile, string Project,
    string Configuration, string Framework, Dictionary<string, string> Properties, string ArtifactFallback, string AppIdFallback);

/// <summary>Reads and validates one build request from the caller's environment.</summary>
public sealed class BuildRequestLoader(Func<string, string?> environment)
{
    public string RequiredEnvironment(string name) => environment(name) is { Length: > 0 } value
        ? value : throw new InvalidOperationException(name + " is required.");

    public BuildRequest Load(string platform, string resultFile)
    {
        var root = Path.GetFullPath(RequiredEnvironment("CIMT_REPOSITORY_ROOT"));
        using var document = JsonDocument.Parse(File.ReadAllText(RequiredEnvironment("CIMT_BUILD_REQUEST")));
        var request = document.RootElement;
        var project = ResolveProject(Value(request, "project"), root);
        var configuration = Value(request, "configuration");
        var framework = Value(request, "framework");
        ValidateTarget(configuration, framework, platform);
        return new(platform, root, resultFile, project, configuration, framework, ReadProperties(request),
            Value(request, "artifact"), Value(request, "app-id"));
    }

    private static string ResolveProject(string value, string root)
    {
        if (Path.IsPathRooted(value) || value.Replace('\\', '/').Split('/').Contains(".."))
            throw new InvalidOperationException("Build project must be relative to the repository root.");
        var project = Path.GetFullPath(value.Replace('\\', Path.DirectorySeparatorChar), root);
        if (!File.Exists(project) || !project.EndsWith(".csproj", StringComparison.OrdinalIgnoreCase))
            throw new InvalidOperationException("Configured application project does not exist.");
        return project;
    }

    private static void ValidateTarget(string configuration, string framework, string platform)
    {
        if (string.IsNullOrWhiteSpace(configuration) || !framework.Contains("-" + platform, StringComparison.Ordinal))
            throw new InvalidOperationException("Build configuration and matching target framework are required.");
    }

    private static Dictionary<string, string> ReadProperties(JsonElement request)
    {
        var result = new Dictionary<string, string>();
        if (!request.TryGetProperty("properties", out var properties))
            return result;
        foreach (var property in properties.EnumerateObject())
        {
            if (!Regex.IsMatch(property.Name, "^[A-Za-z_][A-Za-z0-9_]*$"))
                throw new InvalidOperationException("Invalid MSBuild property name.");
            result[property.Name] = property.Value.ValueKind == JsonValueKind.String
                ? property.Value.GetString()! : property.Value.GetRawText();
        }
        return result;
    }

    private static string Value(JsonElement request, string name) =>
        request.TryGetProperty(name, out var value) ? value.GetString() ?? "" : "";
}
