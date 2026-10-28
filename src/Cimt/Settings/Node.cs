
namespace Cimt;

/// <summary>A configuration value with the file that declared it.</summary>
public sealed record Node(string? Scalar, Dictionary<string, Node>? Map, List<Node>? List, string Origin)
{
    public string Text => Scalar ?? throw new ConfigurationException("Expected a scalar configuration value.");
    public Node? Get(string key) => Map?.GetValueOrDefault(key);
    public string? Value(string key) => Get(key)?.Scalar;
    public string PathValue => Path.GetFullPath(Text, Path.GetDirectoryName(Origin)!);
    /// <summary>Convenience entry for callers that need to read a YAML file.</summary>
    public static Node Read(string file) => new YamlConfigurationReader().Read(file);

    /// <summary>Merge mappings, replace lists, and keep the original file for inherited values.</summary>
    public static Node Merge(Node a, Node b)
    {
        if (a.Map is null || b.Map is null)
            return b;
        var map = new Dictionary<string, Node>(a.Map, StringComparer.Ordinal);
        foreach (var (key, value) in b.Map)
            map[key] = map.TryGetValue(key, out var previous) ? Merge(previous, value) : value;
        return new(null, map, null, b.Origin);
    }
}

