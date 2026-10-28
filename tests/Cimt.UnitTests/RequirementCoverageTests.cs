using System.Text.Json;
using Cimt;

namespace Cimt.UnitTests;

/// <summary>Each test changes one requirement or execution scope.</summary>
public sealed class RequirementCoverageTests
{
    private static readonly RequirementDefinition Definition = new("REQ-0001", "Value stays saved.", 1, 1);
    private static readonly RequirementScope Scope = new("Release", "android", "phone-a", "Phone A", "Build unavailable.");

    [Theory]
    [InlineData("passed", "passed", "passed")]
    [InlineData("passed", "failed", "failed")]
    [InlineData("failed", "not tested", "failed")]
    [InlineData("passed", "not tested", "inconclusive")]
    [InlineData("not tested", "not tested", "not tested")]
    [InlineData("overridden", "overridden", "overridden")]
    [InlineData("passed", "overridden", "passed")]
    public void ScopedStatusesUseConservativePrecedence(string first, string second, string expected)
    {
        Assert.Equal(expected, RequirementStatus.Combine([first, second]));
    }

    [Fact]
    public void MissingExecutionStillListsEveryRequirement()
    {
        var definitions = new[] { Definition, new RequirementDefinition("REQ-0002", "Back works.", 2, 2) };
        var coverage = RequirementReportBuilder.Build(definitions, [Scope], null, "");
        Assert.Equal(2, coverage.Requirements.Count);
        Assert.All(coverage.Requirements, row => Assert.Equal("not tested", row.Status));
        Assert.Contains("Build unavailable", coverage.Requirements[0].Results[0].Reason);
    }

    [Fact]
    public void LockedDeviceExplainsWhyItsRequirementsWereNotTested()
    {
        var execution = JsonSerializer.Deserialize<JsonElement>("""
            {"devices":[{"device":{"id":"phone-a","platform":"android"},
            "stoppingReason":"Phone locked","scenarios":[]}]}
            """);
        var coverage = RequirementReportBuilder.Build([Definition], [Scope], execution, "");
        Assert.Contains("Phone locked", coverage.Requirements[0].Results[0].Reason);
    }

    [Fact]
    public void ObservedRequirementIncludesItsStepAndScreenshot()
    {
        var coverage = Build(Result("passed"));
        var result = Assert.Single(Assert.Single(coverage.Requirements).Results);
        Assert.Equal(4, result.Step);
        Assert.Equal("devices/phone-a/check-0004.png", result.Screenshot);
        Assert.Equal("Value stays saved.", coverage.Requirements[0].Definition.Text);
    }

    [Fact]
    public void UnknownWorkerIdDoesNotReplaceTheHostRequirement()
    {
        var row = Result("passed", id: "UNKNOWN");
        Assert.Equal("not tested", Build(row).Requirements[0].Status);
    }

    [Fact]
    public void OtherDeviceEvidenceCannotPassThisDevice()
    {
        Assert.Equal("not tested", Build(Result("passed"), device: "phone-b").Requirements[0].Status);
    }

    [Fact]
    public void OtherTargetEvidenceCannotPassThisTarget()
    {
        Assert.Equal("not tested", Build(Result("passed"), target: "Other").Requirements[0].Status);
    }

    [Fact]
    public void UntestedSecondDevicePreventsFullCoverage()
    {
        var second = Scope with
        {
            DeviceId = "phone-b",
            DeviceName = "Phone B"
        };
        var coverage = RequirementReportBuilder.Build([Definition], [Scope, second], Execution(Result("passed")), "");
        Assert.Equal("inconclusive", coverage.Requirements[0].Status);
        Assert.True(coverage.HasUnresolved);
    }

