using System.Text.Json;
using Cimt;

namespace Cimt.UnitTests;

public sealed class SwipeReportTests
{
    [Fact]
    public async Task ReportShowsRequestedTargetAndActualAdapterCoordinates()
    {
        using var fixture = new DiagnosticFixture();
        await fixture.Prepare();
        var execution = JsonSerializer.Deserialize<JsonElement>("""
            {"devices":[{"device":{"id":"phone","platform":"ios"},"scenarios":[{"target":"Debug","steps":[
              {"step":1,"action":{"action":"swipe","ref":"@wheel","direction":"up","distance":40},
               "adapterCall":{"tool":"mobile_swipe_on_screen","status":"completed",
                 "arguments":{"device":"phone","direction":"up","x":201,"y":765.5,"distance":40}}}]}]}]}
            """);
        var html = new StepHtmlRenderer(fixture.State.Configuration, new ReportEvidence(fixture.State.Report))
            .Render(Assert.Single(ReportScenario.Read(execution)));
        Assert.Contains("Requested action", html);
        Assert.Contains("Adapter call attempted", html);
        Assert.Contains("@wheel", html);
        Assert.Contains("mobile_swipe_on_screen", html);
        Assert.Contains("765.5", html);
        Assert.DoesNotContain("2296.5", html);
    }

    [Fact]
    public async Task HistoricalStringSwipeActionDoesNotRequireStructuredArguments()
    {
        using var fixture = new DiagnosticFixture();
        await fixture.Prepare();
        var execution = JsonSerializer.Deserialize<JsonElement>("""
            {"devices":[{"device":{"id":"phone","platform":"ios"},"scenarios":[{"target":"Debug","steps":[
              {"step":1,"action":"swipe"}]}]}]}
            """);
        var html = new StepHtmlRenderer(fixture.State.Configuration, new ReportEvidence(fixture.State.Report))
            .Render(Assert.Single(ReportScenario.Read(execution)));
        Assert.Contains("swipe", html);
    }

    [Fact]
    public void AdapterProtocolAndNumbersSurviveSecretRedaction()
    {
        var execution = JsonSerializer.Deserialize<JsonElement>("""
            {"devices":[{"device":{"id":"phone","platform":"ios"},"scenarios":[{"target":"Debug","steps":[
              {"step":1,"action":{"action":"swipe","ref":"@wheel","distance":40},
               "adapterCall":{"tool":"mobile_swipe_on_screen","status":"failed",
                 "arguments":{"device":"phone","direction":"up","x":201,"y":765.5,"distance":40},
                 "error":"synthetic-secret"}}]}]}]}
            """);
        var redactor = new ExecutionRedactor(new JsonTextRedactor(value => value.Replace("1", "masked")
            .Replace("synthetic-secret", "masked")));
        var safe = JsonSerializer.SerializeToElement(redactor.Execution(execution));
        var step = safe.GetProperty("devices")[0].GetProperty("scenarios")[0].GetProperty("steps")[0];
        var call = step.GetProperty("adapterCall");
        Assert.Equal("mobile_swipe_on_screen", call.GetProperty("tool").GetString());
        Assert.Equal("failed", call.GetProperty("status").GetString());
        Assert.Equal(201, call.GetProperty("arguments").GetProperty("x").GetInt32());
        Assert.Equal(40, call.GetProperty("arguments").GetProperty("distance").GetInt32());
        Assert.DoesNotContain("synthetic-secret", safe.GetRawText());
    }
}
