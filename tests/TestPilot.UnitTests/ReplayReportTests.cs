using System.Text.Json;
using TestPilot;

namespace TestPilot.UnitTests;

public sealed class ReplayReportTests
{
    [Fact]
    public async Task ReplayHasItsOwnFolderAndKeepsThePreviousReport()
    {
        using var fixture = new DiagnosticFixture();
        await fixture.Prepare();
        var writer = new RunReportWriter();
        RunFinalization.Finish(fixture.State, writer);
        var previous = File.ReadAllText(Path.Combine(fixture.State.Report, "index.html"));
        var pair = new RunFolderAllocator().Create(fixture.State.Configuration.WorkspaceRoot,
            fixture.State.Configuration.ReportsRoot, fixture.State.Started.AddMinutes(1));
        var replay = new RunState(fixture.State.Configuration, pair, fixture.State.Deadline) { Command = "replay" };
        RunFinalization.Finish(replay, writer);
        var html = File.ReadAllText(Path.Combine(replay.Report, "index.html"));
        Assert.NotEqual(fixture.State.Report, replay.Report);
        Assert.Equal(2, Directory.GetDirectories(fixture.State.Configuration.ReportsRoot).Length);
        Assert.Contains("Command: replay", html);
        Assert.Contains("<title>TestPilot replay — " + pair.Identity.Id, html);
        Assert.DoesNotContain("<base", html);
        Assert.Equal(previous, File.ReadAllText(Path.Combine(fixture.State.Report, "index.html")));
        Assert.False(File.Exists(Path.Combine(fixture.State.Configuration.ReportsRoot, "index.html")));
    }

    [Fact]
    public async Task ReplaySnapshotsAndFinalResultStayInTheSameFolder()
    {
        using var fixture = new DiagnosticFixture();
        await fixture.Prepare();
        var replay = new RunState(fixture.State.Configuration, fixture.State.Folders, fixture.State.Deadline) { Command = "replay" };
        var writer = new RunReportWriter();
        RunFinalization.Snapshot(replay, writer);
        Assert.Contains("Partial report", File.ReadAllText(Path.Combine(replay.Report, "index.html")));
        RunFinalization.Finish(replay, writer);
        Assert.DoesNotContain("Partial report", File.ReadAllText(Path.Combine(replay.Report, "index.html")));
        var result = JsonSerializer.Deserialize<JsonElement>(File.ReadAllText(Path.Combine(replay.Report, "result.json")));
        Assert.Equal("replay", result.GetProperty("command").GetString());
        Assert.Equal(replay.Identity.Id, result.GetProperty("runIdentity").GetProperty("id").GetString());
        Assert.Single(Directory.GetDirectories(replay.Configuration.ReportsRoot));
        Assert.False(File.Exists(Path.Combine(replay.Configuration.ReportsRoot, "index.html")));
    }

    [Theory]
    [InlineData("run")]
    [InlineData("replay")]
    public async Task EarlyErrorStaysInsideItsAllocatedFolder(string command)
    {
        using var fixture = new DiagnosticFixture();
        await fixture.Prepare();
        var session = new CommandSession(fixture.State.Started)
        {
            Command = command, Folders = fixture.State.Folders,
            Outputs = fixture.State.Configuration.Outputs
        };
        session.Messages.Add("configuration failed");
        await new CommandReports().Write(session, "inconclusive", "incomplete", 3);
        var html = File.ReadAllText(Path.Combine(session.Report!, "index.html"));
        Assert.Contains("Command: " + command, html);
        Assert.Contains(session.Folders.Identity.Id, html);
        Assert.DoesNotContain("<base", html);
        Assert.False(File.Exists(Path.Combine(session.Outputs.ReportsRoot, "index.html")));
    }

    [Fact]
    public async Task ReplayHtmlContainsBothPlatformsAndRelativeScreenshots()
    {
        using var fixture = new DiagnosticFixture();
        await fixture.Prepare();
        var replay = new RunState(fixture.State.Configuration, fixture.State.Folders, fixture.State.Deadline) { Command = "replay" };
        var devices = new[] { "ios", "android" }.Select(platform => new
        {
            device = new { id = platform, platform, name = platform + " phone" },
            scenarios = new[] { new { target = "Release", verdict = "inconclusive", completion = "incomplete",
                crashes = Array.Empty<object>(),
                steps = new[] { new { action = "tap", observation = "Observed control", screenshot = "devices/" + platform + "/step.png" } } } }
        });
        File.WriteAllText(Path.Combine(replay.Report, "ui-results.json"), JsonSerializer.Serialize(new { devices }));
        RunFinalization.Finish(replay, new RunReportWriter());
        var html = File.ReadAllText(Path.Combine(replay.Report, "index.html"));
        Assert.Contains("ios phone", html);
        Assert.Contains("android phone", html);
        Assert.Contains("devices/ios/step.png", html);
        Assert.Contains("devices/android/step.png", html);
        Assert.DoesNotContain("<base", html);
    }
}
