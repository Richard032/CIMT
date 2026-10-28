using System.Text.Json;
using Cimt;

namespace Cimt.UnitTests;

/// <summary>Report choices can hide details, but must keep failure totals visible.</summary>
public sealed class CheckReportTests
{
    [Fact]
    public void FunctionalFindingShowsExpectedAndObservedBehavior()
    {
        var html = Render("findings");
        Assert.Contains("Recorded checks: 1; failed: 1", html);
        Assert.Contains("Expected saved value", html);
        Assert.Contains("Observed missing value", html);
        Assert.Contains("check-0001.png", html);
        Assert.DoesNotContain("<unsafe>", html);
        Assert.Contains("&lt;unsafe&gt;", html);
    }

    [Fact]
    public void SummaryKeepsFailureCountWhenDetailsAreDisabled()
    {
        var html = Render("budget");
        Assert.Contains("Recorded checks: 1; failed: 1", html);
        Assert.DoesNotContain("Expected saved value", html);
        Assert.Contains("Verdict: failed", html);
    }

    [Fact]
    public void RequirementsSectionShowsRecordedCheckDetails()
    {
        Assert.Contains("Observed missing value", Render("requirements"));
    }

    private static string Render(string section)
    {
        const string origin = "/fixture/config.yaml";
        var root = new Node(null, new()
        {
            ["repository"] = new(null, new()
            {
                ["branch"] = new("main", null, null, origin)
            }, null, origin),
            ["reports"] = new(null, new()
            {
                ["sections"] = new(null, null, [new(section, null, null, origin)], origin)
            }, null, origin)
        }, null, origin);
        var state = new RunState(new Configuration(root), "/unused", DateTimeOffset.UnixEpoch,
            new RunDeadline(DateTimeOffset.UtcNow.AddMinutes(1)));
        var data = JsonSerializer.Deserialize<JsonElement>("""
            {"devices":[{"device":{"name":"fixture"},"scenarios":[{
              "target":"Release","verdict":"failed","completion":"complete","crashes":[],
              "checks":[{"subject":"Save <unsafe>","source":"instructions","status":"failed",
              "expected":"Expected saved value","observed":"Observed missing value","reason":"",
              "screenshot":"check-0001.png"}]}]}]}
            """);
        return new RunHtmlRenderer(state.Configuration).Render(state, new(1, "failed", "complete"), data);
    }
}
