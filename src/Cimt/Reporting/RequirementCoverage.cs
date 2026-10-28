namespace Cimt;

/// <summary>One target and startup device where a requirement needs a result.</summary>
public sealed record RequirementScope(string Target, string Platform, string DeviceId, string DeviceName, string UnavailableReason);

/// <summary>A result keeps its scope and evidence separate from the original source text.</summary>
public sealed record RequirementAssessment(RequirementScope Scope, string Status, string Expected,
    string Observed, string Reason, string InstructionQuote, int? Step, string Screenshot, string EvidenceError);

/// <summary>Retains every scoped decision under its original catalogue entry.</summary>
public sealed record RequirementSummary(RequirementDefinition Definition, string Status, IReadOnlyList<RequirementAssessment> Results);

/// <summary>Stores a complete matrix, including combinations that never started.</summary>
public sealed record RequirementCoverage(IReadOnlyList<RequirementSummary> Requirements, string SourceSha256 = "")
{
    public bool HasFailures => Requirements.Any(row => row.Status == "failed");
    public bool HasUnresolved => Requirements.Any(row => row.Status is "not tested" or "inconclusive"
        || row.Results.Any(result => result.Status is "not tested" or "inconclusive"));
}

/// <summary>Combines scoped results without allowing an untested combination to pass.</summary>
public static class RequirementStatus
{
    public static string Combine(IEnumerable<string> values)
    {
        var statuses = values.ToArray();
        if (statuses.Contains("failed"))
            return "failed";
        if (statuses.Length == 0 || statuses.All(value => value == "not tested"))
            return "not tested";
        if (statuses.Any(value => value is not ("passed" or "overridden")))
            return "inconclusive";
        return statuses.All(value => value == "overridden") ? "overridden" : "passed";
    }
}
