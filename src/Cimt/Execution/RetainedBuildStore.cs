using System.Security.Cryptography;
using System.Text.Json;

namespace Cimt;

public sealed record RetainedApp(string Target, string Platform, string Project, string Configuration,
    string Framework, string Artifact, string AppId, string Sha256, string DeviceKind = "physical");

public sealed record RetainedBuildSet(int Version, string SourceRunId, string Repository,
    string Branch, string Commit, List<RetainedApp> Apps);

/// <summary>Saves and verifies references to the last successfully built apps for one input folder.</summary>
public sealed class RetainedBuildStore
{
    private static readonly JsonSerializerOptions JsonOptions = new()
    {
        PropertyNamingPolicy = JsonNamingPolicy.CamelCase,
        PropertyNameCaseInsensitive = true,
        WriteIndented = true
    };

    public async Task Save(RunState state)
    {
        if (state.Builds.Count == 0)
            return;
        var apps = new List<RetainedApp>();
        foreach (var build in state.Builds)
            apps.Add(await Describe(state, build));
        var repository = state.Configuration.Root.Get("repository")!;
        var saved = new RetainedBuildSet(1, state.Identity.Id, repository.Value("url")!,
            repository.Value("branch")!, state.Commit, apps);
        var file = FilePath(state.Configuration);
        RunFolderSafety.Inside(state.Configuration.Outputs.Root, file);
        var temporary = file + "." + Guid.NewGuid().ToString("N") + ".partial";
        await using (var output = new FileStream(temporary, FileMode.CreateNew, FileAccess.Write, FileShare.None))
            await JsonSerializer.SerializeAsync(output, saved, JsonOptions);
        if (!OperatingSystem.IsWindows())
            File.SetUnixFileMode(temporary, UnixFileMode.UserRead | UnixFileMode.UserWrite);
        File.Move(temporary, file, overwrite: true);
    }

    public async Task Load(RunState state)
    {
        var saved = await Read(state.Configuration);
        var repository = state.Configuration.Root.Get("repository")!;
        if (saved.Repository != repository.Value("url") || saved.Branch != repository.Value("branch"))
            throw new ConfigurationException("The retained build belongs to another repository or branch. Run CIMT normally to build the selected branch.");
        foreach (var app in saved.Apps)
            await ReuseApp(state, saved.SourceRunId, app);
        if (state.Builds.Count == 0)
            throw new ConfigurationException("No retained app matches the configured build targets. Run CIMT normally to create a matching build.");
        state.Commit = saved.Commit;
        state.Stages.Add(new
        {
            stage = "retained app builds",
            result = "reused apps from run " + saved.SourceRunId + "; no repository clone or build",
            sourceRunId = saved.SourceRunId,
            sourceCommit = saved.Commit
        });
    }

    private static async Task<RetainedApp> Describe(RunState state, Dictionary<string, string> build)
    {
        var target = FindTarget(state.Configuration, build["target"])!;
        var settings = target.Get(build["platform"])!;
        RunFolderSafety.Inside(state.Report, build["artifact"]);
        return new(build["target"], build["platform"], target.Value("project")!, target.Value("configuration")!,
            settings.Value("framework")!, Path.GetRelativePath(state.Configuration.Outputs.Root, build["artifact"]),
            build["app-id"], await Digest(build["artifact"], state.Deadline), new DeviceSelection(state.Configuration.Root.Get("execution")).Kind);
    }

    private static async Task<RetainedBuildSet> Read(Configuration configuration)
    {
        var file = FilePath(configuration);
        RunFolderSafety.Inside(configuration.Outputs.Root, file);
        if (!File.Exists(file))
            throw new ConfigurationException("No retained app build is available in this input folder. Complete a CIMT build first; replay will not clone or build.");
        try
        {
            var saved = JsonSerializer.Deserialize<RetainedBuildSet>(await File.ReadAllTextAsync(file), JsonOptions);
            if (saved is not { Version: 1, Apps.Count: > 0 } || string.IsNullOrWhiteSpace(saved.SourceRunId)
                || string.IsNullOrWhiteSpace(saved.Commit))
                throw new ConfigurationException("Retained build metadata is incomplete or unsupported.");
            return saved;
        }
        catch (JsonException)
        {
            throw new ConfigurationException("Retained build metadata is invalid; no app was executed.");
        }
    }

