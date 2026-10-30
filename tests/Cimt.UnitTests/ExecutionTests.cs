using System.Text.Json;
using Cimt;

namespace Cimt.UnitTests;

public sealed class ExecutionTests : IDisposable
{
    private readonly TestDirectory report = new();
    public void Dispose() => report.Dispose();
    [Theory]
    [InlineData(0, 0, 0)]
    [InlineData(0, 2, 2)]
    [InlineData(2, 1, 1)]
    [InlineData(1, 2, 1)]
    [InlineData(3, 1, 3)]
    [InlineData(1, 3, 3)]
    public void MoreSeriousExitIsKept(int first, int next, int expected)
    {
        Assert.Equal(expected, ExitCodes.Combine(first, next));
    }

    [Fact]
    public void DeadlineUsesTheInjectedClock()
    {
        var clock = new TestClock();
        var deadline = new RunDeadline(clock.GetUtcNow().AddSeconds(40), clock);
        Assert.Equal(10, deadline.RemainingSeconds(10));
        clock.Advance(TimeSpan.FromSeconds(35));
        Assert.Equal(5, deadline.RemainingSeconds(10));
        clock.Advance(TimeSpan.FromSeconds(5));
        Assert.Throws<RunLimitException>(() => deadline.RemainingSeconds(10));
    }

    [Fact]
    public async Task DeadlineStopsProcessCallsBeforeStartingATool()
    {
        var clock = new TestClock();
        var state = State(new RunDeadline(clock.GetUtcNow(), clock));
        var runner = new FakeCommandRunner();
        await Assert.ThrowsAsync<RunLimitException>(() => new RunProcess(runner).Invoke(state, "unused", []));
        Assert.Empty(runner.Commands);
    }

    [Fact]
    public async Task StepFailureStopsLaterStepsButStillCleansAndReports()
    {
        var calls = new List<string>();
        var steps = new[]
        {
            new FakeStep(state => { calls.Add("first"); throw new ConfigurationException("failed"); }),
            new FakeStep(state => calls.Add("must not run"))
        };
        var coordinator = new RunCoordinator(steps, new FakeCleanup(calls), new FakeReport(calls));
        var state = State();
        Assert.Equal(3, await coordinator.Execute(state));
        Assert.Equal(["first", "cleanup", "report"], calls);
        Assert.Contains("failed", state.Errors);
    }

    [Fact]
    public async Task TimeLimitDoesNotEraseAnEarlierBuildFailure()
    {
        var calls = new List<string>();
        var steps = new[] { new FakeStep(state => { state.Exit = 3; throw new RunLimitException("time"); }) };
        var coordinator = new RunCoordinator(steps, new FakeCleanup(calls), new FakeReport(calls));
        Assert.Equal(3, await coordinator.Execute(State()));
        Assert.Equal(["cleanup", "report"], calls);
    }

    [Fact]
    public async Task CleanupFailureIsReportedAsInfrastructureFailure()
    {
        var calls = new List<string>();
        var cleanup = new FakeCleanup(calls) { Fail = true };
        var state = State();
        Assert.Equal(3, await new RunCoordinator([], cleanup, new FakeReport(calls)).Execute(state));
        Assert.Contains(state.Errors, error => error.Contains("finalization requires attention"));
        Assert.Equal(["cleanup", "report"], calls);
    }

    [Fact]
    public void MissingUiResultsCannotProduceAPass()
    {
        Assert.Equal(new RunOutcome(2, "inconclusive", "incomplete"), RunOutcomePolicy.Evaluate(0, null));
    }

    [Theory]
    [InlineData(0, 1)]
    [InlineData(2, 1)]
    [InlineData(3, 3)]
    public void CrashRemainsAFailureWhenExplorationIsIncomplete(int exit, int expected)
    {
        var execution = JsonSerializer.Deserialize<JsonElement>("""
            {"devices":[{"stoppingReason":"limit","error":null,
            "scenarios":[{"crashes":[{}],"completion":"incomplete"}]}]}
            """);
        var outcome = RunOutcomePolicy.Evaluate(exit, execution);
        Assert.Equal(expected, outcome.ExitCode);
        Assert.Equal("failed", outcome.Verdict);
        Assert.Equal("incomplete", outcome.Completion);
    }

    [Theory]
    [InlineData("android", "online", true)]
    [InlineData("ios", "online", true)]
    [InlineData("ios", "offline", false)]
    [InlineData("windows", "online", false)]
    public void SnapshotAcceptsOnlySupportedOnlineDevices(string platform, string state, bool accepted)
    {
        var json = JsonSerializer.SerializeToElement(new
        {
            platform,
            state,
            id = "fixture-device"
        });
        Assert.Equal(accepted, DeviceDiscovery.ReadDevice(json) is not null);
    }

