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
    public string ReportsRoot => Root.Get("reports")?.Get("root")?.PathValue ?? Path.Combine(InstallationRoot, "reports");
    public string WorkspaceRoot => Root.Get("workspace")?.Get("root")?.PathValue ?? Path.Combine(InstallationRoot, "work");
    public static string InstallationRoot => Environment.GetEnvironmentVariable("CIMT_INSTALL_ROOT") ?? "/Users/Shared/CIMT";

    public Configuration(Node root)
    {
        Root = root;
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
