using System.Globalization;

namespace Cimt;

/// <summary>Connects production services. The coordinator owns the run order.</summary>
public static class RunEngine
{
    public static Task<int> Execute(Configuration config, RunFolders runFolders) => Start(config, runFolders, false);

    public static Task<int> Replay(Configuration config, RunFolders runFolders) => Start(config, runFolders, true);

    private static async Task<int> Start(Configuration config, RunFolders runFolders, bool replay)
    {
        using var http = new HttpClient { Timeout = TimeSpan.FromSeconds(20) };
        var root = Configuration.InstallationRoot;
        var paths = new RuntimePaths(root);
        var runner = new CommandRunner();
        var processes = new RunProcess(runner);
        var progress = new RunProgress();
        var folders = new WorkDirectoryManager(Path.Combine(root, "state/owned-work.json"));
        // Console.In can block even on an async read. Use the input stream for bounded waits.
        using var terminalInput = new StreamReader(Console.OpenStandardInput());
        using var interruption = new RunInterruption(runFolders.Report);
        interruption.Listen();
        var reports = new RunReportWriter(new LatestReportPublisher(config.ReportsRoot));
        var steps = CreateSteps(paths, processes, progress, folders, new TextInputReader(http), terminalInput, runner, replay, reports);
        var coordinator = new RunCoordinator(steps, new RunCleanup(runner, paths, folders), reports);
        return await coordinator.Execute(CreateState(config, runFolders, replay, interruption.Token));
    }

    private static IRunStep[] CreateSteps(RuntimePaths paths, RunProcess processes, IRunProgress progress,
        WorkDirectoryManager folders, ITextInputReader inputs, TextReader terminalInput, ICommandRunner runner, bool replay,
        IRunReportWriter reports)
    {
        var retained = new RetainedBuildStore();
        var steps = new List<IRunStep> { new TextInputLoader(inputs), new RuntimeFilesCheck(paths) };
        if (replay)
            steps.Add(new LoadRetainedBuilds(retained));
        steps.AddRange([
            new WorkPreparation(folders, runner, paths),
            new ExecutionCheckpoint(ExecutionPhase.OpenAiPreflight, terminalInput, Console.Out, Console.IsInputRedirected),
            new ModelAccessCheck(processes, paths, progress),
            new DeviceDiscovery(processes, paths, progress)
        ]);
        if (!replay)
            steps.AddRange([
                new ExecutionCheckpoint(ExecutionPhase.RepositoryBuild, terminalInput, Console.Out, Console.IsInputRedirected),
                new RepositoryCheckout(processes, progress, folders),
                new ApplicationBuilds(new BuildJobFactory(paths), new ApplicationBuilder(processes, new BuildArtifactStore(), progress)),
                new SaveRetainedBuilds(retained)
            ]);
        steps.AddRange([
            new ExecutionCheckpoint(ExecutionPhase.OpenAiTesting, terminalInput, Console.Out, Console.IsInputRedirected),
            new UiExecution(processes, paths, progress, reports)
        ]);
        return steps.ToArray();
    }

    private static RunState CreateState(Configuration config, RunFolders runFolders, bool replay, CancellationToken cancellation)
    {
        var minutes = double.Parse(config.Root.Get("execution")!.Value("time-limit-minutes")!, CultureInfo.InvariantCulture);
        return new(config, runFolders, new RunDeadline(runFolders.Identity.Started.AddMinutes(minutes)))
        {
            Command = replay ? "replay" : "run", Cancellation = cancellation
        };
    }
}
