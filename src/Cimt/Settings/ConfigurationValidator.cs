using System.Globalization;

namespace Cimt;

/// <summary>Checks configuration structure and values without accessing tools or files.</summary>
public sealed class ConfigurationValidator
{
    static void Keys(Node? n, params string[] allowed)
    {
        if (n is null)
            return;
        if (n.Map is null)
            throw new ConfigurationException("Expected a configuration mapping.");
        if (n.Map.Keys.Any(k => !allowed.Contains(k, StringComparer.Ordinal)))
            throw new ConfigurationException("Unknown configuration key in a mapping.");
    }
    static Node Required(Node n, string key) => n.Get(key) ?? throw new ConfigurationException("Missing required configuration field: " + key);
    static string Text(Node n, string key)
    {
        var s = Required(n, key).Text;
        if (string.IsNullOrWhiteSpace(s) || s.Contains('<') || s.Contains('>'))
            throw new ConfigurationException("A non-placeholder value is required for: " + key);
        return s;
    }
    static void Positive(Node n, string key)
    {
        if (!decimal.TryParse(Text(n, key), NumberStyles.Number, CultureInfo.InvariantCulture, out var value) || value <= 0)
            throw new ConfigurationException(key + " must be a positive number.");
    }
    static void Command(Node? n)
    {
        if (n is null)
            return;
        if (n.List is not { Count: > 0 } || n.List.Any(x => string.IsNullOrWhiteSpace(x.Scalar)))
            throw new ConfigurationException("Commands must be nonempty argument lists.");
    }
    /// <summary>Check each settings section; file access checks belong to a separate service.</summary>
    public void Validate(Node root)
    {
        Keys(root, "workspace", "reports", "repository", "build", "inputs", "credentials", "reset", "masking", "execution", "ai-model", "ai-budget");
        Keys(root.Get("workspace"), "root");
        ValidateReports(root.Get("reports"));
        ValidateRepository(Required(root, "repository"));
        ValidateExecution(Required(root, "execution"));
        ValidateModel(Required(root, "ai-model"));
        ValidateBudget(Required(root, "ai-budget"));
        ValidateInputs(Required(root, "inputs"));
        ValidateBuilds(Required(root, "build"));
        ValidateCredentials(root.Get("credentials"));
        ValidateReset(root.Get("reset"));
        ValidateMasking(root.Get("masking"));
    }

    private static void ValidateRepository(Node repository)
    {
        Keys(repository, "url", "branch", "solution");
        var url = Text(repository, "url");
        Text(repository, "branch");
        Configuration.RepoPath(Text(repository, "solution"));
        if (Uri.TryCreate(url, UriKind.Absolute, out var uri) && uri.Scheme is "https" or "ssh")
        {
            if (uri.Scheme == "https" && !string.IsNullOrEmpty(uri.UserInfo))
                throw new ConfigurationException("Repository URL must not contain credentials.");
            return;
        }
        if (!System.Text.RegularExpressions.Regex.IsMatch(url, @"^[\w.-]+@[\w.-]+:[^\s]+$"))
            throw new ConfigurationException("Repository URL must use HTTPS or SSH.");
    }

    private static void ValidateExecution(Node execution)
    {
        Keys(execution, "time-limit-minutes");
        Positive(execution, "time-limit-minutes");
    }

    private static void ValidateModel(Node model)
    {
        Keys(model, "name", "api-key");
        Text(model, "name");
        Text(model, "api-key");
    }

    private static void ValidateBudget(Node budget)
    {
        Keys(budget, "amount", "currency");
        Positive(budget, "amount");
        if (!System.Text.RegularExpressions.Regex.IsMatch(Text(budget, "currency"), "^[A-Z]{3}$"))
            throw new ConfigurationException("currency must be an uppercase three-letter code.");
    }

    private static void ValidateInputs(Node inputs)
    {
        Keys(inputs, "instructions", "requirements", "setup");
        Text(inputs, "instructions");
    }

    private static void ValidateBuilds(Node build)
    {
        Keys(build, "targets");
        if (Required(build, "targets").List is not { Count: > 0 } targets)
            throw new ConfigurationException("At least one build target is required.");
        var names = new HashSet<string>(StringComparer.Ordinal);
        foreach (var target in targets)
        {
            ValidateTarget(target);
            if (!names.Add(Text(target, "name")))
                throw new ConfigurationException("Build target names must be unique.");
        }
    }

    private static void ValidateTarget(Node target)
    {
        Keys(target, "name", "configuration", "project", "android", "ios");
        Text(target, "name");
        Text(target, "configuration");
        Configuration.RepoPath(Text(target, "project"));
        if (target.Get("android") is null && target.Get("ios") is null)
            throw new ConfigurationException("Each target requires Android or iOS settings.");
        foreach (var platform in new[] { "android", "ios" })
            if (target.Get(platform) is { } settings)
                ValidatePlatform(settings, platform);
    }

    private static void ValidatePlatform(Node settings, string platform)
    {
        Keys(settings, "framework", "properties", "script", "artifact", "app-id");
        if (!Text(settings, "framework").Contains("-" + platform, StringComparison.Ordinal))
            throw new ConfigurationException("Target framework does not match its platform.");
        if (settings.Get("properties") is { } properties &&
            (properties.Map is null || properties.Map.Values.Any(value => value.Scalar is null)))
            throw new ConfigurationException("Build properties must be scalar mappings.");
    }

    private static void ValidateCredentials(Node? credentials)
    {
        if (credentials is null)
            return;
        if (credentials.Map is null)
            throw new ConfigurationException("credentials must be a named mapping.");
        foreach (var credential in credentials.Map.Values)
        {
            Keys(credential, "username", "password");
            Text(credential, "username");
            Text(credential, "password");
        }
    }

    private static void ValidateReset(Node? reset)
    {
        Keys(reset, "command", "verify-command");
        Command(reset?.Get("command"));
        Command(reset?.Get("verify-command"));
    }

    private static void ValidateMasking(Node? masking)
    {
        Keys(masking, "rules");
        if (masking?.Get("rules") is not { } rules)
            return;
        if (rules.List is null)
            throw new ConfigurationException("masking.rules must be a list.");
        foreach (var rule in rules.List)
        {
            Keys(rule, "element-id");
            Text(rule, "element-id");
        }
    }

    private static void ValidateReports(Node? reports)
    {
        Keys(reports, "root", "sections");
        if (reports?.Get("sections") is not { } sections)
            return;
        var allowed = new[] { "requirements", "scenarios", "findings", "interpretations", "diagnostics" };
        if (sections.List is null || sections.List.Any(value => !allowed.Contains(value.Scalar)))
            throw new ConfigurationException("Invalid report detail section.");
    }
}