    [Fact]
    public async Task DiscoveryReportsTheRedactedHelperError()
    {
        using var folder = new TestDirectory();
        var origin = Path.Combine(folder.Path, "config.yaml");
        var key = new Node("fixture-secret", null, null, origin);
        var model = new Node(null, new() { ["api-key"] = key }, null, origin);
        var config = new Configuration(new Node(null, new() { ["ai-model"] = model }, null, origin));
        var pair = new RunFolderAllocator().Create(folder.Path, folder.Path, DateTimeOffset.UtcNow);
        var state = new RunState(config, pair, new RunDeadline(DateTimeOffset.UtcNow.AddMinutes(1)));
        var runner = new FakeCommandRunner { Result = new(1, "", "socket path too long fixture-secret") };
        var discovery = new DeviceDiscovery(new RunProcess(runner), new RuntimePaths(folder.Path), new RunProgress());
        var error = await Assert.ThrowsAsync<ConfigurationException>(() => discovery.Execute(state));
        Assert.Contains("socket path too long", error.Message);
        Assert.DoesNotContain("fixture-secret", error.Message);
    }

    [Fact]
    public async Task UserInterruptionStopsLaterStepsAndStillCleansAndReports()
    {
        using var interruption = new RunInterruption(report.Path);
        var state = State(cancellation: interruption.Token);
        var calls = new List<string>();
        var steps = new[] { new FakeStep(_ => interruption.Request()),
            new FakeStep(_ => calls.Add("must not run")) };
        Assert.Equal(2, await new RunCoordinator(steps, new FakeCleanup(calls), new FakeReport(calls)).Execute(state));
        Assert.Equal(["cleanup", "report"], calls);
        Assert.Contains(state.StopReasons, reason => reason.Category == "User interruption");
        Assert.True(File.Exists(Path.Combine(report.Path, "stop-requested")));
    }

    [Fact]
    public async Task InterruptedRunDoesNotEraseAnEarlierFailure()
    {
        using var interruption = new RunInterruption(report.Path);
        var state = State(cancellation: interruption.Token);
        state.Exit = 1;
        interruption.Request();
        var calls = new List<string>();
        Assert.Equal(1, await new RunCoordinator([], new FakeCleanup(calls), new FakeReport(calls)).Execute(state));
    }

    [Fact]
    public async Task CancellationPreventsAnotherProcessFromStarting()
    {
        using var interruption = new RunInterruption(report.Path);
        interruption.Request();
        var runner = new FakeCommandRunner();
        await Assert.ThrowsAnyAsync<OperationCanceledException>(() =>
            new RunProcess(runner).Invoke(State(cancellation: interruption.Token), "unused", []));
        Assert.Empty(runner.Commands);
    }

    [Fact]
    public void RepeatedStopRequestsAreSafe()
    {
        using var interruption = new RunInterruption(report.Path);
        interruption.Request();
        interruption.Request();
        Assert.True(interruption.Token.IsCancellationRequested);
    }

    [Fact]
    public async Task CancellationActivityIsStoppedRatherThanFailed()
    {
        using var cancellation = new CancellationTokenSource();
        cancellation.Cancel();
        var state = State();
        await Assert.ThrowsAnyAsync<OperationCanceledException>(() => state.Activity.Run("Interrupted operation",
            () => Task.FromCanceled(cancellation.Token)));
        Assert.Contains(RunActivityLog.Read(state.Report, state.Configuration.Scrub),
            row => row.Operation == "Interrupted operation" && row.Status == "stopped");
    }

    [Fact]
    public async Task PipeFailureDuringInterruptionDoesNotCreateAnInfrastructureFailure()
    {
        using var interruption = new RunInterruption(report.Path);
        var state = State(cancellation: interruption.Token);
        var calls = new List<string>();
        var step = new FakeStep(_ => { interruption.Request(); throw new IOException("pipe closed"); });
        Assert.Equal(2, await new RunCoordinator([step], new FakeCleanup(calls), new FakeReport(calls)).Execute(state));
        Assert.Contains(state.StopReasons, reason => reason.Category == "User interruption");
        Assert.Empty(state.Errors);
    }

    private RunState State(RunDeadline? deadline = null, CancellationToken cancellation = default)
    {
        var config = new Configuration(new Node(null, [], null, "/fixture/config.yaml"));
        return new(config, TestRunFolders.At(report.Path, DateTimeOffset.UnixEpoch),
            deadline ?? new RunDeadline(DateTimeOffset.UtcNow.AddMinutes(1))) { Cancellation = cancellation };
    }
}

// These fakes record calls. They never start processes, use phones, or call AI.
internal sealed class FakeCommandRunner : ICommandRunner
{
    public List<ProcessCommand> Commands { get; } = [];
    public ProcessResult Result { get; set; } = new(0, "", "");
    public Task<ProcessResult> Run(ProcessCommand command)
    {
        Commands.Add(command);
        return Task.FromResult(Result);
    }
}

internal sealed class FakeStep(Action<RunState> execute) : IRunStep
{
    public Task Execute(RunState state)
    {
        execute(state);
        return Task.CompletedTask;
    }
}

internal sealed class FakeCleanup(List<string> calls) : IRunCleanup
{
    public bool Fail
    {
        get; init;
    }
    public Task Execute(RunState state)
    {
        calls.Add("cleanup");
        if (Fail)
            throw new IOException("fixture failure");
        return Task.CompletedTask;
    }
}

internal sealed class FakeReport(List<string> calls) : IRunReportWriter
{
    public int Write(RunState state)
    {
        calls.Add("report");
        return state.Exit;
    }
}

internal sealed class TestClock : TimeProvider
{
    private DateTimeOffset now = DateTimeOffset.UnixEpoch;
    public override DateTimeOffset GetUtcNow() => now;
    public void Advance(TimeSpan duration) => now += duration;
}
