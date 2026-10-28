using System.Text.RegularExpressions;

namespace Cimt;

/// <summary>Finds configured secrets and removes their values from text or snapshots.</summary>
public sealed class ConfigurationSecrets
{
    public HashSet<string> Values { get; } = new(StringComparer.Ordinal);

    public ConfigurationSecrets(Node root) => Collect(root, false);

    private void Collect(Node node, bool sensitive)
    {
        if (node.Scalar is { Length: > 0 } value && sensitive)
            Values.Add(value);
        if (node.Map is not null)
            foreach (var (key, child) in node.Map)
                Collect(child, sensitive || key == "credentials" || Regex.IsMatch(key, "pass|secret|token|key", RegexOptions.IgnoreCase));
        if (node.List is not null)
            foreach (var child in node.List)
                Collect(child, sensitive);
    }

    public string Scrub(string value)
    {
        // Longer values go first so a short secret cannot expose part of a longer one.
        foreach (var secret in Values.OrderByDescending(item => item.Length))
            value = value.Replace(secret, "<redacted>", StringComparison.Ordinal);
        return value;
    }

    public object? Sanitized(Node node)
    {
        if (node.Map is not null)
            return node.Map.ToDictionary(item => item.Key, item => Sanitized(item.Value));
        if (node.List is not null)
            return node.List.Select(Sanitized).ToArray();
        return Values.Contains(node.Scalar ?? "") ? "<redacted>" : node.Scalar;
    }
}

/// <summary>Checks file access rights only for files that contributed secret values.</summary>
public static class SecretFilePermissions
{
    public static void Validate(Node root, HashSet<string> secrets)
    {
        if (OperatingSystem.IsWindows())
            return;
        foreach (var file in FindFiles(root, secrets).Distinct())
        {
            var publicAccess = UnixFileMode.GroupRead | UnixFileMode.GroupWrite | UnixFileMode.GroupExecute
                | UnixFileMode.OtherRead | UnixFileMode.OtherWrite | UnixFileMode.OtherExecute;
            if ((File.GetUnixFileMode(file) & publicAccess) != 0)
                throw new ConfigurationException("Secret configuration requires owner-only file permissions: " + Path.GetFileName(file));
        }
    }

    private static IEnumerable<string> FindFiles(Node node, HashSet<string> secrets)
    {
        if (node.Scalar is { } value && secrets.Contains(value))
            yield return node.Origin;
        var children = node.Map?.Values.AsEnumerable() ?? node.List ?? Enumerable.Empty<Node>();
        foreach (var child in children)
            foreach (var file in FindFiles(child, secrets))
                yield return file;
    }
}
