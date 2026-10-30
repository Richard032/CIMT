using Cimt;
using System.Text.Json;

namespace Cimt.UnitTests;

/// <summary>Verify all five statuses and their explanations remain readable in HTML.</summary>
public sealed class RequirementHtmlTests
{
    [Fact]
    public void EveryRequirementAndStatusIsRendered()
    {
        var coverage = Coverage();
        var html = new RequirementHtmlRenderer(Configuration()).Render(coverage);
        foreach (var row in coverage.Requirements)
        {
            Assert.Contains(row.Definition.Id, html);
            Assert.Contains(row.Status, html);
        }
        Assert.Contains("Source text", html);
        Assert.Contains("Instruction taking priority", html);
        Assert.Contains("Step evidence is missing", html);
    }

    [Fact]
    public void SourceAndObservationsAreEscapedAndRedacted()
    {
        var html = new RequirementHtmlRenderer(Configuration()).Render(Coverage());
        Assert.DoesNotContain("<script>", html);
        Assert.DoesNotContain("synthetic-secret", html);
        Assert.Contains("&lt;script&gt;", html);
    }

    [Fact]
    public void FilterMetadataRedactsTheDeviceDisplayName()
    {
        var summary = Coverage().Requirements[0];
        var row = summary.Results[0];
        var scope = row.Scope with { DeviceName = "Phone synthetic-secret" };
        var coverage = new RequirementCoverage([summary with { Results = [row with { Scope = scope }] }]);
        Assert.DoesNotContain("synthetic-secret", new RequirementHtmlRenderer(Configuration()).Render(coverage));
    }

    [Fact]
    public void OverriddenHistoricalObservationIsNotCountedAsAnEffectiveFailure()
    {
        var config = Configuration();
        var state = new RunState(config, TestRunFolders.At("/unused", DateTimeOffset.UtcNow), new RunDeadline(DateTimeOffset.UtcNow.AddMinutes(1)));
        var execution = JsonSerializer.Deserialize<JsonElement>("""
            {"devices":[{"device":{"name":"fixture"},"scenarios":[{
            "target":"Release","completion":"complete","verdict":"passed","crashes":[],"steps":[],
            "requirements":[{"id":"REQ-0001","status":"overridden"}],
            "checks":[{"subject":"Historical check","source":"requirements","requirementId":"REQ-0001",
            "status":"failed","expected":"Old expectation","observed":"Observed value"}]}]}]}
            """);
        var html = new RunHtmlRenderer(config).Render(state, new(0, "passed", "complete"), execution);
        Assert.Contains("Recorded checks: 1; failed: 0", html);
        Assert.Contains("Historical observation", html);
        Assert.Contains("Old expectation", html);
    }

    [Fact]
    public void AbsentRequirementsAreExplained()
    {
        Assert.Contains("No requirements were supplied", new RequirementHtmlRenderer(Configuration()).Render(new([])));
    }

    [Fact]
    public void HeadingOnlyReportShowsContextWithoutInventedStatuses()
    {
        var document = RequirementCatalogue.Parse("# Requirements <script>synthetic-secret</script>");
        var html = new RequirementHtmlRenderer(Configuration()).Render(new([]), document.Headings);
        Assert.Contains("Document headings (context)", html);
        Assert.Contains("Only document headings", html);
        Assert.Contains("Source lines 1–1", html);
        Assert.Contains("&lt;script&gt;", html);
        Assert.DoesNotContain("synthetic-secret", html);
        Assert.DoesNotContain("not tested", html);
    }

    [Fact]
    public void RequirementShowsItsSectionMeaning()
    {
        var original = Coverage();
        var row = original.Requirements[0];
        var contextual = row with { Definition = row.Definition with { HeadingContext = "## Android" } };
        var html = new RequirementHtmlRenderer(Configuration()).Render(new([contextual]));
        Assert.Contains("Section context: ## Android", html);
    }

    private static RequirementCoverage Coverage()
    {
        var statuses = new[] { "passed", "failed", "not tested", "inconclusive", "overridden" };
        var scope = new RequirementScope("Release", "android", "fixture", "Test phone", "");
        return new(statuses.Select((status, index) => new RequirementSummary(
            new("REQ-" + index, "Source text <script>synthetic-secret</script>", index + 1, index + 1), status,
            [new(scope, status, "Expected", "Observed", "Explanation", "Explore only", null, "", "Step evidence is missing")])).ToArray());
    }

    private static Configuration Configuration() => new(new Node(null, new()
    {
        ["repository"] = new(null, new()
        {
            ["branch"] = new("fixture", null, null, "/fixture/config.yaml")
        }, null, "/fixture/config.yaml"),
        ["ai-model"] = new(null, new()
        {
            ["api-key"] = new("synthetic-secret", null, null, "/fixture/config.yaml")
        }, null, "/fixture/config.yaml")
    }, null, "/fixture/config.yaml"));
}
