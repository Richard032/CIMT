using System.Text.Json;
using Cimt;

namespace Cimt.UnitTests;

/// <summary>Outcome policy tests use report data only, without tools or files.</summary>
public sealed class OutcomeTests
{
    [Theory]
    [InlineData(0, 1)]
    [InlineData(2, 1)]
    [InlineData(3, 3)]
    public void FunctionalFailureRemainsVisible(int exit, int expectedExit)
    {
        var outcome = RunOutcomePolicy.Evaluate(exit, Execution("failed", "complete"));
        Assert.Equal(expectedExit, outcome.ExitCode);
        Assert.Equal("failed", outcome.Verdict);
    }

    [Fact]
    public void FunctionalFailureSurvivesIncompleteExploration()
    {
        Assert.Equal(new RunOutcome(1, "failed", "incomplete"),
            RunOutcomePolicy.Evaluate(2, Execution("failed", "incomplete")));
    }

    [Fact]
    public void ExplicitPassWithCompleteExplorationCanPass()
    {
        Assert.Equal(new RunOutcome(0, "passed", "complete"),
            RunOutcomePolicy.Evaluate(0, Execution("passed", "complete")));
    }

    [Fact]
    public void InconclusiveScenarioCannotPass()
    {
        Assert.Equal(new RunOutcome(2, "inconclusive", "incomplete"),
            RunOutcomePolicy.Evaluate(0, Execution("inconclusive", "complete")));
    }

    [Theory]
    [InlineData("phone-a", "first", 0)]
    [InlineData("phone-a", "second", 2)]
    [InlineData("phone-b", "first", 2)]
    public void EveryExpectedDeviceAndTargetNeedsAnObjectiveEvenWithoutRequirements(string device, string target, int exit)
    {
        var execution = JsonSerializer.Deserialize<JsonElement>("""
            {"devices":[{"device":{"id":"phone-a","platform":"android"},
            "scenarios":[{"target":"first","verdict":"passed","completion":"complete","crashes":[]}]}]}
            """);
        var scopes = new[] { new RequirementScope(target, "android", device, device, "") };
        Assert.Equal(exit, RunOutcomePolicy.Evaluate(0, execution, expectedScopes: scopes).ExitCode);
    }

    [Fact]
    public void InvalidCheckStatusCannotBeHiddenByAPassedScenario()
    {
        var execution = JsonSerializer.Deserialize<JsonElement>("""
            {"devices":[{"scenarios":[{"verdict":"passed","completion":"complete","crashes":[],
            "checks":[{"status":"<redacted>"}]}]}]}
            """);
        Assert.Equal(new RunOutcome(2, "inconclusive", "incomplete"), RunOutcomePolicy.Evaluate(0, execution));
    }

    [Theory]
    [InlineData("{\"devices\":[]}")]
    [InlineData("{\"devices\":[{\"scenarios\":[]}]}")]
    [InlineData("{\"devices\":[{\"scenarios\":[{\"crashes\":[],\"completion\":\"complete\"}]}]}")]
    public void MissingEvidenceCannotPass(string json)
    {
        var outcome = RunOutcomePolicy.Evaluate(0, JsonSerializer.Deserialize<JsonElement>(json));
        Assert.Equal("inconclusive", outcome.Verdict);
        Assert.Equal(2, outcome.ExitCode);
    }

    private static JsonElement Execution(string verdict, string completion) => JsonSerializer.SerializeToElement(new
    {
        devices = new[] { new { scenarios = new[] { new { verdict, completion, crashes = Array.Empty<object>() } } } }
    });
}