    [Fact]
    public void FailureDoesNotHideAnUntestedDevice()
    {
        var second = Scope with
        {
            DeviceId = "phone-b",
            DeviceName = "Phone B"
        };
        var execution = Execution(Result("failed"));
        var coverage = RequirementReportBuilder.Build([Definition], [Scope, second], execution, "");
        Assert.True(coverage.HasFailures);
        Assert.True(coverage.HasUnresolved);
        Assert.Equal(new RunOutcome(1, "failed", "incomplete"), RunOutcomePolicy.Evaluate(1, execution, coverage));
    }

    [Fact]
    public void OverrideNeedsTheActualInstructionQuote()
    {
        var coverage = Build(Result("overridden", quote: "invented"), instructions: "Explore only");
        Assert.Equal("inconclusive", coverage.Requirements[0].Status);
    }

    [Fact]
    public void ValidConflictRetainsItsExplanationAndQuote()
    {
        var coverage = Build(Result("overridden", quote: "Explore only"), instructions: "Explore only");
        Assert.Equal("overridden", coverage.Requirements[0].Status);
        Assert.Equal("Explore only", coverage.Requirements[0].Results[0].InstructionQuote);
    }

    [Fact]
    public void PassWithoutObservedBehaviorIsInconclusive()
    {
        var row = Result("passed");
        row["observed"] = "";
        Assert.Equal("inconclusive", Build(row).Requirements[0].Status);
    }

    [Fact]
    public void MissingScreenshotHasAnExplicitExplanation()
    {
        var row = Result("failed");
        row["screenshot"] = "";
        var coverage = Build(row);
        Assert.True(coverage.HasFailures);
        Assert.NotEmpty(coverage.Requirements[0].Results[0].EvidenceError);
    }

    [Fact]
    public void MissingRequirementCoverageCannotProduceAPass()
    {
        var execution = Execution(Result("passed"));
        var coverage = RequirementReportBuilder.Build([Definition], [Scope], null, "");
        Assert.Equal(new RunOutcome(2, "inconclusive", "incomplete"), RunOutcomePolicy.Evaluate(0, execution, coverage));
    }

    [Fact]
    public void DocumentHeadingDoesNotPreventAPassedRequirementFromCompleting()
    {
        var definitions = RequirementCatalogue.Read("# Requirements\nValue stays saved.");
        var execution = Execution(Result("passed"));
        var coverage = RequirementReportBuilder.Build(definitions, [Scope], execution, "");
        Assert.Single(coverage.Requirements);
        Assert.False(coverage.HasUnresolved);
        Assert.Equal(new RunOutcome(0, "passed", "complete"), RunOutcomePolicy.Evaluate(0, execution, coverage));
    }

    [Fact]
    public void RequirementFailureSurvivesAnInfrastructureError()
    {
        var coverage = Build(Result("failed"));
        var outcome = RunOutcomePolicy.Evaluate(3, null, coverage);
        Assert.Equal("failed", outcome.Verdict);
        Assert.Equal(3, outcome.ExitCode);
    }

    private static RequirementCoverage Build(Dictionary<string, object?> row, string device = "phone-a",
        string target = "Release", string instructions = "") =>
        RequirementReportBuilder.Build([Definition], [Scope], Execution(row, device, target), instructions);

    // Normal dictionaries make changed fields visible in each test.
    private static Dictionary<string, object?> Result(string status, string id = "REQ-0001", string quote = "") => new()
    {
        ["id"] = id,
        ["status"] = status,
        ["expected"] = "Value stays saved",
        ["observed"] = "Saved value visible",
        ["reason"] = "Instruction conflicts with this expectation",
        ["instructionQuote"] = quote,
        ["step"] = 4,
        ["screenshot"] = "devices/phone-a/check-0004.png"
    };

    private static JsonElement Execution(Dictionary<string, object?> row, string device = "phone-a", string target = "Release") =>
        JsonSerializer.SerializeToElement(new
        {
            devices = new[] { new {
            device = new { id = device, platform = "android" },
            scenarios = new[] { new { target, verdict = "passed", completion = "complete", crashes = Array.Empty<object>(), requirements = new[] { row } } }
        } }
        });
}
