using Cimt;

namespace Cimt.UnitTests;

public sealed class LatestReportTests
{
    [Fact]
    public async Task RunSnapshotPublishesPartialReportAtStablePath()
    {
        using var fixture = new DiagnosticFixture();
        await fixture.Prepare();
        var latest = new LatestReportPublisher(fixture.State.Configuration.ReportsRoot);
        new RunReportWriter(latest).Snapshot(fixture.State);
        var html = File.ReadAllText(latest.EntryPath);
        Assert.Contains("Partial report", html);
        Assert.Contains("<base href=\"report_" + fixture.State.Identity.Id + "/\">", html);
        Assert.Contains("Command: run", html);
        Assert.DoesNotContain("<base", File.ReadAllText(Path.Combine(fixture.State.Report, "index.html")));
    }

    [Fact]
    public async Task ReplayReplacesLatestWithoutChangingPreviousReport()
    {
        using var fixture = new DiagnosticFixture();
        await fixture.Prepare();
        var latest = new LatestReportPublisher(fixture.State.Configuration.ReportsRoot);
        var writer = new RunReportWriter(latest);
        writer.Write(fixture.State);
        var previous = File.ReadAllText(Path.Combine(fixture.State.Report, "index.html"));
        var pair = new RunFolderAllocator().Create(fixture.State.Configuration.WorkspaceRoot,
            fixture.State.Configuration.ReportsRoot, fixture.State.Started.AddMinutes(1));
        var replay = new RunState(fixture.State.Configuration, pair, fixture.State.Deadline) { Command = "replay" };
        writer.Write(replay);
        var html = File.ReadAllText(latest.EntryPath);
        Assert.Contains("Command: replay", html);
        Assert.Contains("<title>CIMT replay — " + pair.Identity.Id, html);
        Assert.Contains("<base href=\"report_" + pair.Identity.Id + "/\">", html);
        Assert.Equal(previous, File.ReadAllText(Path.Combine(fixture.State.Report, "index.html")));
        Assert.False(File.Exists(latest.EntryPath + ".partial"));
    }

    [Fact]
    public async Task FinalReportReplacesPartialLatestPage()
    {
        using var fixture = new DiagnosticFixture();
        await fixture.Prepare();
        var latest = new LatestReportPublisher(fixture.State.Configuration.ReportsRoot);
        var writer = new RunReportWriter(latest);
        writer.Snapshot(fixture.State);
        writer.Write(fixture.State);
        Assert.DoesNotContain("Partial report", File.ReadAllText(latest.EntryPath));
        Assert.Contains("../index.html", File.ReadAllText(Path.Combine(fixture.State.Report, "index.html")));
    }

    [Theory]
    [InlineData("run")]
    [InlineData("replay")]
    public async Task EarlyExecutionErrorReplacesLatest(string command)
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
        var latest = Path.Combine(session.Outputs.ReportsRoot, "index.html");
        Assert.Contains("configuration failed", File.ReadAllText(latest));
        Assert.Contains("Command: " + command, File.ReadAllText(latest));
        Assert.Contains("<base href=\"report_" + session.Folders.Identity.Id + "/\">", File.ReadAllText(latest));
    }

    [Fact]
    public async Task ValidationDoesNotReplaceLatestExecution()
    {
        using var fixture = new DiagnosticFixture();
        await fixture.Prepare();
        var latest = new LatestReportPublisher(fixture.State.Configuration.ReportsRoot);
        new RunReportWriter(latest).Write(fixture.State);
        var previous = File.ReadAllText(latest.EntryPath);
        var session = new CommandSession(fixture.State.Started)
        {
            Command = "validate", Folders = fixture.State.Folders,
            Outputs = fixture.State.Configuration.Outputs
        };
        await new CommandReports().Write(session, "passed", "complete", 0);
        Assert.Equal(previous, File.ReadAllText(latest.EntryPath));
    }

    [Fact]
    public async Task LatestPageResolvesEvidenceInsideDatedReport()
    {
        using var fixture = new DiagnosticFixture();
        await fixture.Prepare();
        var latest = new LatestReportPublisher(fixture.State.Configuration.ReportsRoot);
        new RunReportWriter(latest).Snapshot(fixture.State);
        var entry = new Uri(latest.EntryPath);
        var html = File.ReadAllText(latest.EntryPath);
        var basePath = System.Text.RegularExpressions.Regex.Match(html, "<base href=\"([^\"]+)\">").Groups[1].Value;
        var assetBase = new Uri(entry, basePath);
        Assert.Equal(Path.Combine(fixture.State.Report, "devices", "phone", "step.png"),
            new Uri(assetBase, "devices/phone/step.png").LocalPath);
        Assert.Equal(Path.Combine(fixture.State.Report, "result.json"), new Uri(assetBase, "result.json").LocalPath);
    }

    [Fact]
    public async Task FailedLatestUpdateKeepsTheDatedReport()
    {
        using var fixture = new DiagnosticFixture();
        await fixture.Prepare();
        var latest = new LatestReportPublisher(fixture.State.Configuration.ReportsRoot);
        Directory.CreateDirectory(latest.EntryPath);
        new RunReportWriter(latest).Write(fixture.State);
        Assert.True(File.Exists(Path.Combine(fixture.State.Report, "index.html")));
        Assert.True(File.Exists(Path.Combine(fixture.State.Report, "result.json")));
    }

    [Fact]
    public async Task SymlinkCannotOverwriteAnArchivedReport()
    {
        using var fixture = new DiagnosticFixture();
        await fixture.Prepare();
        var latest = new LatestReportPublisher(fixture.State.Configuration.ReportsRoot);
        var archive = Path.Combine(fixture.State.Report, "index.html");
        File.WriteAllText(archive, "saved report");
        File.CreateSymbolicLink(latest.EntryPath + ".partial", archive);
        Assert.False(latest.Publish(fixture.State.Folders, "<meta charset=\"utf-8\">new report"));
        Assert.Equal("saved report", File.ReadAllText(archive));
    }
}
