using Cimt;

namespace Cimt.UnitTests;

/// <summary>Verify command ownership and error paths without tools, devices, or an API.</summary>
public sealed class CommandIdentityTests
{
    [Fact]
    public async Task InvocationReadsTheClockOnceAndPassesItsIdentityToTheRun()
    {
        using var fixture = new CommandIdentityFixture();
        Assert.Equal(0, await fixture.Execute("run"));
        Assert.Equal(1, fixture.Clock.Reads);
        Assert.Equal(fixture.Started, fixture.Received!.Identity.Started);
        Assert.True(fixture.RunHeldLock);
        Assert.False(fixture.Lock.Held);
    }

    [Fact]
    public async Task FailedRunKeepsTheSameIdentityWhileReportingUnderTheLock()
    {
        using var fixture = new CommandIdentityFixture();
        fixture.FailRun = true;
        Assert.Equal(3, await fixture.Execute("run"));
        Assert.Same(fixture.Received, fixture.Reports.Session!.Folders);
        Assert.True(fixture.Reports.HeldLockOnWrite);
        Assert.Single(Directory.GetDirectories(fixture.ReportRoot, "report_*"));
        Assert.False(fixture.Lock.Held);
    }

    [Fact]
    public async Task ValidationRetainsAnIdentityWithoutCreatingCloneWork()
    {
        using var fixture = new CommandIdentityFixture();
        Assert.Equal(0, await fixture.Execute("validate"));
        var pair = fixture.Reports.Session!.Folders!;
        Assert.False(Directory.Exists(pair.Work));
        Assert.True(File.Exists(Path.Combine(pair.Report, "run-identity.json")));
        Assert.True(fixture.Reports.HeldLockOnWrite);
    }

    [Fact]
    public async Task RejectedInvocationCannotAlterTheActiveRun()
    {
        using var fixture = new CommandIdentityFixture();
        var active = new RunFolderAllocator().Create(fixture.WorkRoot, fixture.ReportRoot, fixture.Started);
        Directory.CreateDirectory(active.Work);
        File.WriteAllText(Path.Combine(active.Work, "keep.txt"), "active source");
        var metadata = File.ReadAllText(Path.Combine(active.Report, "run-identity.json"));
        fixture.Lock.Reject = true;
        Assert.Equal(3, await fixture.Execute("run"));
        Assert.Null(fixture.Received);
        Assert.Equal(0, fixture.Loader.Calls);
        Assert.NotEqual(active.Identity.Id, fixture.Reports.Session!.Folders!.Identity.Id);
        Assert.Equal("active source", File.ReadAllText(Path.Combine(active.Work, "keep.txt")));
        Assert.Equal(metadata, File.ReadAllText(Path.Combine(active.Report, "run-identity.json")));
    }
}

internal sealed class CommandIdentityFixture : IDisposable
{
    private readonly TestDirectory directory = new();
    public DateTimeOffset Started { get; } = new(2026, 10, 28, 14, 30, 0, TimeSpan.Zero);
    public string WorkRoot => Path.Combine(directory.Path, "work");
    public string ReportRoot => Path.Combine(directory.Path, "reports");
    public CountingClock Clock
    {
        get;
    }
    public RecordingRunLock Lock { get; } = new();
    public IdentityConfigurationLoader Loader
    {
        get;
    }
    public IdentityCommandReports Reports
    {
        get;
    }
    public RunFolders? Received
    {
        get; private set;
    }
    public bool RunHeldLock
    {
        get; private set;
    }
    public bool FailRun
    {
        get; set;
    }

    public CommandIdentityFixture()
    {
        Clock = new(Started);
        var file = Path.Combine(directory.Path, "fixture.yaml");
        File.WriteAllText(file, """
            workspace: {root: ./work}
            reports: {root: ./reports}
            repository: {url: 'https://example.invalid/app.git', branch: main, solution: App.sln}
            execution: {time-limit-minutes: 5}
            ai-model: {name: fixture-model, api-key: synthetic-credential}
            ai-budget: {amount: 1, currency: USD}
            inputs: {instructions: ./instructions.txt}
            build: {targets: [{name: fixture, configuration: Release, project: App.csproj, android: {framework: net10.0-android}}]}
            """);
        if (!OperatingSystem.IsWindows())
            File.SetUnixFileMode(file, UnixFileMode.UserRead | UnixFileMode.UserWrite);
        Loader = new(new Configuration(Node.Read(file)));
        Reports = new(ReportRoot, Lock);
    }

    public Task<int> Execute(string command) => new CommandApplication(Loader, new IdentityReadiness(),
        Run, Reports, new RunFolderAllocator(), Lock.Acquire, TextWriter.Null, TextWriter.Null, Clock)
        .Run([command, "--config", "fixture.yaml"]);

    private Task<int> Run(Configuration config, RunFolders folders)
    {
        Received = folders;
        RunHeldLock = Lock.Held;
        if (FailRun)
            throw new ConfigurationException("fixture run failure");
        return Task.FromResult(0);
    }

    public void Dispose() => directory.Dispose();
}

// The following fakes store calls; none forwards to another implementation.
internal sealed class CountingClock(DateTimeOffset now) : TimeProvider
{
    public int Reads
    {
        get; private set;
    }
    public override DateTimeOffset GetUtcNow()
    {
        Reads++;
        return now;
    }
}

internal sealed class RecordingRunLock : IDisposable
{
    public bool Held
    {
        get; private set;
    }
    public bool Reject
    {
        get; set;
    }
    public IDisposable Acquire()
    {
        if (Reject)
            throw new ConfigurationException("Another run is active.");
        Held = true;
        return this;
    }
    public void Dispose() => Held = false;
}

internal sealed class IdentityConfigurationLoader(Configuration configuration) : IConfigurationLoader
{
    public int Calls
    {
        get; private set;
    }
    public Configuration Load(CommandOptions options)
    {
        Calls++;
        return configuration;
    }
}

internal sealed class IdentityReadiness : IReadinessValidator
{
    public Task Validate(Configuration configuration, List<string> messages) => Task.CompletedTask;
}

internal sealed class IdentityCommandReports(string root, RecordingRunLock runLock) : ICommandReports
{
    public CommandSession? Session
    {
        get; private set;
    }
    public bool HeldLockOnWrite
    {
        get; private set;
    }
    public string ErrorRoot(Configuration? configuration) => root;
    public Task SaveConfiguration(CommandSession session) => Task.CompletedTask;
    public Task Write(CommandSession session, string verdict, string completion, int exit)
    {
        Session = session;
        HeldLockOnWrite = runLock.Held;
        return Task.CompletedTask;
    }
}
