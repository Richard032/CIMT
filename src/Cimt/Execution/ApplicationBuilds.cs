using System.Text.Json;
using System.Text.RegularExpressions;
using System.Diagnostics;

namespace Cimt;

public sealed record BuildJob(string Target, string Platform, string Folder, string RequestFile,
    string ResultFile, string Script, string RepositoryRoot, string? ArtifactFallback, string? AppIdFallback,
    string Configuration = "", string Framework = "")
{
    public string LogName => Path.GetFileName(Folder) + ".log";
}

/// <summary>Prepares one build-script request from a target's settings.</summary>
public sealed class BuildJobFactory(RuntimePaths paths)
{
    public async Task<BuildJob> Create(RunState state, Node target, string platform)
    {
        var settings = target.Get(platform)!;
        new DeviceSelection(state.Configuration.Root.Get("execution")).ValidateBuild(platform, settings);
        var name = target.Value("name")!;
        var slug = Regex.Replace(name, "[^A-Za-z0-9_.-]", "_") + "-" + platform + "-" + Guid.NewGuid().ToString("N")[..8];
        var folder = Path.Combine(state.Work, slug);
        Directory.CreateDirectory(folder);
        var job = new BuildJob(name, platform, folder, Path.Combine(folder, "request.json"),
            Path.Combine(folder, "result.json"), settings.Get("script")?.PathValue ?? paths.BuildScript(platform),
            Path.Combine(state.Work, "repository"), settings.Value("artifact"), settings.Value("app-id"),
            target.Value("configuration")!, settings.Value("framework")!);
        await WriteRequest(job.RequestFile, target, settings);
        return job;
    }

    private static async Task WriteRequest(string path, Node target, Node settings)
    {
        var request = new Dictionary<string, object?>
        {
            ["project"] = target.Value("project"),
            ["configuration"] = target.Value("configuration"),
            ["framework"] = settings.Value("framework"),
            ["properties"] = settings.Get("properties")?.Map?.ToDictionary(p => p.Key, p => p.Value.Text) ?? [],
            ["artifact"] = settings.Value("artifact"),
            ["app-id"] = settings.Value("app-id")
        };
        await File.WriteAllTextAsync(path, JsonSerializer.Serialize(request));
        if (!OperatingSystem.IsWindows())
            File.SetUnixFileMode(path, UnixFileMode.UserRead | UnixFileMode.UserWrite);
    }
}

/// <summary>Verifies and saves successful artifacts outside the disposable clone.</summary>
public sealed class BuildArtifactStore
{
    public async Task<Dictionary<string, string>> Save(RunState state, BuildJob job)
    {
        var script = await ReadScriptResult(job.ResultFile);
        var result = BuildResultResolver.Resolve(script, job.RepositoryRoot, job.ArtifactFallback, job.AppIdFallback);
        if (!File.Exists(result.Artifact))
            throw new ConfigurationException("The resolved build artifact does not exist.");
        var destination = Path.Combine(state.Report, "artifacts", Path.GetFileName(job.Folder));
        Directory.CreateDirectory(destination);
        var saved = Path.Combine(destination, Path.GetFileName(result.Artifact));
        File.Copy(result.Artifact, saved);
        return new()
        {
            ["target"] = job.Target,
            ["platform"] = job.Platform,
            ["artifact"] = saved,
            ["app-id"] = result.AppId
        };
    }

    private static async Task<Dictionary<string, string>> ReadScriptResult(string path)
    {
        if (!File.Exists(path))
            return [];
        try
        {
            return JsonSerializer.Deserialize<Dictionary<string, string>>(await File.ReadAllTextAsync(path))
                ?? throw new ConfigurationException("Build result must be a JSON object.");
        }
        catch (JsonException)
        {
            throw new ConfigurationException("Build result is not valid artifact/app-id JSON.");
        }
    }
}

/// <summary>Runs one build script and records its outcome.</summary>
public sealed class ApplicationBuilder(RunProcess processes, BuildArtifactStore artifacts, IRunProgress progress)
{
    public async Task Build(RunState state, BuildJob job)
    {
        SetBuildEnvironment(state, job);
        progress.Write(state, "Building " + job.Target + " for " + job.Platform
            + " (configuration: " + job.Configuration + "; framework: " + job.Framework + ")");
        state.Activity.Record("Build application", "started", "Configuration: " + job.Configuration
            + "; framework: " + job.Framework, job.Target, job.Platform, log: job.LogName);
        var started = Stopwatch.GetTimestamp();
        var result = await processes.Invoke(state, "bash", [job.Script], 1800);
        await SaveLog(state, job, result);
        state.Activity.Record("Build script returned", result.Exit == 0 ? "completed" : "failed",
            "Exit code: " + result.Exit, job.Target, job.Platform,
            seconds: Stopwatch.GetElapsedTime(started).TotalSeconds, log: job.LogName);
        if (result.Exit != 0)
        {
            RecordFailure(state, job, result.Exit);
            return;
        }
        if (!await SaveArtifact(state, job))
            return;
        RecordStage(state, job, "passed");
        state.Activity.Record("Installable app artifact saved", "completed", target: job.Target,
            platform: job.Platform, log: job.LogName);
        // Keep publish output and intermediates until the next clone for these inputs.
    }

    private static void SetBuildEnvironment(RunState state, BuildJob job)
    {
        state.Environment["CIMT_REPOSITORY_ROOT"] = job.RepositoryRoot;
        state.Environment["CIMT_BUILD_REQUEST"] = job.RequestFile;
        state.Environment["CIMT_BUILD_RESULT"] = job.ResultFile;
    }

    private static Task SaveLog(RunState state, BuildJob job, ProcessResult result)
    {
        return File.WriteAllTextAsync(Path.Combine(state.Report, job.LogName),
            state.Configuration.Scrub(result.Stdout + "\n" + result.Stderr));
    }

    private async Task<bool> SaveArtifact(RunState state, BuildJob job)
    {
        try
        {
            state.Builds.Add(await artifacts.Save(state, job));
            return true;
        }
        catch (ConfigurationException error)
        {
            // Invalid target metadata is a build failure; other targets can still run.
            RecordFailure(state, job, 0);
            state.Errors.Add(state.Configuration.Scrub(error.Message));
            state.Activity.Record("Resolve installable build artifact", "failed", error.Message,
                job.Target, job.Platform, log: job.LogName, error: error);
            return false;
        }
    }

    private static void RecordFailure(RunState state, BuildJob job, int exit)
    {
        var message = "Build failed: " + job.Target + " / " + job.Platform + " (exit " + exit + "). See " + job.LogName;
        state.Errors.Add(message);
        state.StopReasons.Add(new("Build failure", job.Target + " / " + job.Platform, message));
        RecordStage(state, job, "error");
        state.Exit = 3;
    }

    private static void RecordStage(RunState state, BuildJob job, string result)
    {
        state.Stages.Add(new
        {
            stage = "build",
            target = job.Target,
            platform = job.Platform,
            result,
            log = job.LogName
        });
    }
}

/// <summary>Schedules builds only for platforms present in the startup snapshot.</summary>
public sealed class ApplicationBuilds(BuildJobFactory jobs, ApplicationBuilder builder) : IRunStep
{
    public async Task Execute(RunState state)
    {
        foreach (var target in state.Configuration.Root.Get("build")!.Get("targets")!.List!)
            foreach (var platform in new[] { "android", "ios" })
                if (target.Get(platform) is not null && state.Devices.Any(device => device["platform"] == platform))
                    await builder.Build(state, await jobs.Create(state, target, platform));
    }
}
