using System.Text.Json;
using System.Text.RegularExpressions;

namespace Cimt;

public sealed record BuildJob(string Target, string Platform, string Folder, string RequestFile, string ResultFile, string Script)
{
    public string LogName => Path.GetFileName(Folder) + ".log";
}

/// <summary>Prepares one build-script request from a target's settings.</summary>
public sealed class BuildJobFactory(RuntimePaths paths)
{
    public async Task<BuildJob> Create(RunState state, Node target, string platform)
    {
        var settings = target.Get(platform)!;
        var name = target.Value("name")!;
        var slug = Regex.Replace(name, "[^A-Za-z0-9_.-]", "_") + "-" + platform + "-" + Guid.NewGuid().ToString("N")[..8];
        var folder = Path.Combine(state.Work, slug);
        Directory.CreateDirectory(folder);
        var job = new BuildJob(name, platform, folder, Path.Combine(folder, "request.json"),
            Path.Combine(folder, "result.json"), settings.Get("script")?.PathValue ?? paths.BuildScript(platform));
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
        var result = JsonSerializer.Deserialize<Dictionary<string, string>>(await File.ReadAllTextAsync(job.ResultFile))!;
        Validate(result);
        var destination = Path.Combine(state.Report, "artifacts", Path.GetFileName(job.Folder));
        Directory.CreateDirectory(destination);
        var saved = Path.Combine(destination, Path.GetFileName(result["artifact"]));
        File.Copy(result["artifact"], saved);
        return new()
        {
            ["target"] = job.Target,
            ["platform"] = job.Platform,
            ["artifact"] = saved,
            ["app-id"] = result["app-id"]
        };
    }

    private static void Validate(Dictionary<string, string> result)
    {
        if (!result.TryGetValue("artifact", out var artifact) || !File.Exists(artifact) ||
            !result.TryGetValue("app-id", out var appId) || !Regex.IsMatch(appId, "^[A-Za-z0-9_.-]+$"))
            throw new ConfigurationException("A successful build returned invalid artifact metadata.");
    }
}

/// <summary>Runs one build script and records its outcome.</summary>
public sealed class ApplicationBuilder(RunProcess processes, BuildArtifactStore artifacts, IRunProgress progress)
{
    public async Task Build(RunState state, BuildJob job)
    {
        SetBuildEnvironment(state, job);
        progress.Write(state, "Building " + job.Target + " for " + job.Platform);
        var result = await processes.Invoke(state, "bash", [job.Script], 1800);
        await SaveLog(state, job, result);
        if (result.Exit != 0 || !File.Exists(job.ResultFile))
        {
            RecordFailure(state, job, result.Exit);
            return;
        }
        state.Builds.Add(await artifacts.Save(state, job));
        RecordStage(state, job, "passed");
        // The saved artifact survives cleanup; publish intermediates do not.
        Directory.Delete(job.Folder, recursive: true);
    }

    private static void SetBuildEnvironment(RunState state, BuildJob job)
    {
        state.Environment["CIMT_REPOSITORY_ROOT"] = Path.Combine(state.Work, "repository");
        state.Environment["CIMT_BUILD_REQUEST"] = job.RequestFile;
        state.Environment["CIMT_BUILD_RESULT"] = job.ResultFile;
    }

    private static Task SaveLog(RunState state, BuildJob job, ProcessResult result)
    {
        return File.WriteAllTextAsync(Path.Combine(state.Report, job.LogName),
            state.Configuration.Scrub(result.Stdout + "\n" + result.Stderr));
    }

    private static void RecordFailure(RunState state, BuildJob job, int exit)
    {
        state.Errors.Add("Build failed: " + job.Target + " / " + job.Platform + " (exit " + exit + "). See " + job.LogName);
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
