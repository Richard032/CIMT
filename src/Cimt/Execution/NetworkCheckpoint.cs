namespace Cimt;

public enum NetworkPhase { OpenAiPreflight, RepositoryBuild, OpenAiTesting }

/// <summary>Waits for a manual network change before the next network-dependent stage.</summary>
public sealed class NetworkCheckpoint(NetworkPhase phase, TextReader input, TextWriter output,
    bool inputRedirected) : IRunStep
{
    public async Task Execute(RunState state)
    {
        if (!IsEnabled(state) || (phase == NetworkPhase.OpenAiTesting && state.Builds.Count == 0))
            return;
        if (inputRedirected)
            throw new ConfigurationException("Network switching needs an interactive terminal. Set execution.network-switch-pauses to false for Jenkins or redirected input.");

        using var timeout = new CancellationTokenSource(
            TimeSpan.FromSeconds(state.Deadline.RemainingSeconds(int.MaxValue)));
        Record(state, "waiting");
        output.WriteLine(Message());
        output.WriteLine("Switch networks, then press Enter to continue. Waiting counts toward the run time limit.");
        await output.FlushAsync();
        await WaitForEnter(timeout.Token);
        // A late acknowledgement must not allow a network request after the deadline.
        state.Deadline.RemainingSeconds(int.MaxValue);
        Record(state, "continued");
    }

    private static bool IsEnabled(RunState state) =>
        bool.TryParse(state.Configuration.Root.Get("execution")?.Value("network-switch-pauses"), out var enabled)
        && enabled;

    private string Message() => phase switch
    {
        NetworkPhase.OpenAiPreflight => "PAUSED before OpenAI access: CIMT will use the configured API key to check model access. Connect to your private network with OpenAI access. No inference is requested in this check.",
        NetworkPhase.RepositoryBuild => "PAUSED before repository access and builds: connect to your work network for Git, submodules, package restore, and builds.",
        NetworkPhase.OpenAiTesting => "PAUSED before OpenAI testing: CIMT will use the configured API key for AI requests, which may incur charges. Connect to your private network with OpenAI access. Keep any required app backend reachable.",
        _ => throw new InvalidOperationException("Unknown network checkpoint.")
    };

    private async Task WaitForEnter(CancellationToken cancellation)
    {
        try
        {
            // WaitAsync also bounds readers whose underlying stream cannot cancel a pending read.
            if (await input.ReadLineAsync(cancellation).AsTask().WaitAsync(cancellation) is null)
                throw new ConfigurationException("Terminal input closed at a network checkpoint; execution stopped.");
        }
        catch (OperationCanceledException)
        {
            throw new RunLimitException("Whole-run time limit reached while waiting for a network switch.");
        }
    }

    private void Record(RunState state, string result) => state.Stages.Add(new
    {
        stage = "network checkpoint: " + phase,
        result
    });
}
