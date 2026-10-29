namespace Cimt;

public sealed class ConfigurationException(string message) : Exception(message);

/// <summary>Provides the merged settings and their redacted view.</summary>
public sealed class Configuration
{
    private readonly ConfigurationSecrets redactor;
    public Node Root
    {
        get;
    }
    public HashSet<string> Secrets => redactor.Values;
    public OutputLayout Outputs { get; }
    public string ReportsRoot => Outputs.ReportsRoot;
    public string WorkspaceRoot => Outputs.WorkRoot;
    public bool HasLegacyOutputRoots => Root.Get("workspace")?.Get("root") is not null
        || Root.Get("reports")?.Get("root") is not null;
    public static string InstallationRoot => Environment.GetEnvironmentVariable("CIMT_INSTALL_ROOT") ?? "/Users/Shared/CIMT";

    public Configuration(Node root, OutputLayout? outputs = null)
    {
        Root = root;
        Outputs = outputs ?? OutputLayout.ForFile(root.Origin);
        redactor = new ConfigurationSecrets(root);
    }

    public string Scrub(string value) => redactor.Scrub(value);
    public object? Sanitized(Node node) => redactor.Sanitized(node);

    public void Validate()
    {
        new ConfigurationValidator().Validate(Root);
        SecretFilePermissions.Validate(Root, Secrets);
    }

    public static void RepoPath(string path)
    {
        if (Path.IsPathRooted(path) || path.Replace('\\', '/').Split('/').Contains(".."))
            throw new ConfigurationException("Repository paths must remain relative to the clone root.");
    }
}
