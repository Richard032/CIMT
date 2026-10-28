namespace Cimt;

public sealed record CommandOptions(string Command, Dictionary<string, string> Values)
{
    public bool IsHelp => Command == "help";
}

/// <summary>Checks command words and options without loading files.</summary>
public static class CommandLine
{
    public static CommandOptions Parse(string[] arguments)
    {
        if (arguments.Length == 0 || arguments[0] is "--help" or "help")
            return new("help", []);
        if (arguments[0] is not ("setup" or "validate" or "run" or "replay"))
            throw new ConfigurationException("Unknown CIMT command.");
        var values = ReadOptions(arguments);
        if (!values.ContainsKey("--config"))
            throw new ConfigurationException("--config is required.");
        return new(arguments[0], values);
    }

    private static Dictionary<string, string> ReadOptions(string[] arguments)
    {
        var values = new Dictionary<string, string>();
        for (var index = 1; index < arguments.Length; index += 2)
        {
            if (!IsValidOption(arguments, index) || !values.TryAdd(arguments[index], arguments[index + 1]))
                throw new ConfigurationException("Invalid, duplicate, or missing command option.");
        }
        return values;
    }

    private static bool IsValidOption(string[] arguments, int index) =>
        arguments[index] is "--config" or "--run-config" or "--branch" or "--scenario"
        && index + 1 < arguments.Length && !arguments[index + 1].StartsWith("--");
}

public interface IConfigurationLoader
{
    Configuration Load(CommandOptions options);
}

/// <summary>Loads defaults and applies overrides while keeping file origins.</summary>
public sealed class ConfigurationLoader(IConfigurationNodeReader? reader = null) : IConfigurationLoader
{
    public Configuration Load(CommandOptions options)
    {
        var nodes = reader ?? new YamlConfigurationReader();
        var root = nodes.Read(options.Values["--config"]);
        if (options.Command == "setup")
            throw new ConfigurationException("YAML-driven setup is not implemented yet; the documented prerequisite bootstrap helper is available.");
        if (options.Values.TryGetValue("--run-config", out var extra))
            root = Node.Merge(root, nodes.Read(extra));
        if (options.Values.TryGetValue("--branch", out var branch))
            root = Node.Merge(root, BranchOverride(options.Values["--config"], branch));
        var configuration = new Configuration(root);
        return configuration;
    }

    private static Node BranchOverride(string file, string branch)
    {
        var origin = Path.GetFullPath(file);
        var branchNode = new Node(branch, null, null, origin);
        var repository = new Node(null, new()
        {
            ["branch"] = branchNode
        }, null, origin);
        return new(null, new()
        {
            ["repository"] = repository
        }, null, origin);
    }
}
