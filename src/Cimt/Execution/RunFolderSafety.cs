namespace Cimt;

/// <summary>Prevents retained reports from being placed inside temporary cleanup folders.</summary>
public static class RunFolderSafety
{
    public static void Check(RunFolders folders)
    {
        Outside(folders.Work, folders.Report);
        var current = new DirectoryInfo(Physical(folders.Report)).Parent;
        while (current is not null)
        {
            if (File.Exists(Path.Combine(current.FullName, ".cimt-owned")))
                throw new ConfigurationException("Reports must remain outside CIMT-owned work folders.");
            current = current.Parent;
        }
    }

    public static void Outside(string work, string report)
    {
        var relative = Path.GetRelativePath(Physical(work), Physical(report));
        if (relative == "." || !Path.IsPathRooted(relative) && relative != ".."
            && !relative.StartsWith(".." + Path.DirectorySeparatorChar, StringComparison.Ordinal))
            throw new ConfigurationException("Reports must remain outside the temporary cleanup folder.");
    }

    private static string Physical(string path)
    {
        var full = Path.GetFullPath(path);
        var current = Path.GetPathRoot(full)!;
        foreach (var part in full[current.Length..].Split(Path.DirectorySeparatorChar, StringSplitOptions.RemoveEmptyEntries))
        {
            var next = new DirectoryInfo(Path.Combine(current, part));
            // Resolve existing aliases too, so a symlink cannot hide a nested report path.
            current = next.LinkTarget is null ? next.FullName : next.ResolveLinkTarget(true)!.FullName;
        }
        return current;
    }
}
