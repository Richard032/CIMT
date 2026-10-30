using System.Text.Json;

namespace Cimt;

/// <summary>Checks local runtime files without calling the AI provider.</summary>
public sealed class RuntimeFilesCheck(RuntimePaths paths) : IRunStep
{
    public Task Execute(RunState state)
    {
        if (!File.Exists(paths.Worker) || !File.Exists(paths.Python))
            throw new ConfigurationException("CIMT support runtime is missing. Install it with scripts/install-cimt-runtime.sh from the source installation.");
        return Task.CompletedTask;
    }
}

/// <summary>Checks model access. This step does not request inference.</summary>
public sealed class ModelAccessCheck(RunProcess processes, RuntimePaths paths, IRunProgress progress) : IRunStep
{
    public async Task Execute(RunState state)
    {
        progress.Write(state, "Checking model access and the installed execution runtime");
        var result = await processes.Invoke(state, paths.Python, [paths.Worker, "--preflight"], 45,
            JsonSerializer.Serialize(RuntimeRequest.Create(state)));
        if (result.Exit != 0)
            throw new ConfigurationException(state.Configuration.Scrub(result.Stderr.Trim()));
        state.Stages.Add(new
        {
            stage = "model/runtime preflight",
            result = "passed; no inference issued"
        });
    }
}

/// <summary>Runs the device worker after successful builds are available.</summary>
public sealed class UiExecution(RunProcess processes, RuntimePaths paths, IRunProgress progress,
    IRunReportWriter? reports = null) : IRunStep
{
    public async Task Execute(RunState state)
    {
        if (state.Builds.Count == 0)
            throw new ConfigurationException("No installable build was produced; no application interactions were executed.");
        progress.Write(state, "Executing instructions on startup devices (maximum two at once)");
        var worker = processes.Invoke(state, paths.Python, [paths.Worker], int.MaxValue,
            JsonSerializer.Serialize(RuntimeRequest.Create(state)), output: line => ShowActivity(state, line),
            stopGraceSeconds: 5);
        while (!worker.IsCompleted)
        {
            await Task.WhenAny(worker, Task.Delay(TimeSpan.FromSeconds(2)));
            reports?.Snapshot(state);
        }
        var result = await worker;
        await SaveLog(state, result);
        state.UiExit = result.Exit is >= 0 and <= 3 ? result.Exit : 3;
        if (state.UiExit == 3)
            await ReportFailure(state, result);
        state.Activity.Record("Device worker result", state.UiExit == 3 ? "failed" : "completed",
            "Worker exit code: " + result.Exit, log: "logs/execution-worker.log");
        state.Exit = ExitCodes.Combine(state.Exit, state.UiExit);
    }

    private static void ShowActivity(RunState state, string line)
    {
        // Only the worker's already-redacted activity messages are live terminal output.
        if (line.StartsWith("CIMT activity: ", StringComparison.Ordinal))
            Console.WriteLine(line);
    }

    private static async Task SaveLog(RunState state, ProcessResult result)
    {
        var logs = Path.Combine(state.Report, "logs");
        Directory.CreateDirectory(logs);
        await File.WriteAllTextAsync(Path.Combine(logs, "execution-worker.log"),
            state.Configuration.Scrub(result.Stdout + "\n" + result.Stderr));
    }

    private static async Task ReportFailure(RunState state, ProcessResult result)
    {
        var file = Path.Combine(state.Report, "ui-results.json");
        JsonElement? execution = File.Exists(file)
            ? JsonSerializer.Deserialize<JsonElement>(await File.ReadAllTextAsync(file)) : null;
        var messages = RunDiagnostics.WorkerReasons(execution)
            .Where(reason => reason.Category == "Infrastructure failure")
            .Select(reason => reason.Description).ToArray();
        if (messages.Length == 0)
            messages = ["Device/AI execution failed (exit " + result.Exit + "). "
                + (string.IsNullOrWhiteSpace(result.Stderr) ? "No worker error detail was returned; see logs/execution-worker.log."
                    : result.Stderr.Trim())];
        foreach (var message in messages)
        {
            var safe = state.Configuration.Scrub(message);
            state.Errors.Add(safe);
            Console.WriteLine(safe);
        }
    }
}
