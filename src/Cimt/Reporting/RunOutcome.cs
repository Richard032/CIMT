using System.Text.Json;

namespace Cimt;

public sealed record RunOutcome(int ExitCode, string Verdict, string Completion);

/// <summary>Calculates the final outcome without reading files or calling tools.</summary>
public static class RunOutcomePolicy
{
    /// <summary>Keep failures visible even when coverage is incomplete or a build failed.</summary>
    public static RunOutcome Evaluate(int exit, JsonElement? execution)
    {
        var hasCrash = false;
        var allComplete = execution.HasValue;
        if (execution is { } value && value.TryGetProperty("devices", out var devices))
            foreach (var device in devices.EnumerateArray())
            {
                allComplete &= !HasStop(device);
                foreach (var scenario in device.GetProperty("scenarios").EnumerateArray())
                {
                    hasCrash |= scenario.GetProperty("crashes").GetArrayLength() > 0;
                    allComplete &= scenario.GetProperty("completion").GetString() == "complete";
                }
            }
        if (hasCrash)
            exit = ExitCodes.Combine(exit, 1);
        if (!execution.HasValue)
            exit = ExitCodes.Combine(exit, 2);
        var verdict = hasCrash || exit == 1 ? "failed" : exit == 0 ? "passed" : "inconclusive";
        var completion = (exit is 0 or 1) && allComplete ? "complete" : "incomplete";
        return new(exit, verdict, completion);
    }

    private static bool HasStop(JsonElement device)
    {
        return new[] { "stoppingReason", "error" }.Any(key =>
            device.TryGetProperty(key, out var reason) && reason.ValueKind != JsonValueKind.Null);
    }
}
