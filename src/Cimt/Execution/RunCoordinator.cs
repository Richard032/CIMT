namespace Cimt;

/// <summary>One ordered part of the run. Tests can supply a small fake step.</summary>
public interface IRunStep
{
    Task Execute(RunState state);
}

public interface IRunCleanup
{
    Task Execute(RunState state);
}

public interface IRunReportWriter
{
    int Write(RunState state);
    void Snapshot(RunState state) { }
}

/// <summary>Runs the steps in order and always performs cleanup and reporting.</summary>
public sealed class RunCoordinator(IEnumerable<IRunStep> steps, IRunCleanup cleanup, IRunReportWriter reports)
{
    /// <summary>Run each step, then clean up and write the result even after a failure.</summary>
    public async Task<int> Execute(RunState state)
    {
        try
        {
            await ExecuteSteps(state);
        }
        catch (RunLimitException error)
        {
            state.Errors.Add(error.Message);
            state.StopReasons.Add(new("Run limit", "Run", state.Configuration.Scrub(error.Message)));
            state.Exit = ExitCodes.Combine(state.Exit, 2);
        }
        catch (Exception) when (state.Cancellation.IsCancellationRequested)
        {
            const string message = "User interrupted execution; partial observations and remaining work were retained.";
            state.StopReasons.Add(new("User interruption", "Run", message));
            state.Exit = ExitCodes.Combine(state.Exit, 2);
        }
        catch (Exception error)
        {
            RecordFailure(state, error);
        }
        finally
        {
            await Cleanup(state);
        }
        if (state.Exit == 0 && state.UiExit == 2)
            state.Exit = 2;
        return reports.Write(state);
    }

    private async Task ExecuteSteps(RunState state)
    {
        reports.Snapshot(state);
        state.Cancellation.ThrowIfCancellationRequested();
        foreach (var step in steps)
        {
            state.Cancellation.ThrowIfCancellationRequested();
            await state.Activity.Run(StepName(step), () => step.Execute(state), state.Cancellation);
            reports.Snapshot(state);
        }
    }

    private static string StepName(IRunStep step) => step switch
    {
        TextInputLoader => "Load testing inputs",
        RuntimeFilesCheck => "Check installed runtime",
        WorkPreparation => "Prepare working folder",
        ExecutionCheckpoint => "Execution checkpoint",
        ModelAccessCheck => "Check OpenAI model access",
        DeviceDiscovery => "Discover connected devices",
        RepositoryCheckout => "Clone repository and initialize submodules",
        ApplicationBuilds => "Build configured applications",
        SaveRetainedBuilds => "Save retained app metadata",
        LoadRetainedBuilds => "Load retained apps for replay",
        UiExecution => "Execute device tests",
        _ => step.GetType().Name
    };

    private static void RecordFailure(RunState state, Exception error)
    {
        var message = error is ConfigurationException
            ? state.Configuration.Scrub(error.Message)
            : "Execution infrastructure failed: " + error.GetType().Name;
        state.Errors.Add(message);
        state.StopReasons.Add(new("Infrastructure failure", "Run", message));
        state.Exit = 3;
    }

    private async Task Cleanup(RunState state)
    {
        try
        {
            await state.Activity.Run("Finalize owned helper and logs", () => cleanup.Execute(state));
        }
        catch (Exception error)
        {
            state.Errors.Add("Owned helper finalization requires attention: " + error.GetType().Name);
            state.StopReasons.Add(new("Infrastructure failure", "Helper finalization", error.GetType().Name));
            state.Exit = 3;
        }
    }
}

/// <summary>Keeps a more serious failure when several outcomes occur.</summary>
public static class ExitCodes
{
    public static int Combine(int first, int next)
    {
        if (first == 3 || next == 3)
            return 3;
        if (first == 1 || next == 1)
            return 1;
        if (first == 2 || next == 2)
            return 2;
        return 0;
    }
}
