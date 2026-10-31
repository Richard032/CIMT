using System.Text.Json;
using Cimt;

namespace Cimt.UnitTests;

public sealed class PlanningReportTests
{
    [Fact]
    public async Task ReportSeparatesTestResultsFromVisitedPaths()
    {
        using var fixture = new DiagnosticFixture();
        await fixture.Prepare();
        var html = new PlanningHtmlRenderer(fixture.State.Configuration).Render(Context());
        Assert.Contains("Source-linked testing tasks", html);
        Assert.Contains("Requirement REQ-0001", html);
        Assert.Contains("Selection survives restart", html);
        Assert.Contains("1 visited", html);
        Assert.Contains("Visited paths do not prove passed tests", html);
        Assert.Contains("Last-observed configuration", html);
        Assert.Contains("Language = German", html);
    }

    [Fact]
    public async Task PlanIsVisibleEvenWhenOptionalScenarioDetailsAreDisabled()
    {
        using var fixture = new DiagnosticFixture();
        await fixture.Prepare();
        var origin = fixture.Inputs.RunFile;
        var configuration = new Configuration(Node.Merge(fixture.State.Configuration.Root, new(null, new()
        {
            ["reports"] = new(null, new() { ["sections"] = new(null, null, [new("budget", null, null, origin)], origin) }, null, origin)
        }, null, origin)));
        var html = new ScenarioHtmlRenderer(configuration, new ReportEvidence(fixture.State.Report)).Render([Context()]);
        Assert.Contains("Testing plan", html);
        Assert.Contains("Observed application map", html);
    }

    [Fact]
    public async Task OlderReportsWithoutPlansDoNotReceiveInventedPlans()
    {
        using var fixture = new DiagnosticFixture();
        await fixture.Prepare();
        var old = JsonSerializer.Deserialize<JsonElement>("""
            {"devices":[{"device":{"id":"phone","platform":"android"},"scenarios":[{"target":"fixture"}]}]}
            """);
        Assert.Equal("", new PlanningHtmlRenderer(fixture.State.Configuration).Render(Assert.Single(ReportScenario.Read(old))));
    }

    [Fact]
    public void PlanningRedactionKeepsIdentityLinksAndValidatedStatuses()
    {
        var json = new JsonTextRedactor(text => text.Replace("e", "<redacted>"));
        var value = JsonSerializer.SerializeToElement(new PlanningRedactor(json).Plan(Context().Result.GetProperty("testPlan")));
        var task = value.GetProperty("tasks")[0];
        Assert.Equal("REQ-0001", task.GetProperty("requirementId").GetString());
        Assert.Equal("pending", task.GetProperty("status").GetString());
        Assert.Contains("<redacted>", task.GetProperty("subject").GetString());
    }

    [Fact]
    public async Task PrivateTextIsRedactedAndHtmlEscapedInPlanningTables()
    {
        using var fixture = new DiagnosticFixture();
        await fixture.Prepare();
        var text = Context().Result.GetRawText().Replace("Selection survives restart", "<script>synthetic-credential</script>");
        var scenario = JsonSerializer.Deserialize<JsonElement>("{\"devices\":[{\"device\":{\"id\":\"phone\",\"platform\":\"ios\"},\"scenarios\":[" + text + "]}]}");
        var html = new PlanningHtmlRenderer(fixture.State.Configuration).Render(Assert.Single(ReportScenario.Read(scenario)));
        Assert.DoesNotContain("synthetic-credential", html);
        Assert.DoesNotContain("<script>", html);
        Assert.Contains("&lt;script&gt;", html);
    }

    private static ReportScenario Context() => Assert.Single(ReportScenario.Read(JsonSerializer.Deserialize<JsonElement>("""
        {"devices":[{"device":{"id":"phone","platform":"ios"},"scenarios":[{"target":"fixture",
        "testPlan":{"activeTaskId":0,"nextTaskId":1,"tasks":[{"id":0,"source":"requirements","requirementId":"REQ-0001",
        "subject":"Selection survives restart","expected":"German remains selected","status":"pending","result":"not tested"}]},
        "exploration":{"paths":[{"id":"path","screen":"state","control":"language","label":"Language","kind":"select",
        "scope":"in scope","attempts":1,"lastOutcome":"Observed UI changed"}],
        "applicationMap":{"states":[{"id":"state","screen":"settings","label":"Settings",
        "configuration":{"Language":{"value":"German","control":"language","observedAt":"state"}}}],
        "transitions":[{"source":"home","destination":"state","action":"tap","control":"language","verified":true,"outcome":"Observed UI changed"}],
        "configuration":{"Language":{"value":"German","control":"language","observedAt":"state"}}}}}]}]}
        """)));
}
