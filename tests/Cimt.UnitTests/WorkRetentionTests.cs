using System.Text.Json;
using Cimt;

namespace Cimt.UnitTests;

public sealed class WorkRetentionTests
{
    [Fact]
    public async Task PreparationKeepsEarlierRepositoryContent()
    {
        using var folder = new TestDirectory();
        var manager = new WorkDirectoryManager(Path.Combine(folder.Path, "owned.json"));
        var first = CreateWork(manager, folder.Path);
        await File.WriteAllTextAsync(Path.Combine(first.Work, "keep.txt"), "previous build");
        var state = State(folder.Path);
        await new WorkPreparation(manager, new FakeCommandRunner(), new RuntimePaths(folder.Path)).Execute(state);
        try { Assert.Equal("previous build", await File.ReadAllTextAsync(Path.Combine(first.Work, "keep.txt"))); }
        finally { manager.ReleaseNativeHome(state.Work); }
    }

    [Fact]
    public void BeforeCloneDeletesOnlyEarlierOwnedWorkForTheSameInputs()
    {
        using var folder = new TestDirectory();
        var manager = new WorkDirectoryManager(Path.Combine(folder.Path, "owned.json"));
        var previous = CreateWork(manager, Path.Combine(folder.Path, "first"));
        var other = CreateWork(manager, Path.Combine(folder.Path, "other"));
        var current = CreateWork(manager, Path.Combine(folder.Path, "first"));
        var unrelated = Path.Combine(Path.GetDirectoryName(current.Work)!, "user-files");
        Directory.CreateDirectory(unrelated);
        manager.CleanupPrevious(current.Report, current.Work);
        Assert.False(Directory.Exists(previous.Work));
        Assert.True(Directory.Exists(previous.Report));
        Assert.True(Directory.Exists(current.Work));
        Assert.True(Directory.Exists(other.Work));
        Assert.True(Directory.Exists(unrelated));
    }

    [Fact]
    public async Task PreflightFailureKeepsBothOldAndNewWork()
    {
        using var folder = new TestDirectory();
        var manager = new WorkDirectoryManager(Path.Combine(folder.Path, "owned.json"));
        var previous = CreateWork(manager, folder.Path);
        var state = State(folder.Path);
        var runner = new FakeCommandRunner();
        var paths = new RuntimePaths(folder.Path);
        var coordinator = new RunCoordinator([
            new WorkPreparation(manager, runner, paths),
            new FakeStep(_ => throw new ConfigurationException("preflight failed"))
        ], new RunCleanup(runner, paths, manager), new FakeReport([]));
        Assert.Equal(3, await coordinator.Execute(state));
        Assert.True(Directory.Exists(previous.Work));
        Assert.True(Directory.Exists(state.Work));
        Assert.Null(new DirectoryInfo(manager.NativeHomeAddress).LinkTarget);
    }

    [Fact]
    public async Task InterruptedHelperIsStoppedWithoutDeletingItsWork()
    {
        using var folder = new TestDirectory();
        var manager = new WorkDirectoryManager(Path.Combine(folder.Path, "owned.json"));
        var previous = CreateWork(manager, folder.Path);
        manager.PrepareNativeHome(previous.Work);
        var state = State(folder.Path);
        var runner = new FakeCommandRunner();
        await new WorkPreparation(manager, runner, new RuntimePaths(folder.Path)).Execute(state);
        try
        {
            Assert.Single(runner.Commands);
            Assert.True(Directory.Exists(previous.Work));
            Assert.Equal(Path.Combine(state.Work, "mobilecli"), new DirectoryInfo(manager.NativeHomeAddress).LinkTarget);
        }
        finally { manager.ReleaseNativeHome(state.Work); }
    }

    [Fact]
    public async Task FailedInterruptedHelperStopDoesNotDeleteOrReplaceWork()
    {
        using var folder = new TestDirectory();
        var manager = new WorkDirectoryManager(Path.Combine(folder.Path, "owned.json"));
        var previous = CreateWork(manager, folder.Path);
        manager.PrepareNativeHome(previous.Work);
        var state = State(folder.Path);
        var runner = new FakeCommandRunner { Result = new(1, "", "fixture") };
        try
        {
            await Assert.ThrowsAsync<ConfigurationException>(() =>
                new WorkPreparation(manager, runner, new RuntimePaths(folder.Path)).Execute(state));
            Assert.True(Directory.Exists(previous.Work));
            Assert.Equal("", state.Work);
        }
        finally { manager.ReleaseNativeHome(previous.Work); }
    }

    [Fact]
    public void LegacyOwnershipRecordSurvivesUntilTheNextClone()
    {
        using var folder = new TestDirectory();
        var registry = Path.Combine(folder.Path, "owned.json");
        var manager = new WorkDirectoryManager(registry);
        var previous = CreateWork(manager, folder.Path);
        File.WriteAllText(registry, JsonSerializer.Serialize(new
        {
            path = previous.Work,
            token = File.ReadAllText(Path.Combine(previous.Work, ".cimt-owned")),
            report = previous.Report
        }));
        var current = CreateWork(manager, folder.Path);
        Assert.True(Directory.Exists(previous.Work));
        manager.CleanupPrevious(current.Report, current.Work);
        Assert.False(Directory.Exists(previous.Work));
        Assert.True(Directory.Exists(current.Work));
    }

    private static RunFolders CreateWork(WorkDirectoryManager manager, string input)
    {
        var layout = new OutputLayout(input);
        var pair = new RunFolderAllocator().Create(layout.WorkRoot, layout.ReportsRoot, DateTimeOffset.UtcNow);
        manager.Create(pair);
        return pair;
    }

    private static RunState State(string input)
    {
        var configuration = new Configuration(new Node(null, [], null, Path.Combine(input, "app.yaml")));
        var pair = new RunFolderAllocator().Create(configuration.WorkspaceRoot, configuration.ReportsRoot, DateTimeOffset.UtcNow);
        return new(configuration, pair, new RunDeadline(DateTimeOffset.UtcNow.AddMinutes(1)));
    }
}
