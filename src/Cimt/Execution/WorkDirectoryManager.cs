using System.Text.Json;

namespace Cimt;

/// <summary>Creates and deletes only folders that belong to CIMT.</summary>
public sealed class WorkDirectoryManager(string registry)
{
    private readonly NativeHomeLink nativeLink = new(registry);

    public string PrepareNativeHome(string work)
    {
        var ownership = ReadOwnership(work);
        VerifyToken(work, ownership.Token);
        var target = Path.Combine(work, "mobilecli");
        Directory.CreateDirectory(target);
        return nativeLink.Create(target);
    }

    /// <summary>Create a private work folder and record proof that CIMT owns it.</summary>
    public string Create(RunFolders folders)
    {
        RunFolderSafety.Check(folders);
        var path = folders.Work;
        if (Directory.Exists(path) || File.Exists(path) || new DirectoryInfo(path).LinkTarget is not null)
            throw new ConfigurationException("The allocated work folder is already occupied; it will not be reused.");
        Directory.CreateDirectory(path);
        if (!OperatingSystem.IsWindows())
            File.SetUnixFileMode(path, UnixFileMode.UserRead | UnixFileMode.UserWrite | UnixFileMode.UserExecute);
        Register(folders);
        return path;
    }

    private static readonly JsonSerializerOptions JsonOptions = new()
    {
        PropertyNamingPolicy = JsonNamingPolicy.CamelCase,
        PropertyNameCaseInsensitive = true
    };

    private sealed record OwnedWork(string Path, string Token, string? RunId = null, string? Report = null);

    private void Register(RunFolders folders)
    {
        var token = Guid.NewGuid().ToString("N");
        File.WriteAllText(Path.Combine(folders.Work, ".cimt-owned"), token);
        var records = ReadRecords();
        records.Add(new(folders.Work, token, folders.Identity.Id, folders.Report));
        SaveRecords(records);
    }

    private List<OwnedWork> ReadRecords()
    {
        if (!File.Exists(registry))
            return [];
        using var document = JsonDocument.Parse(File.ReadAllText(registry));
        // Older installations stored one object. Keep its ownership proof during migration.
        return document.RootElement.ValueKind == JsonValueKind.Array
            ? document.RootElement.Deserialize<List<OwnedWork>>(JsonOptions)!
            : [document.RootElement.Deserialize<OwnedWork>(JsonOptions)!];
    }

    private void SaveRecords(List<OwnedWork> records)
    {
        if (records.Count == 0)
        {
            File.Delete(registry);
            return;
        }
        Directory.CreateDirectory(Path.GetDirectoryName(registry)!);
        File.WriteAllText(registry, JsonSerializer.Serialize(records, JsonOptions));
        if (!OperatingSystem.IsWindows())
            File.SetUnixFileMode(registry, UnixFileMode.UserRead | UnixFileMode.UserWrite);
    }

    /// <summary>Delete earlier owned work for these inputs only, immediately before a new clone.</summary>
    public void CleanupPrevious(string? retainedReport = null, string? currentWork = null)
    {
        foreach (var record in ReadRecords())
        {
            if (currentWork is not null && (record.Path == currentWork
                || Path.GetDirectoryName(record.Path) != Path.GetDirectoryName(currentWork)))
                continue;
            if (retainedReport is not null)
                RunFolderSafety.Outside(record.Path, retainedReport);
            if (record.Report is not null)
                RunFolderSafety.Outside(record.Path, record.Report);
            Remove(record.Path);
        }
    }

    /// <summary>Find the verified work folder behind an existing helper link, without deleting work.</summary>
    public string? LinkedWork()
    {
        var link = new DirectoryInfo(nativeLink.LinkPath);
        if (link.LinkTarget is null)
        {
            if (link.Exists || File.Exists(nativeLink.LinkPath))
                throw new IOException("The native helper address is occupied by an unrelated item.");
            return null;
        }
        var target = Path.GetFullPath(link.LinkTarget, "/tmp");
        var record = ReadRecords().SingleOrDefault(item => Path.Combine(item.Path, "mobilecli") == target)
            ?? throw new IOException("The native helper link has no verified owner.");
        if (Directory.Exists(record.Path))
            VerifyToken(record.Path, record.Token);
        return record.Path;
    }

    public string NativeHomeAddress => nativeLink.LinkPath;

    public void Verify(string work)
    {
        var record = ReadOwnership(work);
        VerifyToken(work, record.Token);
    }

