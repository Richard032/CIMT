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
        foreach (var step in steps)
            await step.Execute(state);
    }

    private static void RecordFailure(RunState state, Exception error)
    {
        var message = error is ConfigurationException
            ? state.Configuration.Scrub(error.Message)
            : "Execution infrastructure failed: " + error.GetType().Name;
        state.Errors.Add(message);
        state.Exit = 3;
    }

    private async Task Cleanup(RunState state)
    {
        try
        {
            await cleanup.Execute(state);
        }
        catch (Exception error)
        {
            state.Errors.Add("Owned helper finalization requires attention: " + error.GetType().Name);
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
