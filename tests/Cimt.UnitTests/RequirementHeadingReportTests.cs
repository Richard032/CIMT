using Cimt;
using System.Text.Json;

namespace Cimt.UnitTests;

/// <summary>Check retained heading context through the final report writer.</summary>
public sealed class RequirementHeadingReportTests
{
    [Fact]
    public void HeadingsSurviveWhenOptionalInputDetailsAreHidden()
    {
        using var folder = new TestDirectory();
        var state = State(folder.Path);
        new RunReportWriter().Write(state);
        var html = File.ReadAllText(Path.Combine(folder.Path, "index.html"));
        Assert.Contains("Document headings (context)", html);
        Assert.Contains("# Requirements", html);
        Assert.Contains("Catalogue items: 1", html);
        Assert.DoesNotContain("Testing instructions and requirements", html);
    }

    [Fact]
    public void FinalJsonSeparatesHeadingsFromRequirementResults()
    {
        using var folder = new TestDirectory();
        var state = State(folder.Path);
        new RunReportWriter().Write(state);
        using var json = JsonDocument.Parse(File.ReadAllText(Path.Combine(folder.Path, "result.json")));
        var heading = Assert.Single(json.RootElement.GetProperty("requirementHeadings").EnumerateArray());
        Assert.Equal("# Requirements", heading.GetProperty("text").GetString());
        Assert.False(heading.TryGetProperty("status", out _));
        var requirement = Assert.Single(json.RootElement.GetProperty("requirementCoverage")
            .GetProperty("requirements").EnumerateArray());
        Assert.Equal("REQ-0001", requirement.GetProperty("definition").GetProperty("id").GetString());
    }

    private static RunState State(string report)
    {
        const string origin = "/fixture/config.yaml";
        var config = new Configuration(new Node(null, new()
        {
            ["repository"] = new(null, new() { ["branch"] = new("fixture", null, null, origin) }, null, origin),
            ["build"] = new(null, new() { ["targets"] = new(null, null, [], origin) }, null, origin),
            ["reports"] = new(null, new() { ["sections"] = new(null, null, [], origin) }, null, origin)
        }, null, origin));
        var document = RequirementCatalogue.Parse("# Requirements\nSave works.");
        return new(config, TestRunFolders.At(report, DateTimeOffset.UtcNow),
            new RunDeadline(DateTimeOffset.UtcNow.AddMinutes(1)))
        {
            Requirements = document.Items,
            RequirementHeadings = document.Headings
        };
    }
}
