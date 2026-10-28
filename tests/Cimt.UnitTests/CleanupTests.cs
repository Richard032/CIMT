using Cimt;

namespace Cimt.UnitTests;

/// <summary>Use owned temporary folders to test cleanup without real helper processes.</summary>
public sealed class CleanupTests
{
    [Fact]
    public async Task SuccessfulHelperStopRemovesOwnedWork()
    {
        using var fixture = new CleanupFixture();
        await fixture.Cleanup(new FakeCommandRunner());
        Assert.False(Directory.Exists(fixture.State.Work));
        Assert.Equal(0, fixture.State.Exit);
    }

    [Fact]
    public async Task NonzeroHelperExitStillRemovesOwnedWork()
    {
        using var fixture = new CleanupFixture();
        await fixture.Cleanup(new FakeCommandRunner { Result = new(9, "", "") });
        Assert.False(Directory.Exists(fixture.State.Work));
        Assert.Equal(3, fixture.State.Exit);
    }

    [Fact]
    public async Task HelperExceptionStillRemovesOwnedWork()
    {
        using var fixture = new CleanupFixture();
        await fixture.Cleanup(new ThrowingCommand());
        Assert.False(Directory.Exists(fixture.State.Work));
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
}

internal sealed class CleanupFixture : IDisposable
{
    private readonly TestDirectory directory = new();
    private readonly WorkDirectoryManager folders;
    public RunState State
    {
        get;
    }

    public CleanupFixture()
    {
        folders = new(Path.Combine(directory.Path, "owned.json"));
        var config = new Configuration(new Node(null, [], null, Path.Combine(directory.Path, "config.yaml")));
        State = new(config, directory.Path, DateTimeOffset.UtcNow, new RunDeadline(DateTimeOffset.UtcNow.AddMinutes(1)));
        State.Work = folders.Create(directory.Path);
    }

    public Task Cleanup(ICommandRunner runner) => new RunCleanup(runner, new RuntimePaths(directory.Path), folders).Execute(State);
    public void Dispose() => directory.Dispose();
}

internal sealed class ThrowingCommand : ICommandRunner
{
    public Task<ProcessResult> Run(ProcessCommand command) => throw new IOException("Synthetic helper failure");
}
