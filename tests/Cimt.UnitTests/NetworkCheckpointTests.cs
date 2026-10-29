using System.Text.Json;
using Cimt;

namespace Cimt.UnitTests;

public sealed class NetworkCheckpointTests
{
    [Theory]
    [InlineData(null)]
    [InlineData("false")]
    public async Task UnattendedRunsDoNotReadTerminalInput(string? setting)
    {
        using var input = new ControlledTerminalInput();
        using var output = new StringWriter();
        var state = State(setting);
        await new NetworkCheckpoint(NetworkPhase.OpenAiPreflight, input, output, true).Execute(state);
        Assert.False(input.ReadStarted.Task.IsCompleted);
        Assert.Equal("", output.ToString());
        Assert.Empty(state.Stages);
    }

    [Theory]
    [InlineData(NetworkPhase.OpenAiPreflight, "configured API key", "No inference")]
    [InlineData(NetworkPhase.RepositoryBuild, "work network", "Git, submodules")]
    [InlineData(NetworkPhase.OpenAiTesting, "configured API key", "may incur charges")]
    public async Task EachCheckpointExplainsTheNextStage(NetworkPhase phase, string expected, string detail)
    {
        using var input = new StringReader("\n");
        using var output = new StringWriter();
        var state = State("true");
        state.Builds.Add([]);
        await new NetworkCheckpoint(phase, input, output, false).Execute(state);
        Assert.Contains(expected, output.ToString());
        Assert.Contains(detail, output.ToString());
        Assert.Contains("press Enter", output.ToString());
        Assert.Contains("continued", JsonSerializer.Serialize(state.Stages));
        Assert.DoesNotContain("synthetic-private-key", output.ToString());
    }

    [Fact]
    public async Task FollowingStageWaitsForAcknowledgement()
    {
        using var input = new ControlledTerminalInput();
        using var output = new StringWriter();
        var calls = new List<string>();
        var state = State("true");
        var coordinator = new RunCoordinator([
            new NetworkCheckpoint(NetworkPhase.OpenAiPreflight, input, output, false),
            new FakeStep(_ => calls.Add("OpenAI request"))
        ], new FakeCleanup(calls), new FakeReport(calls));

        var execution = coordinator.Execute(state);
        await input.ReadStarted.Task.WaitAsync(TimeSpan.FromSeconds(5));
        Assert.Empty(calls);
        Assert.False(execution.IsCompleted);
        input.Line.SetResult("");
        await execution;
        Assert.Equal(["OpenAI request", "cleanup", "report"], calls);
    }

    [Fact]
    public async Task EnabledPausesRejectRedirectedInputBeforeReading()
    {
        using var input = new ControlledTerminalInput();
        var state = State("true");
        var error = await Assert.ThrowsAsync<ConfigurationException>(() =>
            new NetworkCheckpoint(NetworkPhase.OpenAiPreflight, input, TextWriter.Null, true).Execute(state));
        Assert.Contains("execution.network-switch-pauses to false", error.Message);
        Assert.False(input.ReadStarted.Task.IsCompleted);
    }

    [Fact]
    public async Task ClosedInputStopsLaterWorkAndStillReports()
    {
        using var input = new StringReader("");
        var calls = new List<string>();
        var state = State("true");
        var coordinator = new RunCoordinator([
            new NetworkCheckpoint(NetworkPhase.RepositoryBuild, input, TextWriter.Null, false),
            new FakeStep(_ => calls.Add("must not clone"))
        ], new FakeCleanup(calls), new FakeReport(calls));
        Assert.Equal(3, await coordinator.Execute(state));
        Assert.Equal(["cleanup", "report"], calls);
        Assert.Contains(state.Errors, error => error.Contains("Terminal input closed"));
    }

    [Fact]
    public async Task MissingBuildsDoNotAskToSwitchBackForTesting()
    {
        using var input = new ControlledTerminalInput();
        var state = State("true");
        await new NetworkCheckpoint(NetworkPhase.OpenAiTesting, input, TextWriter.Null, false).Execute(state);
        Assert.False(input.ReadStarted.Task.IsCompleted);
        Assert.Empty(state.Stages);
    }

    [Fact]
    public async Task TerminalResponseIsNeverPrintedOrRecorded()
    {
        using var input = new StringReader("private terminal response\n");
        using var output = new StringWriter();
        var state = State("true");
        await new NetworkCheckpoint(NetworkPhase.OpenAiPreflight, input, output, false).Execute(state);
        var history = JsonSerializer.Serialize(state.Stages);
        Assert.Contains("OpenAiPreflight", history);
        Assert.Contains("waiting", history);
        Assert.Contains("continued", history);
        Assert.DoesNotContain("private terminal response", history);
        Assert.DoesNotContain("private terminal response", output.ToString());
    }

