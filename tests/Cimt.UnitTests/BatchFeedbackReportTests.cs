using System.Text.Json;
using Cimt;

namespace Cimt.UnitTests;

public sealed class BatchFeedbackReportTests
{
    [Fact]
    public async Task CompletePathKeepsIntermediateAndUnchangedSteps()
    {
        using var fixture = new DiagnosticFixture();
        await fixture.Prepare();
        var scenario = new
        {
            target = "Debug", verdict = "inconclusive", completion = "incomplete",
            batchFeedback = new { batches = new[] { new {
                id = 0, initialObservation = "A", delivery = "supplied to AI",
                observations = new[] { new { id = "A", screen = "home" }, new { id = "B", screen = "settings" } },
                path = new[] {
                    new { action = "tap", status = "executed", target = new { @ref = "@first" }, observation = "B", uiChange = "changed" },
                    new { action = "tap", status = "executed", target = new { @ref = "@second" }, observation = "B", uiChange = "no observed change" },
                    new { action = "back", status = "executed", target = new { @ref = "@third" }, observation = "A", uiChange = "changed" }
                }
            } } }
        };
        var html = Renderer(fixture).Render(Context(scenario));
        Assert.Contains("Ordered batch results", html);
        Assert.Contains("no observed change", html);
        Assert.Contains("settings", html);
        Assert.True(html.IndexOf("@first", StringComparison.Ordinal) < html.IndexOf("@second", StringComparison.Ordinal));
        Assert.True(html.IndexOf("@second", StringComparison.Ordinal) < html.IndexOf("@third", StringComparison.Ordinal));
    }

    [Fact]
    public async Task SystemWarningsRemainVisibleWithoutOptionalReportSections()
    {
        using var fixture = new DiagnosticFixture();
        await fixture.Prepare();
        var origin = fixture.Inputs.RunFile;
        var configuration = new Configuration(Node.Merge(fixture.State.Configuration.Root, new(null, new()
        {
            ["reports"] = new(null, new() { ["sections"] = new(null, null, [new("budget", null, null, origin)], origin) }, null, origin)
        }, null, origin)));
        var scenario = new { target = "Debug", warnings = new[] { new {
            id = 0, code = "android-anr", level = "warning", timestamp = "2026-01-01T00:00:00Z", step = 2,
            device = "fixture", message = "Android ANR <script>synthetic-credential</script>"
        } } };
        var html = new ScenarioHtmlRenderer(configuration, new ReportEvidence(fixture.State.Report)).Render([Context(scenario)]);
        Assert.Contains("Operating-system warnings", html);
        Assert.Contains("Android ANR", html);
        Assert.Contains("2026-01-01T00:00:00Z", html);
        Assert.Contains("fixture", html);
        Assert.Contains("&lt;script&gt;", html);
        Assert.DoesNotContain("<script>", html);
        Assert.DoesNotContain("synthetic-credential", html);
        Assert.DoesNotContain("confirmed crash report", html);
    }

    [Fact]
    public void BatchRedactionKeepsHostIdentitiesAndScrubsWarningsAndErrors()
    {
        var input = JsonSerializer.SerializeToElement(new { devices = new[] { new {
            device = new { id = "fixture" }, scenarios = new[] { new {
                warnings = new[] { new { id = 0, code = "android-anr", level = "warning", message = "secret-warning" } },
                batchFeedback = new { batches = new[] { new {
                    id = 0, initialObservation = "screen-e", delivery = "supplied to AI",
                    initialWarnings = new[] { 0 }, warnings = Array.Empty<object>(),
                    observations = new[] { new { id = "screen-e", screen = "state-e", screenshot = "safe-e.png" } },
                    path = new[] { new { kind = "command", commandId = 1, action = "tap", status = "executed",
                        observation = "screen-e", uiChange = "no observed change", error = "secret-error", warnings = new[] { 0 },
                        target = new { @ref = "@e1" } } }
                } } }
            } }
        } } });
        var redactor = new ExecutionRedactor(new JsonTextRedactor(text => text.Replace("e", "*")));
        var output = JsonSerializer.SerializeToElement(redactor.Execution(input));
        var scenario = output.GetProperty("devices")[0].GetProperty("scenarios")[0];
        var batch = scenario.GetProperty("batchFeedback").GetProperty("batches")[0];
        Assert.Equal("screen-e", batch.GetProperty("initialObservation").GetString());
        Assert.Equal("no observed change", batch.GetProperty("path")[0].GetProperty("uiChange").GetString());
        Assert.Equal("@e1", batch.GetProperty("path")[0].GetProperty("target").GetProperty("ref").GetString());
        Assert.Equal("android-anr", scenario.GetProperty("warnings")[0].GetProperty("code").GetString());
        Assert.DoesNotContain("secret-", output.GetRawText());
    }

    [Fact]
    public async Task BatchEvidenceOutsideTheReportDoesNotBecomeALink()
    {
        using var fixture = new DiagnosticFixture();
        await fixture.Prepare();
        var scenario = new { batchFeedback = new { batches = new[] { new {
            id = 0, initialObservation = "A", observations = new[] { new { id = "A", screenshot = "../outside.png" } },
            path = new[] { new { kind = "observation", observation = "A" } }
        } } } };
        var html = Renderer(fixture).Render(Context(scenario));
        Assert.Contains("Screenshot unavailable or rejected", html);
        Assert.DoesNotContain("href=\"../outside.png", html);
    }

    private static BatchFeedbackHtmlRenderer Renderer(DiagnosticFixture fixture) =>
        new(fixture.State.Configuration, new ReportEvidence(fixture.State.Report));

    private static ReportScenario Context(object scenario)
    {
        var execution = JsonSerializer.SerializeToElement(new { devices = new[] { new {
            device = new { id = "fixture", platform = "android" }, scenarios = new[] { scenario }
        } } });
        return Assert.Single(ReportScenario.Read(execution));
    }
}
