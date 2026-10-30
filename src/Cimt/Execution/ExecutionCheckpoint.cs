namespace Cimt;

public enum ExecutionPhase { OpenAiPreflight, RepositoryBuild, OpenAiTesting }

/// <summary>Waits for the user before the next execution stage.</summary>
public sealed class ExecutionCheckpoint(ExecutionPhase phase, TextReader input, TextWriter output,
    bool inputRedirected) : IRunStep
{
    public async Task Execute(RunState state)
    {
        if (!IsEnabled(state) || (phase == ExecutionPhase.OpenAiTesting && state.Builds.Count == 0))
            return;
        if (inputRedirected)
            throw new ConfigurationException("Interactive pauses need an interactive terminal. Set execution.interactive-pauses to false for Jenkins or redirected input.");

        using var timeout = new CancellationTokenSource(
            TimeSpan.FromSeconds(state.Deadline.RemainingSeconds(int.MaxValue)));
        using var cancellation = CancellationTokenSource.CreateLinkedTokenSource(timeout.Token, state.Cancellation);
        Record(state, "waiting");
        output.WriteLine(Message());
        output.WriteLine("Press Enter to continue. Waiting counts toward the run time limit.");
        await output.FlushAsync();
        try { await WaitForEnter(cancellation.Token); }
        catch (RunLimitException) when (state.Cancellation.IsCancellationRequested)
        {
            state.Cancellation.ThrowIfCancellationRequested();
            throw;
        }
        // A late acknowledgement must not start the next stage after the deadline.
        state.Deadline.RemainingSeconds(int.MaxValue);
        Record(state, "continued");
    }

    private static bool IsEnabled(RunState state) =>
        bool.TryParse(state.Configuration.Root.Get("execution")?.Value("interactive-pauses"), out var enabled)
        && enabled;

    private string Message() => phase switch
    {
        ExecutionPhase.OpenAiPreflight => "CIMT is about to check OpenAI model access using the configured API key. No inference is requested in this check.",
        ExecutionPhase.RepositoryBuild => "CIMT is about to access the repository and build the application. This includes Git, submodules, and package restore.",
        ExecutionPhase.OpenAiTesting => "CIMT is about to use OpenAI to test the application. The configured API key will be used, and AI requests may incur charges.",
        _ => throw new InvalidOperationException("Unknown execution checkpoint.")
    };

    private async Task WaitForEnter(CancellationToken cancellation)
    {
        try
        {
            // WaitAsync also bounds readers whose underlying stream cannot cancel a pending read.
            if (await input.ReadLineAsync(cancellation).AsTask().WaitAsync(cancellation) is null)
                throw new ConfigurationException("Terminal input closed at an execution checkpoint; execution stopped.");
        }
        catch (OperationCanceledException)
        {
            throw new RunLimitException("Whole-run time limit reached while waiting for user input.");
        }
    }

    private void Record(RunState state, string result)
    {
        state.Stages.Add(new { stage = "execution checkpoint: " + phase, result });
        state.Activity.Record("Execution checkpoint: " + phase, result);
    }
}
