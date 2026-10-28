using System.Globalization;

namespace Cimt;

/// <summary>Connects production services. The coordinator owns the run order.</summary>
public static class RunEngine
{
    public static async Task<int> Execute(Configuration config, RunFolders runFolders)
    {
        using var http = new HttpClient { Timeout = TimeSpan.FromSeconds(20) };
        var root = Configuration.InstallationRoot;
        var paths = new RuntimePaths(root);
        var runner = new CommandRunner();
        var processes = new RunProcess(runner);
        var progress = new RunProgress();
        var folders = new WorkDirectoryManager(Path.Combine(root, "state/owned-work.json"));
        var steps = CreateSteps(paths, processes, progress, folders, new TextInputReader(http));
        var coordinator = new RunCoordinator(steps, new RunCleanup(runner, paths, folders), new RunReportWriter());
        return await coordinator.Execute(CreateState(config, runFolders));
    }

    private static IRunStep[] CreateSteps(RuntimePaths paths, RunProcess processes, IRunProgress progress,
        WorkDirectoryManager folders, ITextInputReader inputs) =>
    [
        new TextInputLoader(inputs),
        new RuntimeFilesCheck(paths),
        new WorkPreparation(folders),
        new ModelAccessCheck(processes, paths, progress),
        new DeviceDiscovery(processes, paths, progress),
        new RepositoryCheckout(processes, progress),
        new ApplicationBuilds(new BuildJobFactory(paths), new ApplicationBuilder(processes, new BuildArtifactStore(), progress)),
        new UiExecution(processes, paths, progress)
    ];

    private static RunState CreateState(Configuration config, RunFolders runFolders)
    {
        var minutes = double.Parse(config.Root.Get("execution")!.Value("time-limit-minutes")!, CultureInfo.InvariantCulture);
        return new(config, runFolders, new RunDeadline(runFolders.Identity.Started.AddMinutes(minutes)));
    }
}
