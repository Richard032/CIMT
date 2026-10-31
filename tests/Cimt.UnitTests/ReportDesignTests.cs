using System.Text.Json;
using Cimt;

namespace Cimt.UnitTests;

/// <summary>Exercise report navigation and evidence without devices or provider access.</summary>
public sealed class ReportDesignTests
{
    [Fact]
    public async Task InterruptedStepShowsItsStoppingReasonWithoutAnActionError()
    {
        using var fixture = new DiagnosticFixture();
        await fixture.Prepare();
        var execution = JsonSerializer.Deserialize<JsonElement>("""
            {"devices":[{"device":{"id":"phone","platform":"ios"},"scenarios":[{"target":"fixture","steps":[
            {"step":0,"action":"tap","stoppingReason":"User interrupted execution; partial observations were retained"}]}]}]}
            """);
        var html = new StepHtmlRenderer(fixture.State.Configuration, new ReportEvidence(fixture.State.Report))
            .Render(Assert.Single(ReportScenario.Read(execution)));
        Assert.Contains("data-status=\"stopped\"", html);
        Assert.Contains("Stopping reason", html);
        Assert.Contains("User interrupted execution", html);
        Assert.DoesNotContain("Action error", html);
    }

    [Fact]
    public async Task InterruptedStepKeepsItsEarlierCrashClassification()
    {
        using var fixture = new DiagnosticFixture();
        await fixture.Prepare();
        var execution = JsonSerializer.Deserialize<JsonElement>("""
            {"devices":[{"device":{"id":"phone","platform":"ios"},"scenarios":[{"target":"fixture","steps":[
            {"step":0,"action":"tap","crash":"confirmed crash report","stoppingReason":"User interrupted execution"}]}]}]}
            """);
        var html = new StepHtmlRenderer(fixture.State.Configuration, new ReportEvidence(fixture.State.Report))
            .Render(Assert.Single(ReportScenario.Read(execution)));
        Assert.Contains("data-status=\"confirmed crash report\"", html);
        Assert.Contains("User interrupted execution", html);
    }

    [Fact]
    public async Task ResultsAppearBeforeTheJournalAndBothPlatformsAreInTheOverview()
    {
        using var fixture = new DiagnosticFixture();
        await fixture.Prepare();
        var html = Render(fixture);
        var overview = html[..html.IndexOf("<section id=\"findings\"", StringComparison.Ordinal)];
        Assert.Contains("Android phone", overview);
        Assert.Contains("iPhone", overview);
        Assert.Contains("1 confirmed / 0 suspected", overview);
        Assert.Contains("0 confirmed / 1 suspected", overview);
        Assert.True(html.IndexOf("<section id=\"devices\"", StringComparison.Ordinal) < html.IndexOf("<section id=\"activity\"", StringComparison.Ordinal));
    }

    [Fact]
    public async Task ExpectedTargetWithoutABuildRemainsInTheOverview()
    {
        using var fixture = new DiagnosticFixture();
        await fixture.Prepare();
        var rows = ReportDeviceSummary.Create(fixture.State, []);
        var row = Assert.Single(rows);
        Assert.Equal("not tested", row.Verdict);
        Assert.Equal("incomplete", row.Completion);
        Assert.Contains("No installable build", row.Stop);
        Assert.Null(row.Anchor);
    }

    [Fact]
    public async Task BuiltTargetThatNeverStartedHasAnExplicitStopReason()
    {
        using var fixture = new DiagnosticFixture();
        await fixture.Prepare();
        fixture.State.Builds.Add(new() { ["platform"] = "android", ["target"] = "fixture" });
        Assert.Contains("No scenario started", Assert.Single(ReportDeviceSummary.Create(fixture.State, [])).Stop);
    }

    [Fact]
    public async Task ABlockedDeviceKeepsItsErrorBeforeAnyScenarioStarts()
    {
        using var fixture = new DiagnosticFixture();
        await fixture.Prepare();
        var execution = JsonSerializer.Deserialize<JsonElement>("""
            {"devices":[{"device":{"id":"android-fixture","platform":"android"},"error":"Phone disconnected","scenarios":[]}]}
            """);
        var row = Assert.Single(ReportDeviceSummary.Create(fixture.State, [], execution));
        Assert.Equal("Phone disconnected", row.Stop);
        Assert.Equal("not tested", row.Verdict);
    }

