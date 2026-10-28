namespace Cimt;

/// <summary>Builds the private request sent to Python through standard input.</summary>
public static class RuntimeRequest
{
    public static Dictionary<string, object?> Create(RunState state) => new()
    {
        ["config"] = ConvertNode(state.Configuration.Root),
        ["report"] = state.Report,
        ["work"] = state.Work,
        ["deadline"] = state.Deadline.End.ToUnixTimeMilliseconds() / 1000.0,
        ["nativeHome"] = state.Environment["MOBILECLI_HOME"],
        ["nativeBinary"] = state.NativeBinary,
        ["builds"] = state.Builds,
        ["devices"] = state.Devices,
        ["inputs"] = state.Inputs,
        ["requirements"] = state.Requirements,
        ["resetDirectories"] = ResetDirectories(state.Configuration.Root)
    };

    public static object? ConvertNode(Node node, string key = "")
    {
        if (node.Map is not null)
            return node.Map.ToDictionary(p => p.Key, p => ConvertNode(p.Value, p.Key));
        if (node.List is null)
            return node.Scalar;
        if (key is "command" or "verify-command")
            return node.List.Select((item, index) => ResolveCommandArgument(item, index)).ToArray();
        return node.List.Select(item => ConvertNode(item)).ToArray();
    }

    private static string ResolveCommandArgument(Node item, int index)
    {
        // Only the executable has a file origin. Other arguments stay literal.
        return index == 0 && item.Text.Contains('/') ? item.PathValue : item.Text;
    }

    private static Dictionary<string, string?> ResetDirectories(Node root)
    {
        return root.Get("reset")?.Map?.ToDictionary(p => p.Key,
            p => Path.GetDirectoryName(p.Value.List![0].Origin)) ?? [];
    }
}
