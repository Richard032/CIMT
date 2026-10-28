using System.Text.Json;

namespace Cimt;

/// <summary>Selects a free shared timestamp and creates only its retained report folder.</summary>
public sealed class RunFolderAllocator
{
    public RunFolders Create(string workRoot, string reportRoot, DateTimeOffset started)
    {
        var identity = RunIdentity.At(started);
        while (true)
        {
            var folders = RunFolders.Under(workRoot, reportRoot, identity);
            RunFolderSafety.Check(folders);
            Directory.CreateDirectory(Path.GetDirectoryName(folders.Report)!);
            using var reservation = TryReserve(folders.Report + ".reserve");
            if (reservation is not null)
            {
                if (!Occupied(folders.Work) && !Occupied(folders.Report))
                    return CreateReport(folders);
            }
            identity = identity.Next();
        }
    }

    private static FileStream? TryReserve(string path)
    {
        try
        {
            // Competing error reports may run without the Mac lock. Reserve atomically.
            return new FileStream(path, FileMode.CreateNew, FileAccess.Write, FileShare.None,
                1, FileOptions.DeleteOnClose);
        }
        catch (IOException) when (Occupied(path))
        {
            return null;
        }
    }

    private static bool Occupied(string path) => File.Exists(path) || Directory.Exists(path)
        || new FileInfo(path).LinkTarget is not null;

    private static RunFolders CreateReport(RunFolders folders)
    {
        Directory.CreateDirectory(folders.Report);
        if (!OperatingSystem.IsWindows())
            File.SetUnixFileMode(folders.Report, UnixFileMode.UserRead | UnixFileMode.UserWrite | UnixFileMode.UserExecute);
        var value = new
        {
            runIdentity = folders.Identity,
            workFolder = Path.GetFileName(folders.Work),
            reportFolder = Path.GetFileName(folders.Report)
        };
        File.WriteAllText(Path.Combine(folders.Report, "run-identity.json"), JsonSerializer.Serialize(value,
            new JsonSerializerOptions { WriteIndented = true, PropertyNamingPolicy = JsonNamingPolicy.CamelCase }));
        return folders;
    }
}
