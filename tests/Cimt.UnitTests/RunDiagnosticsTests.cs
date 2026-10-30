using System.Net;
using System.Text.Json;
using Cimt;

namespace Cimt.UnitTests;

public sealed class RunDiagnosticsTests
{
    [Fact]
    public async Task OverviewShowsActualConfigurationAndRecordedAiCount()
    {
        using var fixture = new DiagnosticFixture();
        await fixture.Prepare();
        var html = fixture.Html();
        Assert.Contains("Run overview", html);
        Assert.Contains("configuration: Release", html);
        Assert.Contains("AI inference requests</dt><dd>0", html);
        Assert.Contains("Started (UTC)", html);
        Assert.Contains("Elapsed seconds", html);
        Assert.Contains("main", html);
    }

    [Fact]
    public async Task DeviceFailureAndOtherDeviceCancellationAreExplainedSeparately()
    {
        using var fixture = new DiagnosticFixture();
        await fixture.Prepare();
        var html = fixture.Html();
        Assert.Contains("Infrastructure failure", html);
        Assert.Contains("Required mask geometry changed", html);
        Assert.Contains("Cancelled after another worker stopped", html);
        Assert.Contains("android / Android fixture / fixture", html);
        Assert.Contains("ios / iPhone fixture / fixture", html);
    }

    [Fact]
    public async Task UnfinishedWorkAppearsInStoppingReasonsAndScenarioDetails()
    {
        using var fixture = new DiagnosticFixture();
        await fixture.Prepare();
        var execution = JsonSerializer.Deserialize<JsonElement>("""
            {"devices":[{"device":{"id":"fixture","platform":"ios","name":"iPhone fixture"},
              "error":"launch timed out","stoppingReason":null,
              "scenarios":[{"target":"Debug_Generic","completion":"incomplete","verdict":"inconclusive",
                "steps":[],"crashes":[],"remaining":["Explore settings buttons","2 requirements have no decided result"]}]}]}
            """);
        var html = new RunHtmlRenderer(fixture.State.Configuration).Render(
            fixture.State, new(3, "inconclusive", "incomplete"), execution);
        Assert.Contains("Remaining or blocked work", html);
        Assert.Contains("Remaining/blocked work:", html);
        Assert.Contains("Explore settings buttons", html);
        Assert.Contains(RunDiagnostics.WorkerReasons(execution),
            reason => reason.Category == "Remaining or blocked work" && reason.Message == "Explore settings buttons");
        Assert.Contains("2 requirements have no decided result", html);
    }

    [Fact]
    public async Task MandatoryDiagnosticsRemainWhenOptionalSectionsAreDisabled()
    {
        using var fixture = new DiagnosticFixture();
        await fixture.Prepare();
        var root = Node.Merge(fixture.State.Configuration.Root,
            new Node(null, new() { ["reports"] = new(null, new()
            {
                ["sections"] = new(null, null, [new("budget", null, null, fixture.Inputs.RunFile)], fixture.Inputs.RunFile)
            }, null, fixture.Inputs.RunFile) }, null, fixture.Inputs.RunFile));
        var html = new RunHtmlRenderer(new Configuration(root)).Render(fixture.State, new(3, "inconclusive", "incomplete"), fixture.Execution);
        Assert.Contains("Run overview", html);
        Assert.Contains("Failures and stopping reasons", html);
        Assert.Contains("Chronological activity", html);
        Assert.Contains("Required mask geometry changed", html);
    }

    [Fact]
    public async Task TimelineOrdersConcurrentDeviceRecordsByTimestamp()
    {
        using var fixture = new DiagnosticFixture();
        await fixture.Prepare();
        var late = new RunActivityEntry(DateTimeOffset.Parse("2026-10-30T09:00:02Z"), "Later capture", "failed", "changed", Platform: "android");
        var early = new RunActivityEntry(late.Timestamp.AddSeconds(-1), "Earlier install", "completed", Platform: "ios", DurationSeconds: 1.25);
        await fixture.SaveActivity(late, early);
        var html = fixture.Html();
        Assert.True(html.IndexOf("Earlier install", StringComparison.Ordinal) < html.IndexOf("Later capture", StringComparison.Ordinal));
        Assert.Contains("1.250 seconds", html);
    }

    [Fact]
    public async Task TruncatedActivityKeepsEarlierRecordsAndExplainsMissingDetail()
    {
        using var fixture = new DiagnosticFixture();
        await fixture.Prepare();
        fixture.State.Activity.Record("Original capture", "started");
        await File.AppendAllTextAsync(Path.Combine(fixture.State.Report, "activity.jsonl"), "{\"timestamp\":");
        var html = fixture.Html();
        Assert.Contains("Original capture", html);
        Assert.Contains("incomplete or invalid", html);
    }