    [Fact]
    public async Task FailedRequirementObservationIsReadableEvenWithoutACheckRecord()
    {
        using var fixture = new DiagnosticFixture();
        await fixture.Prepare();
        var execution = JsonSerializer.Deserialize<JsonElement>("""
            {"devices":[{"device":{"id":"phone","platform":"ios"},"scenarios":[{"target":"fixture","requirements":[
            {"id":"REQ-9","status":"failed","expected":"Saved selection","observed":"Selection was lost"}]}]}]}
            """);
        var html = new FindingHtmlRenderer(fixture.State.Configuration, new ReportEvidence(fixture.State.Report)).Render(ReportScenario.Read(execution));
        Assert.Contains("REQ-9", html);
        Assert.Contains("Saved selection", html);
        Assert.Contains("Selection was lost", html);
    }

    [Fact]
    public async Task ExactStepZeroHasDistinctLinksOnDifferentDevices()
    {
        using var fixture = new DiagnosticFixture();
        await fixture.Prepare();
        var contexts = ReportScenario.Read(Execution());
        Assert.NotEqual(contexts[0].FindStep("0")!.Value.Anchor, contexts[1].FindStep("0")!.Value.Anchor);
        var html = Render(fixture);
        foreach (var context in contexts)
        {
            var anchor = context.FindStep("0")!.Value.Anchor;
            Assert.Contains("id=\"" + anchor + "\"", html);
            Assert.Contains("href=\"#" + anchor + "\"", html);
        }
        Assert.Contains("Step 0", html);
    }

    [Fact]
    public void RepeatedScenariosAndDuplicateStepIdsNeverCreateAnAmbiguousLink()
    {
        var value = JsonSerializer.Deserialize<JsonElement>("""
            {"devices":[{"device":{"id":"phone","platform":"ios"},"scenarios":[
            {"target":"A","steps":[{"step":0},{"step":0}]},{"target":"A","steps":[{"step":0}]}]}]}
            """);
        var contexts = ReportScenario.Read(value);
        Assert.NotEqual(contexts[0].Anchor, contexts[1].Anchor);
        Assert.Null(contexts[0].FindStep("0"));
        Assert.NotEqual(contexts[0].StepAnchor(0), contexts[0].StepAnchor(1));
    }

    [Fact]
    public void ASecretMatchingAFixedCrashClassificationCannotChangeItsCategory()
    {
        var redactor = new ExecutionRedactor(new JsonTextRedactor(value => value.Replace("confirmed crash report", "<redacted>")));
        var safe = JsonSerializer.SerializeToElement(redactor.Execution(Execution()));
        Assert.Equal(1, ReportScenario.Read(safe)[0].ConfirmedCrashes);
        Assert.Equal(0, ReportScenario.Read(safe)[0].SuspectedTerminations);
    }

    [Fact]
    public async Task MandatoryFailuresRemainReadableWithOptionalDetailsDisabled()
    {
        using var fixture = new DiagnosticFixture();
        await fixture.Prepare();
        var origin = fixture.Inputs.RunFile;
        var config = new Configuration(Node.Merge(fixture.State.Configuration.Root, new(null, new()
        {
            ["reports"] = new(null, new() { ["sections"] = new(null, null, [new("budget", null, null, origin)], origin) }, null, origin)
        }, null, origin)));
        var html = new RunHtmlRenderer(config).Render(fixture.State, new(1, "failed", "incomplete"), Execution());
        Assert.Contains("Expected persisted value", html);
        Assert.Contains("Observed missing value", html);
        Assert.Contains("Recorded step 0", html);
        Assert.Contains("confirmed crash report", html);
    }

    [Fact]
    public async Task ScreenshotHasContextAndAnOfflineViewerFallback()
    {
        using var fixture = new DiagnosticFixture();
        await fixture.Prepare();
        Directory.CreateDirectory(Path.Combine(fixture.State.Report, "devices/android"));
        File.WriteAllBytes(Path.Combine(fixture.State.Report, "devices/android/step.png"), [137, 80, 78, 71]);
        var html = Render(fixture);
        Assert.Contains("src=\"devices/android/step.png\"", html);
        Assert.Contains("alt=\"android / Android phone / android / fixture / step 0\"", html);
        Assert.Contains("data-gallery=", html);
        Assert.Contains("id=\"evidence-viewer\"", html);
        Assert.Contains("href=\"devices/android/step.png\"", html);
        Assert.DoesNotContain("src=\"http", html);
    }

    [Fact]
    public async Task MissingScreenshotIsExplainedWithoutABrokenThumbnail()
    {
        using var fixture = new DiagnosticFixture();
        await fixture.Prepare();
        var html = Render(fixture);
        Assert.Contains("Screenshot unavailable or rejected", html);
        Assert.DoesNotContain("src=\"devices/android/step.png\"", html);
    }

