namespace Cimt;

/// <summary>Checks out the requested branch and its recorded submodule commits.</summary>
public sealed class RepositoryCheckout(RunProcess processes, IRunProgress progress) : IRunStep
{
    public async Task Execute(RunState state)
    {
        var repository = state.Configuration.Root.Get("repository")!;
        var clone = Path.Combine(state.Work, "repository");
        await Clone(state, repository, clone);
        await ReadCommit(state, clone);
        await InitializeSubmodules(state, clone);
        VerifySolution(repository, clone);
        state.Stages.Add(new
        {
            stage = "repository",
            branch = repository.Value("branch"),
            sourceCommit = state.Commit
        });
    }

    private async Task Clone(RunState state, Node repository, string clone)
    {
        progress.Write(state, "Cloning the configured branch");
        var result = await processes.Invoke(state, "git", ["clone", "--depth", "1", "--branch",
            repository.Value("branch")!, "--single-branch", repository.Value("url")!, clone], 180);
        RequireSuccess(state, result, "Git clone failed: ");
    }

    private async Task ReadCommit(RunState state, string clone)
    {
        var result = await processes.Invoke(state, "git", ["-C", clone, "rev-parse", "HEAD"], 15);
        state.Commit = result.Stdout.Trim();
    }

    private async Task InitializeSubmodules(RunState state, string clone)
    {
        progress.Write(state, "Initializing the recorded submodule revisions");
        var result = await processes.Invoke(state, "git", ["-C", clone, "submodule", "update",
            "--init", "--recursive", "--depth", "1"], 600);
        RequireSuccess(state, result, "Submodule initialization failed: ");
    }

    private static void RequireSuccess(RunState state, ProcessResult result, string message)
    {
        if (result.Exit != 0)
            throw new ConfigurationException(message + state.Configuration.Scrub(result.Stderr));
    }

    private static void VerifySolution(Node repository, string clone)
    {
        var path = repository.Value("solution")!.Replace('\\', Path.DirectorySeparatorChar);
        if (!File.Exists(Path.Combine(clone, path)))
            throw new ConfigurationException("Configured solution was not found in the clone.");
    }
}
