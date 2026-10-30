namespace Cimt;

/// <summary>Publishes the newest run or replay at one stable HTML path.</summary>
public sealed class LatestReportPublisher(string reportsRoot)
{
    public string EntryPath => Path.Combine(reportsRoot, "index.html");

    public bool Publish(RunFolders folders, string html)
    {
        try
        {
            Save(folders, html);
            return true;
        }
        catch (Exception error) when (error is IOException or UnauthorizedAccessException or ConfigurationException)
        {
            // Keep the dated report even when the shared entry cannot be replaced.
            Console.Error.WriteLine("Latest report could not be updated (" + error.GetType().Name
                + "). Use the saved timestamped report.");
            return false;
        }
    }

    private void Save(RunFolders folders, string html)
    {
        var name = "report_" + folders.Identity.Id;
        var expected = Path.Combine(Path.GetFullPath(reportsRoot), name);
        if (Path.GetFullPath(folders.Report) != expected)
            throw new ConfigurationException("Latest report must refer to a report in this input folder.");
        if (new FileInfo(EntryPath).LinkTarget is not null || new FileInfo(EntryPath + ".partial").LinkTarget is not null)
            throw new ConfigurationException("Latest report files must not be symbolic links.");
        RunFolderSafety.Inside(reportsRoot, folders.Report);
        RunFolderSafety.Inside(reportsRoot, EntryPath);
        RunFolderSafety.Inside(reportsRoot, EntryPath + ".partial");
        // Relative images, logs and JSON still belong to the dated report folder.
        var page = html.Replace("<meta charset=\"utf-8\">",
            "<meta charset=\"utf-8\"><base href=\"" + Uri.EscapeDataString(name) + "/\">", StringComparison.Ordinal);
        File.WriteAllText(EntryPath + ".partial", page);
        File.Move(EntryPath + ".partial", EntryPath, overwrite: true);
    }
}
