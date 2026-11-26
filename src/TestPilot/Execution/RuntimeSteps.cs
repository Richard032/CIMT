using System.Text.Json;

namespace TestPilot;

/// <summary>Checks local runtime files without calling the AI provider.</summary>
public sealed class RuntimeFilesCheck(RuntimePaths paths) : IRunStep
{
    public Task Execute(RunState state)
    {
        if (!File.Exists(paths.Worker) || !File.Exists(paths.Python))
            throw new ConfigurationException("TestPilot support runtime is missing. Install it with scripts/install-testpilot-runtime.sh from the source installation.");
        if (ExternalFileSettings.Read(state.Configuration.Root).Count > 0
            && !File.Exists(Path.Combine(Path.GetDirectoryName(paths.Worker)!, "device_adapter", "external_files.py")))
            throw new ConfigurationException("External test files require the matching TestPilot support runtime. Reinstall it before running.");
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

/// <summary>Reviews the saved test inputs and any partial device results after cleanup.</summary>
public sealed class ProposalFinalization(ICommandRunner runner, RuntimePaths paths) : IRunStep
{
    public async Task Execute(RunState state)
    {
        if (ExecutionCheckpoint.IsEnabled(state) && !state.AiTestingApproved)
            throw new ConfigurationException("The interactive AI testing checkpoint was not acknowledged.");

        const int proposalRequestSeconds = 60;
        var timeout = (state.Configuration.Learning ? 2 : 1) * proposalRequestSeconds + 5;
        state.Activity.Record("Instruction proposal", "started", "Reviewing the test goals and recorded results.");
        // Device limits and cancellation have already been handled. Proposal requests get their own time.
        var result = await runner.Run(new(paths.Python, [paths.Worker, "--proposal"], timeout, state.Environment,
            Input: JsonSerializer.Serialize(new
            {
                protocolVersion = RuntimeResults.ProtocolVersion,
                config = RuntimeRequest.ConvertNode(state.Configuration.Root),
                learning = state.Configuration.Learning,
                builds = state.Builds,
                report = state.Report,
                deadline = DateTimeOffset.UtcNow.AddSeconds(timeout).ToUnixTimeMilliseconds() / 1000.0,
                proposalRequestSeconds,
                inputs = state.Inputs,
                outcome = new
                {
                    command = state.Command, exitCode = state.Exit, deviceExitCode = state.UiExit,
                    cancelled = state.Cancellation.IsCancellationRequested,
                    errors = state.Errors, stoppingReasons = state.StopReasons
                }
            })));
        if (result.Exit != 0)
            throw new ConfigurationException("The proposal worker exited before saving its review.");
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
            if (reports is not null)
                RunFinalization.Snapshot(state, reports);
        }
        var result = await worker;
        await SaveLog(state, result);
        state.UiExit = result.Exit is >= 0 and <= 3 ? result.Exit : 3;
        state.Exit = ExitCodes.Combine(state.Exit, state.UiExit);
        if (state.UiExit == 3)
            ReportFailure(state, result);
        state.Activity.Record("Device worker result", state.UiExit == 3 ? "failed" : "completed",
            "Worker exit code: " + result.Exit, log: "logs/execution-worker.log");
    }

    private static void ShowActivity(RunState state, string line)
    {
        // Only the worker's already-redacted activity messages are live terminal output.
        if (line.StartsWith("TestPilot activity: ", StringComparison.Ordinal))
            Console.WriteLine(line);
    }

    private static async Task SaveLog(RunState state, ProcessResult result)
    {
        var logs = Path.Combine(state.Report, "logs");
        Directory.CreateDirectory(logs);
        await File.WriteAllTextAsync(Path.Combine(logs, "execution-worker.log"),
            state.Configuration.Scrub(result.Stdout + "\n" + result.Stderr));
    }

    private static void ReportFailure(RunState state, ProcessResult result)
    {
        var execution = RuntimeResults.Read(state.Report);
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
