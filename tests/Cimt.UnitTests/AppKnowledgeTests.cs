using System.Text.Json;
using Cimt;

namespace Cimt.UnitTests;

public sealed class AppKnowledgeTests
{
    [Fact]
    public void MissingInstallationSettingsLeaveKnowledgeDisabled()
    {
        using var temporary = new TestDirectory();
        Assert.Null(new RuntimePaths(temporary.Path).AppKnowledgeSettings);
    }

    [Fact]
    public void InstallationSettingsPreserveTheConfiguredSharedBranch()
    {
        using var temporary = new TestDirectory();
        Directory.CreateDirectory(Path.Combine(temporary.Path, "state"));
        File.WriteAllText(Path.Combine(temporary.Path, "state/app-knowledge-settings.json"),
            JsonSerializer.Serialize(new { repository = temporary.Path, remote = "origin", baseBranch = "feature/shared" }));
        var settings = new RuntimePaths(temporary.Path).AppKnowledgeSettings!.Value;
        Assert.Equal("feature/shared", settings.GetProperty("baseBranch").GetString());
        Assert.Equal(temporary.Path, settings.GetProperty("repository").GetString());
    }

    [Theory]
    [InlineData("not json")]
    [InlineData("null")]
    [InlineData("{\"repository\":\"relative/path\",\"remote\":\"origin\",\"baseBranch\":\"feature/shared\"}")]
    [InlineData("{\"repository\":123}")]
    public void InvalidInstallationSettingsGiveAConfigurationError(string content)
    {
        using var temporary = new TestDirectory();
        Directory.CreateDirectory(Path.Combine(temporary.Path, "state"));
        File.WriteAllText(Path.Combine(temporary.Path, "state/app-knowledge-settings.json"), content);
        Assert.Throws<ConfigurationException>(() => new RuntimePaths(temporary.Path).AppKnowledgeSettings);
    }

    [Fact]
    public async Task LearnedGuideIsEscapedAndRedactedInTheReport()
    {
        using var fixture = new DiagnosticFixture();
        await fixture.Prepare();
        var execution = JsonSerializer.SerializeToElement(new
        {
            devices = new[] { new { device = new { id = "fixture", platform = "ios" }, scenarios = new[] { new
            {
                target = "Debug", testPlan = new { tasks = Array.Empty<object>() },
                appKnowledgeProposal = new { appId = "org.example.app", platform = "ios", guide = "Use <Settings> synthetic-credential" }
            } } } }
        });
        var html = new PlanningHtmlRenderer(fixture.State.Configuration).Render(Assert.Single(ReportScenario.Read(execution)));
        Assert.Contains("AI-learned knowledge proposal", html);
        Assert.Contains("&lt;Settings&gt;", html);
        Assert.DoesNotContain("synthetic-credential", html);
        Assert.Contains("Current testing instructions take priority", html);
    }

    [Fact]
    public async Task PublicationFailureIsVisibleWithoutChangingTheTestOutcome()
    {
        using var fixture = new DiagnosticFixture();
        await fixture.Prepare();
        var execution = JsonSerializer.SerializeToElement(new
        {
            devices = Array.Empty<object>(),
            appKnowledgePublication = new { status = "branch-pushed", error = "HTTP 403 synthetic-credential", branch = "knowledge/new" }
        });
        var html = new RunHtmlRenderer(fixture.State.Configuration).Render(fixture.State, new(3, "inconclusive", "incomplete"), execution);
        Assert.Contains("Application knowledge publication", html);
        Assert.Contains("branch-pushed", html);
        Assert.Contains("HTTP 403", html);
        Assert.DoesNotContain("synthetic-credential", html);
        Assert.Contains("Exit: 3", html);
    }

    [Theory]
    [InlineData("https://github.com/example/CIMT/pull/7", true)]
    [InlineData("javascript:alert(1)", false)]
    [InlineData("https://github.com.evil.invalid/example/pull/7", false)]
    public async Task ReportLinksOnlyToGithubPullRequests(string url, bool linked)
    {
        using var fixture = new DiagnosticFixture();
        await fixture.Prepare();
        var execution = JsonSerializer.SerializeToElement(new
        {
            devices = Array.Empty<object>(), appKnowledgePublication = new { status = "pr-created", url }
        });
        var html = new RunHtmlRenderer(fixture.State.Configuration).Render(fixture.State, new(3, "inconclusive", "incomplete"), execution);
        Assert.Equal(linked, html.Contains(">Knowledge pull request</a>"));
    }
}