    [Fact]
    public async Task TimelineEscapesAndRedactsErrorDetails()
    {
        using var fixture = new DiagnosticFixture();
        await fixture.Prepare();
        fixture.State.Activity.Record("Capture", "failed", "<script>synthetic-credential</script>",
            error: new InvalidOperationException("synthetic-credential"));
        var html = WebUtility.HtmlDecode(fixture.Html());
        Assert.DoesNotContain("synthetic-credential", html);
        Assert.Contains("&lt;script&gt;", fixture.Html());
        Assert.Contains("InvalidOperationException", html);
    }

    [Fact]
    public async Task DiagnosticLinkCannotEscapeReportFolder()
    {
        using var fixture = new DiagnosticFixture();
        await fixture.Prepare();
        fixture.State.Activity.Record("Capture", "failed", log: "../../outside.log");
        Assert.Contains("Diagnostic link rejected", fixture.Html());
        Assert.DoesNotContain("href=\"../../outside.log", fixture.Html());
    }

    [Fact]
    public async Task WorkerFailureUsesSavedDeviceReasonWhenStderrIsEmpty()
    {
        using var fixture = new DiagnosticFixture();
        await fixture.Prepare();
        fixture.State.Environment["MOBILECLI_HOME"] = "/fixture/home";
        fixture.State.Builds.Add(new() { ["target"] = "fixture", ["platform"] = "android" });
        await File.WriteAllTextAsync(Path.Combine(fixture.State.Report, "ui-results.json"), fixture.Execution.GetRawText());
        var runner = new FakeCommandRunner { Result = new(3, "", "") };
        await new UiExecution(new RunProcess(runner), new RuntimePaths("/fixture"), new SilentProgress()).Execute(fixture.State);
        Assert.Contains(fixture.State.Errors, error => error.Contains("Required mask geometry changed"));
        Assert.DoesNotContain(fixture.State.Errors, error => error.EndsWith(": ", StringComparison.Ordinal));
        Assert.True(File.Exists(Path.Combine(fixture.State.Report, "logs/execution-worker.log")));
    }

    [Fact]
    public async Task MachineResultIncludesActivityAndSeparateStoppingReasons()
    {
        using var fixture = new DiagnosticFixture();
        await fixture.Prepare();
        fixture.State.Exit = 3;
        fixture.State.Activity.Record("Capture", "failed", "geometry changed");
        await File.WriteAllTextAsync(Path.Combine(fixture.State.Report, "ui-results.json"), fixture.Execution.GetRawText());
        Assert.Equal(3, new RunReportWriter().Write(fixture.State));
        var result = JsonSerializer.Deserialize<JsonElement>(await File.ReadAllTextAsync(Path.Combine(fixture.State.Report, "result.json")));
        Assert.Contains(result.GetProperty("activity").EnumerateArray(), item => item.GetProperty("operation").GetString() == "Capture");
        Assert.Contains(result.GetProperty("stoppingReasons").EnumerateArray(), item => item.GetProperty("category").GetString() == "Infrastructure failure");
        Assert.True(result.GetProperty("durationSeconds").GetDouble() >= 0);
    }
}

internal sealed class DiagnosticFixture : IDisposable
{
    public InputFolderFixture Inputs { get; } = new();
    public RunState State { get; private set; } = null!;
    public JsonElement Execution { get; } = JsonSerializer.Deserialize<JsonElement>("""
        {"devices":[
          {"device":{"id":"android-fixture","platform":"android","name":"Android fixture"},
           "error":"Required mask geometry changed during screenshot capture","stoppingReason":null,
           "scenarios":[{"target":"fixture","completion":"incomplete","verdict":"inconclusive","steps":[],"crashes":[]}]},
          {"device":{"id":"ios-fixture","platform":"ios","name":"iPhone fixture"},
           "error":null,"stoppingReason":"Run stopped after another worker reached a blocking condition",
           "scenarios":[{"target":"fixture","completion":"incomplete","verdict":"inconclusive","steps":[],"crashes":[]}]}],
         "budget":{"requests":0}}
        """);

    public async Task Prepare()
    {
        await Inputs.Prepare();
        var config = new Configuration(Node.Merge(Node.Read(Inputs.SharedFile), Node.Read(Inputs.RunFile)));
        var pair = new RunFolderAllocator().Create(config.WorkspaceRoot, config.ReportsRoot, DateTimeOffset.UtcNow);
        State = new(config, pair, new RunDeadline(DateTimeOffset.UtcNow.AddMinutes(1))) { Commit = "fixture-commit" };
        State.Devices.Add(new() { ["platform"] = "android", ["name"] = "Android fixture", ["id"] = "android-fixture" });
    }

    public string Html() => new RunHtmlRenderer(State.Configuration).Render(State, new(3, "inconclusive", "incomplete"), Execution);

    public Task SaveActivity(params RunActivityEntry[] entries) => File.WriteAllLinesAsync(Path.Combine(State.Report, "activity.jsonl"),
        entries.Select(entry => JsonSerializer.Serialize(entry, new JsonSerializerOptions { PropertyNamingPolicy = JsonNamingPolicy.CamelCase })));

    public void Dispose() => Inputs.Dispose();
}