    private static async Task ReuseApp(RunState state, string sourceRunId, RetainedApp app)
    {
        var target = FindTarget(state.Configuration, app.Target);
        if (target?.Get(app.Platform) is not { } settings)
            return;
        if (app.DeviceKind != new DeviceSelection(state.Configuration.Root.Get("execution")).Kind)
            throw new ConfigurationException("The retained app belongs to another device kind. Run CIMT normally before replay.");
        if (target.Value("project") != app.Project || target.Value("configuration") != app.Configuration
            || settings.Value("framework") != app.Framework)
            throw new ConfigurationException("A configured target differs from its retained build. Run CIMT normally to build the new configuration.");
        var sourceReport = Path.Combine(state.Configuration.ReportsRoot, "report_" + sourceRunId);
        RunFolderSafety.Inside(state.Configuration.ReportsRoot, sourceReport);
        var artifact = Path.GetFullPath(app.Artifact, state.Configuration.Outputs.Root);
        RunFolderSafety.Inside(Path.Combine(sourceReport, "artifacts"), artifact);
        if (!File.Exists(artifact))
            throw new ConfigurationException("A retained app artifact is missing. Replay will not rebuild it.");
        // Copy the already built app so the new report remains portable and independent.
        var copied = Path.Combine(state.Report, Path.GetRelativePath(sourceReport, artifact));
        RunFolderSafety.Inside(state.Report, copied);
        Directory.CreateDirectory(Path.GetDirectoryName(copied)!);
        await Copy(artifact, copied, state.Deadline);
        if (!string.Equals(await Digest(copied, state.Deadline), app.Sha256, StringComparison.OrdinalIgnoreCase))
            throw new ConfigurationException("A retained app artifact changed after its build. No app was executed.");
        state.Builds.Add(new()
        {
            ["target"] = app.Target,
            ["platform"] = app.Platform,
            ["artifact"] = copied,
            ["app-id"] = app.AppId
        });
    }

    private static Node? FindTarget(Configuration configuration, string name) =>
        configuration.Root.Get("build")!.Get("targets")!.List!.SingleOrDefault(target => target.Value("name") == name);

    private static string FilePath(Configuration configuration) =>
        Path.Combine(configuration.Outputs.Root, "retained-builds.json");

    private static async Task Copy(string source, string destination, RunDeadline deadline)
    {
        using var timeout = new CancellationTokenSource(TimeSpan.FromSeconds(deadline.RemainingSeconds(int.MaxValue)));
        await using var input = File.OpenRead(source);
        await using var output = new FileStream(destination, FileMode.CreateNew, FileAccess.Write, FileShare.None);
        try { await input.CopyToAsync(output, timeout.Token); }
        catch (OperationCanceledException)
        {
            throw new RunLimitException("Whole-run time limit reached while copying a retained app.");
        }
    }

    private static async Task<string> Digest(string file, RunDeadline deadline)
    {
        using var timeout = new CancellationTokenSource(TimeSpan.FromSeconds(deadline.RemainingSeconds(int.MaxValue)));
        await using var input = File.OpenRead(file);
        try { return Convert.ToHexString(await SHA256.HashDataAsync(input, timeout.Token)); }
        catch (OperationCanceledException)
        {
            throw new RunLimitException("Whole-run time limit reached while verifying a retained app.");
        }
    }
}

/// <summary>Publishes successful apps after the build stage, even when another target failed.</summary>
public sealed class SaveRetainedBuilds(RetainedBuildStore store) : IRunStep
{
    public Task Execute(RunState state) => store.Save(state);
}

/// <summary>Loads existing app builds before replay makes a model or device request.</summary>
public sealed class LoadRetainedBuilds(RetainedBuildStore store) : IRunStep
{
    public Task Execute(RunState state) => store.Load(state);
}
