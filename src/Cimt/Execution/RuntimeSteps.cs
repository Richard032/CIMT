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
public sealed class UiExecution(RunProcess processes, RuntimePaths paths, IRunProgress progress) : IRunStep
{
    public async Task Execute(RunState state)
    {
        if (state.Builds.Count == 0)
            throw new ConfigurationException("No installable build was produced; no application interactions were executed.");
        progress.Write(state, "Executing instructions on startup devices (maximum two at once)");
        var result = await processes.Invoke(state, paths.Python, [paths.Worker], int.MaxValue,
            JsonSerializer.Serialize(RuntimeRequest.Create(state)));
        state.UiExit = result.Exit is >= 0 and <= 3 ? result.Exit : 3;
        if (state.UiExit == 3)
            state.Errors.Add("Device/AI execution failed (exit " + result.Exit + "): " + state.Configuration.Scrub(result.Stderr));
        state.Exit = ExitCodes.Combine(state.Exit, state.UiExit);
    }
}
