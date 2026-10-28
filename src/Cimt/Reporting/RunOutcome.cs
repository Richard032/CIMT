using System.Text.Json;

namespace Cimt;

public sealed record RunOutcome(int ExitCode, string Verdict, string Completion);

/// <summary>Calculates the final outcome without reading files or calling tools.</summary>
public static class RunOutcomePolicy
{
    /// <summary>Keep failures visible even when coverage is incomplete or a build failed.</summary>
    public static RunOutcome Evaluate(int exit, JsonElement? execution, RequirementCoverage? coverage = null)
    {
        var hasFailure = false;
        var scenarioCount = 0;
        var allComplete = execution.HasValue;
        var allDecided = execution.HasValue;
        if (execution is { } value && value.TryGetProperty("devices", out var devices))
            foreach (var device in devices.EnumerateArray())
            {
                allComplete &= !HasStop(device);
                foreach (var scenario in device.GetProperty("scenarios").EnumerateArray())
                {
                    scenarioCount++;
                    var verdict = scenario.TryGetProperty("verdict", out var result) ? result.GetString() : null;
                    hasFailure |= scenario.GetProperty("crashes").GetArrayLength() > 0 || verdict == "failed";
                    allDecided &= verdict is "passed" or "failed";
                    allComplete &= scenario.GetProperty("completion").GetString() == "complete";
                }
            }
        allDecided &= scenarioCount > 0;
        hasFailure |= coverage?.HasFailures == true;
        allComplete &= coverage?.HasUnresolved != true;
        if (hasFailure)
            exit = ExitCodes.Combine(exit, 1);
        if (!allComplete || !allDecided)
            exit = ExitCodes.Combine(exit, 2);
        var finalVerdict = hasFailure || exit == 1 ? "failed" : exit == 0 ? "passed" : "inconclusive";
        var completion = (exit is 0 or 1) && allComplete && allDecided ? "complete" : "incomplete";
        return new(exit, finalVerdict, completion);
    }

    private static bool HasStop(JsonElement device)
    {
        return new[] { "stoppingReason", "error" }.Any(key =>
            device.TryGetProperty(key, out var reason) && reason.ValueKind != JsonValueKind.Null);
    }
}