    /// <summary>Release only the short helper link. Keep the work folder and ownership record.</summary>
    public void ReleaseNativeHome(string work)
    {
        var record = ReadOwnership(work);
        if (Directory.Exists(work))
            VerifyToken(work, record.Token);
        nativeLink.Remove(Path.Combine(work, "mobilecli"));
    }

    /// <summary>Verify the recorded path and token before deleting an owned folder.</summary>
    public void Remove(string path)
    {
        var record = ReadOwnership(path);
        if (Directory.Exists(path))
            VerifyToken(path, record.Token);
        var link = new DirectoryInfo(nativeLink.LinkPath);
        if (link.LinkTarget is not null && Path.GetFullPath(link.LinkTarget, "/tmp") == Path.Combine(path, "mobilecli"))
            nativeLink.Remove(Path.Combine(path, "mobilecli"));
        if (Directory.Exists(path))
            Directory.Delete(path, recursive: true);
        SaveRecords(ReadRecords().Where(item => item.Path != path).ToList());
    }

    private OwnedWork ReadOwnership(string path)
    {
        var record = ReadRecords().SingleOrDefault(item => item.Path == path);
        if (record is not null && Path.GetFileName(path).StartsWith("work_", StringComparison.Ordinal)
            && new DirectoryInfo(path).LinkTarget is null)
            return record;
        throw new IOException("Unverified work ownership");
    }

    private static void VerifyToken(string path, string? expected)
    {
        // The registry and folder must agree before any recursive deletion.
        if (File.ReadAllText(Path.Combine(path, ".cimt-owned")) != expected)
            throw new IOException("Work ownership token mismatch");
    }
}

/// <summary>Prepares the private work folder before other run steps use it.</summary>
public sealed class WorkPreparation(WorkDirectoryManager folders, ICommandRunner runner, RuntimePaths paths) : IRunStep
{
    public async Task Execute(RunState state)
    {
        var previous = folders.LinkedWork();
        if (previous is not null)
        {
            var environment = new Dictionary<string, string>(state.Environment)
            {
                ["MOBILECLI_HOME"] = folders.NativeHomeAddress
            };
            var stopped = await NativeHelperStop.Execute(runner, paths, environment);
            if (stopped.Exit != 0)
                throw new ConfigurationException("The previous owned helper could not be stopped; retained work was preserved.");
            folders.ReleaseNativeHome(previous);
            state.Stages.Add(new { stage = "previous helper recovery", result = "stopped; previous work preserved" });
        }
        state.Work = folders.Create(state.Folders);
        state.Environment["MOBILECLI_HOME"] = folders.PrepareNativeHome(state.Work);
    }
}

/// <summary>Stops the owned helper and keeps work files for inspection and replay.</summary>
public sealed class RunCleanup(ICommandRunner runner, RuntimePaths paths, WorkDirectoryManager folders) : IRunCleanup
{
    public async Task Execute(RunState state)
    {
        if (state.Work.Length == 0)
            return;
        folders.Verify(state.Work);
        var stopped = false;
        try
        {
            stopped = await StopHelper(state);
        }
        catch (Exception error)
        {
            state.Errors.Add("The owned native daemon could not be stopped: " + error.GetType().Name);
            state.Exit = 3;
        }
        await PreserveHelperLog(state);
        if (stopped)
            folders.ReleaseNativeHome(state.Work);
    }

    private async Task<bool> StopHelper(RunState state)
    {
        // Startup may fail before any owned helper address has been selected.
        if (!state.Environment.ContainsKey("MOBILECLI_HOME"))
            return false;
        var stopped = await NativeHelperStop.Execute(runner, paths, state.Environment);
        if (stopped.Exit == 0)
            return true;
        state.Errors.Add("The owned native daemon could not be stopped cleanly: "
            + state.Configuration.Scrub(stopped.Stderr.Trim()));
        state.Exit = 3;
        return false;
    }

    private static async Task PreserveHelperLog(RunState state)
    {
        var source = Path.Combine(state.Work, "mobilecli", "daemon.log");
        if (!File.Exists(source))
            return;
        try
        {
            var text = state.Configuration.Scrub(await File.ReadAllTextAsync(source));
            await File.WriteAllTextAsync(source, text);
            var logs = Path.Combine(state.Report, "logs");
            Directory.CreateDirectory(logs);
            await File.WriteAllTextAsync(Path.Combine(logs, "native-daemon.log"), text);
        }
        catch (Exception error)
        {
            state.Errors.Add("Native helper log could not be retained: " + error.GetType().Name);
            state.Exit = 3;
        }
    }
}