    [Fact]
    public async Task NonImageFileCannotBecomeAScreenshotLink()
    {
        using var fixture = new DiagnosticFixture();
        await fixture.Prepare();
        File.WriteAllText(Path.Combine(fixture.State.Report, "page.html"), "<script>alert(1)</script>");
        var html = new ReportEvidence(fixture.State.Report).ImageLink("page.html", "Unexpected file", "fixture");
        Assert.Contains("rejected", html);
        Assert.DoesNotContain("href=", html);
    }

    [Theory]
    [InlineData("../outside.png")]
    [InlineData("https://example.com/image.png")]
    [InlineData("javascript:alert(1)")]
    [InlineData("/private/tmp/image.png")]
    public async Task EvidenceCannotLeaveItsReport(string path)
    {
        using var fixture = new DiagnosticFixture();
        await fixture.Prepare();
        Assert.Null(new ReportEvidence(fixture.State.Report).RelativePath(path));
    }

    [Fact]
    public async Task EvidenceSymlinkCannotExposeAFileOutsideTheReport()
    {
        using var fixture = new DiagnosticFixture();
        await fixture.Prepare();
        var outside = Path.Combine(Path.GetDirectoryName(fixture.State.Report)!, "outside.png");
        File.WriteAllText(outside, "private fixture");
        File.CreateSymbolicLink(Path.Combine(fixture.State.Report, "alias.png"), outside);
        Assert.Null(new ReportEvidence(fixture.State.Report).RelativePath("alias.png"));
    }

    [Fact]
    public async Task RequirementStepLinkUsesTheMatchingDevice()
    {
        using var fixture = new DiagnosticFixture();
        await fixture.Prepare();
        var scope = new RequirementScope("fixture", "android", "android", "Android phone", "");
        var assessment = new RequirementAssessment(scope, "failed", "Expected", "Observed", "Reason", "", 0, "", "");
        var coverage = new RequirementCoverage([new(new("REQ-1", "Persist value", 1, 1), "failed", [assessment])]);
        var contexts = ReportScenario.Read(Execution());
        var html = new RequirementHtmlRenderer(fixture.State.Configuration).Render(coverage, scenarios: contexts);
        Assert.Contains("href=\"#" + contexts[0].FindStep("0")!.Value.Anchor + "\"", html);
        Assert.DoesNotContain("href=\"#" + contexts[1].FindStep("0")!.Value.Anchor + "\"", html);
    }

    [Fact]
    public async Task PartialReportsRemainExplicitAndKeepAllFiveSections()
    {
        using var fixture = new DiagnosticFixture();
        await fixture.Prepare();
        var html = new RunHtmlRenderer(fixture.State.Configuration).Render(fixture.State, new(2, "failed", "incomplete"), Execution(), inProgress: true);
        Assert.Contains("Partial report", html);
        Assert.Contains("Snapshot updated (UTC)", html);
        foreach (var section in new[] { "overview", "findings", "devices", "requirements", "activity" })
            Assert.Contains("href=\"#" + section + "\"", html);
        Assert.Contains("name=\"viewport\"", html);
        Assert.Contains("<main", html);
    }

    private static string Render(DiagnosticFixture fixture) => new RunHtmlRenderer(fixture.State.Configuration)
        .Render(fixture.State, new(1, "failed", "incomplete"), Execution());

    private static JsonElement Execution() => JsonSerializer.Deserialize<JsonElement>("""
        {"devices":[
          {"device":{"id":"android","platform":"android","name":"Android phone"},"scenarios":[{
            "target":"fixture","verdict":"failed","completion":"incomplete",
            "crashes":[{"step":0,"kind":"confirmed crash report","point":"Bluetooth","matchingAttempt":1}],
            "steps":[{"step":0,"action":{"action":"tap"},"controlLabel":"Bluetooth","screenshot":"devices/android/step.png"}],
            "checks":[{"step":0,"source":"instructions","status":"failed","subject":"Persist value",
              "expected":"Expected persisted value","observed":"Observed missing value"}]}]},
          {"device":{"id":"ios","platform":"ios","name":"iPhone"},"scenarios":[{
            "target":"fixture","verdict":"failed","completion":"incomplete",
            "crashes":[{"step":0,"kind":"unexpected termination / suspected crash"}],"steps":[{"step":0,"action":"tap"}]}]}]}
        """);
}
