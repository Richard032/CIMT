using System.Text.Json;
using Cimt;

namespace Cimt.UnitTests;

public sealed class PlanningReportTests
{
    [Fact]
    public async Task AiRepliesAreVisibleEscapedAndRedactedWithoutFormatJudgments()
    {
        using var fixture = new DiagnosticFixture();
        await fixture.Prepare();
        var context = Context();
        context = context with { Result = JsonSerializer.SerializeToElement(new
        {
            testPlan = context.Result.GetProperty("testPlan"),
            decisions = new[] { new { id = 0, response = new
            {
                action = "note", modelResponse = "<script>synthetic-credential</script>",
                resourceFeedback = "No device command dispatched"
            } } }
        }) };
        var html = new PlanningHtmlRenderer(fixture.State.Configuration).Render(context);
        Assert.Contains("AI replies and resource feedback", html);
        Assert.Contains("No device command dispatched", html);
        Assert.Contains("&lt;script&gt;", html);
        Assert.DoesNotContain("<script>", html);
        Assert.DoesNotContain("synthetic-credential", html);
        Assert.DoesNotContain("rejected", html);
    }

    [Fact]
    public async Task QueueReportDistinguishesExecutedCommandsFromUnperformedPlans()
    {
        using var fixture = new DiagnosticFixture();
        await fixture.Prepare();
        var context = Context();
        context = context with { Result = JsonSerializer.SerializeToElement(new
        {
            testPlan = context.Result.GetProperty("testPlan"),
            commandQueue = new { commands = new object[] {
                new { id = 0, batchId = 0, position = 0, status = "executed", step = 1,
                    reason = "Observed UI changed", response = new { action = "tap", modelResponse = "<script>synthetic-credential</script>" } },
                new { id = 1, batchId = 0, position = 1, status = "not executed",
                    reason = "User interrupted", response = new { action = "back" } }
            } }
        }) };
        var html = new PlanningHtmlRenderer(fixture.State.Configuration).Render(context);
        Assert.Contains("AI command queue", html);
        Assert.Contains("not performed actions", html);
        Assert.Contains("not executed", html);
        Assert.Contains("User interrupted", html);
        Assert.Contains("&lt;script&gt;", html);
        Assert.DoesNotContain("<script>", html);
        Assert.DoesNotContain("synthetic-credential", html);
    }

    [Fact]
    public void QueueRedactionPreservesExecutionIdentityAndScrubsAiText()
    {
        var input = JsonSerializer.SerializeToElement(new { devices = new[] { new {
            device = new { id = "phone", platform = "android" }, scenarios = new[] { new {
                commandQueue = new { commands = new[] { new {
                    id = 2, batchId = 1, position = 0, status = "not executed", reason = "secret text",
                    response = new { action = "tap", @ref = "@e1", modelResponse = "secret reply" }
                } } }
            } }
        } } });
        var redactor = new ExecutionRedactor(new JsonTextRedactor(text => text.Replace("e", "*")));
        var output = JsonSerializer.SerializeToElement(redactor.Execution(input));
        var command = output.GetProperty("devices")[0].GetProperty("scenarios")[0]
            .GetProperty("commandQueue").GetProperty("commands")[0];
        Assert.Equal(2, command.GetProperty("id").GetInt32());
        Assert.Equal("not executed", command.GetProperty("status").GetString());
        Assert.Equal("@e1", command.GetProperty("response").GetProperty("ref").GetString());
        Assert.DoesNotContain("secret", command.GetProperty("reason").GetString());
    }

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

    [Fact]
    public async Task ReportShowsAiContextAndRecoveryWithoutExposingPrivateText()
    {
        using var fixture = new DiagnosticFixture();
        await fixture.Prepare();
        var context = Context();
        context = context with { Result = JsonSerializer.SerializeToElement(new
        {
            testPlan = context.Result.GetProperty("testPlan"),
            exploration = context.Result.GetProperty("exploration"),
            contextSelection = new { summary = "<script>synthetic-credential</script>", includeAll = new[] { "actions" },
                records = new[] { new { collection = "tasks", id = "0" } } },
            recoveries = new[] { new { id = 0, step = 3, kind = "repetition", reason = "Repeated menu navigation",
                decision = "replan", explanation = "Retrieve earlier outcomes and try another path", status = "continued" } }
        }) };
        var html = new PlanningHtmlRenderer(fixture.State.Configuration).Render(context);
        Assert.Contains("AI-selected working context", html);
        Assert.Contains("AI-directed recovery", html);
        Assert.Contains("Retrieve earlier outcomes", html);
        Assert.Contains("&lt;script&gt;", html);
        Assert.DoesNotContain("synthetic-credential", html);
        Assert.DoesNotContain("<script>", html);
    }

    [Fact]
    public void ContextRedactionPreservesAddressesAndRemovesSummarySecrets()
    {
        var redactor = new PlanningRedactor(new JsonTextRedactor(text => text.Replace("e", "<redacted>")));
        var value = JsonSerializer.SerializeToElement(redactor.ContextSelection(JsonSerializer.SerializeToElement(new
        {
            summary = "Remember the failure", includeAll = new[] { "states" },
            records = new[] { new { collection = "states", id = "state-e" } }
        })));
        Assert.Contains("<redacted>", value.GetProperty("summary").GetString());
        Assert.Equal("states", value.GetProperty("includeAll")[0].GetString());
        Assert.Equal("state-e", value.GetProperty("records")[0].GetProperty("id").GetString());
    }

    [Fact]
    public async Task BudgetReportShowsCacheDetailsAndRecoveryRequestUsage()
    {
        using var fixture = new DiagnosticFixture();
        await fixture.Prepare();
        var execution = JsonSerializer.SerializeToElement(new { budget = new
        {
            inputTokens = 100, outputTokens = 20, cachedInputTokens = 80, cacheUsageRequests = 1,
            requestUsage = new[] { new { kind = "recovery", status = "recorded", inputTokens = 100,
                outputTokens = 20, cachedInputTokens = 80 } }
        }});
        var html = new RunDiagnosticsRenderer(fixture.State.Configuration).Budget(execution);
        Assert.Contains("Recorded cached input tokens", html);
        Assert.Contains("AI request token usage", html);
        Assert.Contains("recovery", html);
        Assert.Contains("80", html);
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
