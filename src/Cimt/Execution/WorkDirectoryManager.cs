using System.Text.Json;

namespace Cimt;

/// <summary>Creates and deletes only folders that belong to CIMT.</summary>
public sealed class WorkDirectoryManager(string registry)
{
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

    private void Register(RunFolders folders)
    {
        var path = folders.Work;
        var token = Guid.NewGuid().ToString("N");
        File.WriteAllText(Path.Combine(path, ".cimt-owned"), token);
        Directory.CreateDirectory(Path.GetDirectoryName(registry)!);
        File.WriteAllText(registry, JsonSerializer.Serialize(new
        {
            path,
            token,
            runId = folders.Identity.Id,
            report = folders.Report
        }));
    }

    /// <summary>Remove a previous interrupted run only when its ownership can be verified.</summary>
    public void CleanupPrevious(string? retainedReport = null)
    {
        if (!File.Exists(registry))
            return;
        using var record = JsonDocument.Parse(File.ReadAllText(registry));
        var path = record.RootElement.GetProperty("path").GetString()!;
        if (retainedReport is not null)
            RunFolderSafety.Outside(path, retainedReport);
        Remove(path);
    }

    /// <summary>Verify the recorded path and token before deleting any folder.</summary>
    public void Remove(string path)
    {
        using var record = ReadOwnership(path);
        if (Directory.Exists(path))
        {
            VerifyToken(path, record.RootElement.GetProperty("token").GetString());
            Directory.Delete(path, recursive: true);
        }
        File.Delete(registry);
    }

    private JsonDocument ReadOwnership(string path)
    {
        if (!File.Exists(registry))
            throw new IOException("Missing ownership registry");
        var record = JsonDocument.Parse(File.ReadAllText(registry));
        if (record.RootElement.GetProperty("path").GetString() == path &&
            Path.GetFileName(path).StartsWith("work_", StringComparison.Ordinal) &&
            new DirectoryInfo(path).LinkTarget is null)
            return record;
        record.Dispose();
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
public sealed class WorkPreparation(WorkDirectoryManager folders) : IRunStep
{
    public Task Execute(RunState state)
    {
        folders.CleanupPrevious(state.Report);
        state.Work = folders.Create(state.Folders);
        state.Environment["MOBILECLI_HOME"] = Path.Combine(state.Work, "mobilecli");
        return Task.CompletedTask;
    }
}

/// <summary>Stops this run's helper, then removes its disposable work.</summary>
public sealed class RunCleanup(ICommandRunner runner, RuntimePaths paths, WorkDirectoryManager folders) : IRunCleanup
{
    public async Task Execute(RunState state)
    {
        if (state.Work.Length == 0)
            return;
        try
        {
            await StopHelper(state);
        }
        catch (Exception error)
        {
            state.Errors.Add("The owned native daemon could not be stopped: " + error.GetType().Name);
            state.Exit = 3;
        }
        // Helper shutdown must not prevent deletion of an owned source clone.
        folders.Remove(state.Work);
    }

    private async Task StopHelper(RunState state)
    {
        var stopped = await runner.Run(new("node", ["-e",
            "const {Mobilecli}=require(process.argv[1]);console.log(new Mobilecli().executeCommand(['daemon','stop'],15000));",
            paths.NativeModule], 20, state.Environment));
        if (stopped.Exit == 0)
            return;
        state.Errors.Add("The owned native daemon could not be stopped cleanly.");
        state.Exit = 3;
    }
}
