namespace Cimt;

/// <summary>A local test file copied into the tested application's data container.</summary>
public sealed record ExternalFileSettings(string Source, string Platform, string Destination)
{
    public static IReadOnlyList<ExternalFileSettings> Read(Node root)
    {
        var setting = root.Get("external-files");
        if (setting is null)
            return [];
        if (setting.List is null)
            throw new ConfigurationException("external-files must be a list.");
        var files = new List<ExternalFileSettings>();
        var destinations = new HashSet<(string Platform, string Destination)>();
        foreach (var entry in setting.List)
        {
            if (entry.Map is null || entry.Map.Keys.Any(key => key is not ("source" or "platform" or "destination")))
                throw new ConfigurationException("Each external file must contain source, platform and destination only.");
            var source = Field(entry, "source");
            var platform = Field(entry, "platform");
            var destination = Field(entry, "destination").Replace('\\', '/');
            if (platform is not ("ios" or "android"))
                throw new ConfigurationException("External file platform must be ios or android.");
            RelativePath(source, true);
            RelativePath(destination, false);
            if (!destinations.Add((platform, platform == "ios" ? destination.ToUpperInvariant() : destination)))
                throw new ConfigurationException("External file destinations must be unique within each platform.");
            var local = Path.GetFullPath(source.Replace('\\', Path.DirectorySeparatorChar),
                Path.GetDirectoryName(entry.Get("source")!.Origin)!);
            files.Add(new(local, platform, destination));
        }
        return files;
    }

    public static void CheckSources(Node root)
    {
        foreach (var file in Read(root))
        {
            try
            {
                using var stream = File.OpenRead(file.Source);
            }
            catch (Exception error) when (error is IOException or UnauthorizedAccessException)
            {
                throw new ConfigurationException("External test file is not readable: " + Path.GetFileName(file.Source));
            }
        }
    }

    private static string Field(Node entry, string key)
    {
        var value = entry.Value(key);
        if (string.IsNullOrWhiteSpace(value) || value.Contains('<') || value.Contains('>'))
            throw new ConfigurationException("An external file requires a non-placeholder " + key + ".");
        return value;
    }

    private static void RelativePath(string path, bool source)
    {
        var normalized = path.Replace('\\', '/');
        var parts = normalized.Split('/');
        if (normalized.StartsWith('/') || normalized.Contains(':') || normalized.Any(char.IsControl)
            || parts.Any(part => part.Length == 0 || part == ".." || (!source && part == ".")))
            throw new ConfigurationException(source
                ? "External file sources must stay relative to their test configuration folder."
                : "External file destinations must stay relative to the app data container.");
    }
}