    [Fact]
    public async Task ExpiredRunDoesNotWaitForInput()
    {
        using var input = new ControlledTerminalInput();
        var state = State("true", new RunDeadline(DateTimeOffset.UtcNow.AddSeconds(-1)));
        await Assert.ThrowsAsync<RunLimitException>(() =>
            new NetworkCheckpoint(NetworkPhase.OpenAiPreflight, input, TextWriter.Null, false).Execute(state));
        Assert.False(input.ReadStarted.Task.IsCompleted);
    }

    [Fact]
    public async Task PendingInputCannotOutlastTheWholeRunLimit()
    {
        using var input = new ControlledTerminalInput();
        var state = State("true", new RunDeadline(DateTimeOffset.UtcNow.AddSeconds(2)));
        var error = await Assert.ThrowsAsync<RunLimitException>(() =>
            new NetworkCheckpoint(NetworkPhase.OpenAiPreflight, input, TextWriter.Null, false)
                .Execute(state).WaitAsync(TimeSpan.FromSeconds(5)));
        Assert.Contains("waiting for a network switch", error.Message);
        Assert.DoesNotContain("continued", JsonSerializer.Serialize(state.Stages));
    }

    [Fact]
    public async Task AcknowledgementAfterTheDeadlineDoesNotContinue()
    {
        using var input = new ControlledTerminalInput();
        var clock = new TestClock();
        var state = State("true", new RunDeadline(clock.GetUtcNow().AddMinutes(1), clock));
        var execution = new NetworkCheckpoint(NetworkPhase.OpenAiPreflight, input, TextWriter.Null, false).Execute(state);
        await input.ReadStarted.Task.WaitAsync(TimeSpan.FromSeconds(5));
        clock.Advance(TimeSpan.FromMinutes(1));
        input.Line.SetResult("");
        await Assert.ThrowsAsync<RunLimitException>(() => execution);
        Assert.DoesNotContain("continued", JsonSerializer.Serialize(state.Stages));
    }

    [Theory]
    [InlineData("true")]
    [InlineData("false")]
    public async Task BooleanPauseSettingIsAccepted(string value)
    {
        using var fixture = new InputFolderFixture();
        await fixture.Prepare();
        var root = Node.Read(fixture.SharedFile);
        new ConfigurationValidator().Validate(WithSetting(root, value));
    }

    [Theory]
    [InlineData("yes")]
    [InlineData("1")]
    [InlineData("")]
    public async Task InvalidPauseSettingIsRejected(string value)
    {
        using var fixture = new InputFolderFixture();
        await fixture.Prepare();
        var root = Node.Read(fixture.SharedFile);
        Assert.Throws<ConfigurationException>(() => new ConfigurationValidator().Validate(WithSetting(root, value)));
    }

    private static Node WithSetting(Node root, string? value) => Node.Merge(root,
        new(null, new() { ["execution"] = new(null, value is null ? [] : new()
        {
            ["network-switch-pauses"] = new(value, null, null, root.Origin)
        }, null, root.Origin) }, null, root.Origin));

    private static RunState State(string? setting, RunDeadline? deadline = null)
    {
        const string origin = "/fixture/config.yaml";
        var root = new Node(null, new()
        {
            ["ai-model"] = new(null, new() { ["api-key"] = new("synthetic-private-key", null, null, origin) }, null, origin)
        }, null, origin);
        return new(new Configuration(WithSetting(root, setting)), TestRunFolders.At("/unused-report", DateTimeOffset.UtcNow),
            deadline ?? new RunDeadline(DateTimeOffset.UtcNow.AddMinutes(1)));
    }
}

/// <summary>A small terminal fake lets each test decide when Enter arrives.</summary>
internal sealed class ControlledTerminalInput : TextReader
{
    public TaskCompletionSource ReadStarted { get; } = new(TaskCreationOptions.RunContinuationsAsynchronously);
    public TaskCompletionSource<string?> Line { get; } = new(TaskCreationOptions.RunContinuationsAsynchronously);

    public override ValueTask<string?> ReadLineAsync(CancellationToken cancellationToken)
    {
        ReadStarted.SetResult();
        return new(Line.Task.WaitAsync(cancellationToken));
    }
}
