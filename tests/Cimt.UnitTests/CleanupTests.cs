using Cimt;

namespace Cimt.UnitTests;

/// <summary>Use owned temporary folders to test cleanup without real helper processes.</summary>
public sealed class CleanupTests
{
    [Fact]
    public async Task FailedStopKeepsTheOwnedLinkForNextLaunchRecovery()
    {
        using var fixture = new CleanupFixture();
        fixture.PrepareNativeHome();
        await fixture.Cleanup(new FakeCommandRunner { Result = new(1, "", "fixture") });
        Assert.Equal(Path.Combine(fixture.State.Work, "mobilecli"),
            new DirectoryInfo(fixture.State.Environment["MOBILECLI_HOME"]).LinkTarget);
        Assert.True(Directory.Exists(fixture.State.Work));
    }

    [Fact]
    public async Task SuccessfulHelperStopKeepsOwnedWork()
    {
        using var fixture = new CleanupFixture();
        await fixture.Cleanup(new FakeCommandRunner());
        Assert.True(Directory.Exists(fixture.State.Work));
        Assert.Equal(0, fixture.State.Exit);
    }

    [Fact]
    public async Task NonzeroHelperExitKeepsOwnedWork()
    {
        using var fixture = new CleanupFixture();
        await fixture.Cleanup(new FakeCommandRunner { Result = new(9, "", "") });
        Assert.True(Directory.Exists(fixture.State.Work));
        Assert.Equal(3, fixture.State.Exit);
    }

    [Fact]
    public async Task HelperExceptionKeepsOwnedWork()
    {
        using var fixture = new CleanupFixture();
        await fixture.Cleanup(new ThrowingCommand());
        Assert.True(Directory.Exists(fixture.State.Work));
        Assert.Equal(3, fixture.State.Exit);
        Assert.Single(fixture.State.Errors);
    }

    [Fact]
    public async Task ChangedOwnershipIsNeverDeletedAfterAHelperError()
    {
        using var fixture = new CleanupFixture();
        File.WriteAllText(Path.Combine(fixture.State.Work, ".cimt-owned"), "changed");
        await Assert.ThrowsAsync<IOException>(() => fixture.Cleanup(new ThrowingCommand()));
        Assert.True(Directory.Exists(fixture.State.Work));
    }

    [Fact]
    public async Task MissingOwnedHelperAddressDoesNotStopAGlobalDaemon()
    {
        using var fixture = new CleanupFixture();
        fixture.State.Environment.Remove("MOBILECLI_HOME");
        var runner = new FakeCommandRunner();
        await fixture.Cleanup(runner);
        Assert.Empty(runner.Commands);
    }

    [Fact]
    public async Task HelperFailureDetailsAreRetained()
    {
        using var fixture = new CleanupFixture();
        await fixture.Cleanup(new FakeCommandRunner { Result = new(1, "", "socket path too long") });
        Assert.Contains(fixture.State.Errors, error => error.Contains("socket path too long"));
    }

    [Fact]
    public async Task HelperLogSurvivesWorkCleanup()
    {
        using var fixture = new CleanupFixture();
        var home = Path.Combine(fixture.State.Work, "mobilecli");
        Directory.CreateDirectory(home);
        await File.WriteAllTextAsync(Path.Combine(home, "daemon.log"), "helper failed");
        await fixture.Cleanup(new FakeCommandRunner());
        var retained = Path.Combine(fixture.State.Report, "logs", "native-daemon.log");
        Assert.Equal("helper failed", await File.ReadAllTextAsync(retained));
        Assert.True(Directory.Exists(fixture.State.Work));
    }

    [Fact]
    public async Task RetainedHelperLogRedactsConfiguredSecrets()
    {
        var origin = "/fixture/config.yaml";
        var model = new Node(null, new() { ["api-key"] = new("fixture-secret", null, null, origin) }, null, origin);
        var config = new Configuration(new Node(null, new() { ["ai-model"] = model }, null, origin));
        using var fixture = new CleanupFixture(config);
        var home = Path.Combine(fixture.State.Work, "mobilecli");
        Directory.CreateDirectory(home);
        await File.WriteAllTextAsync(Path.Combine(home, "daemon.log"), "failed fixture-secret");
        await fixture.Cleanup(new FakeCommandRunner());
        var retained = Path.Combine(fixture.State.Report, "logs", "native-daemon.log");
        Assert.Equal("failed <redacted>", await File.ReadAllTextAsync(retained));
        Assert.Equal("failed <redacted>", await File.ReadAllTextAsync(Path.Combine(home, "daemon.log")));
    }
}

internal sealed class CleanupFixture : IDisposable
{
    private readonly TestDirectory directory = new();
    private readonly WorkDirectoryManager folders;
    public RunState State
    {
        get;
    }

    public CleanupFixture(Configuration? configuration = null)
    {
        folders = new(Path.Combine(directory.Path, "owned.json"));
        var config = configuration ?? new Configuration(new Node(null, [], null, Path.Combine(directory.Path, "config.yaml")));
        var pair = new RunFolderAllocator().Create(directory.Path, directory.Path, DateTimeOffset.UtcNow);
        State = new(config, pair, new RunDeadline(DateTimeOffset.UtcNow.AddMinutes(1)));
        State.Work = folders.Create(pair);
        State.Environment["MOBILECLI_HOME"] = "fixture-owned-helper";
    }

    public Task Cleanup(ICommandRunner runner) => new RunCleanup(runner, new RuntimePaths(directory.Path), folders).Execute(State);
    public void PrepareNativeHome() => State.Environment["MOBILECLI_HOME"] = folders.PrepareNativeHome(State.Work);
    public void Dispose()
    {
        if (new DirectoryInfo(folders.NativeHomeAddress).LinkTarget is not null)
            folders.ReleaseNativeHome(State.Work);
        directory.Dispose();
    }
}

internal sealed class ThrowingCommand : ICommandRunner
{
    public Task<ProcessResult> Run(ProcessCommand command) => throw new IOException("Synthetic helper failure");
}
