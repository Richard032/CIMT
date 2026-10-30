using System.Text.Json;

namespace Cimt;

public sealed record RunStopReason(string Category, string Scope, string Message)
{
    public string Description => Scope + ": " + Message;
}

/// <summary>Explains saved worker outcomes without inferring crashes from infrastructure errors.</summary>
public static class RunDiagnostics
{
    public static IReadOnlyList<RunStopReason> WorkerReasons(JsonElement? execution)
    {
        var reasons = new List<RunStopReason>();
        if (execution is not { } value || !value.TryGetProperty("devices", out var devices))
            return reasons;
        foreach (var device in devices.EnumerateArray())
        {
            var identity = device.GetProperty("device");
            var scope = Field(identity, "platform") + " / " + Field(identity, "name", Field(identity, "id"));
            var scenarios = device.GetProperty("scenarios").EnumerateArray().ToArray();
            if (scenarios.Length > 0)
                scope += " / " + Field(scenarios[^1], "target");
            var error = Field(device, "error");
            if (error.Length > 0)
                reasons.Add(new("Infrastructure failure", scope, error));
            var stop = Field(device, "stoppingReason");
            if (stop.Length > 0)
                reasons.Add(new(StopCategory(stop), scope, stop));
            foreach (var scenario in scenarios)
            {
                var scenarioScope = Field(identity, "platform") + " / " + Field(identity, "name", Field(identity, "id"))
                    + " / " + Field(scenario, "target");
                if (Field(scenario, "verdict") == "failed")
                    reasons.Add(new("Application test failure", scenarioScope,
                        "Recorded checks or crash/termination findings failed. See the scenario findings."));
                if (scenario.TryGetProperty("remaining", out var remaining))
                    foreach (var item in remaining.EnumerateArray())
                        reasons.Add(new("Remaining or blocked work", scenarioScope, item.ToString()));
            }
        }
        return reasons;
    }

    public static IReadOnlyList<RunStopReason> StopReasons(RunState state, JsonElement? execution, RunOutcome outcome)
    {
        var reasons = state.StopReasons.Concat(WorkerReasons(execution)).Distinct().ToList();
        foreach (var error in state.Errors.Distinct())
            if (!reasons.Any(reason => reason.Description == error || reason.Message == error))
                reasons.Add(new("Run error", "Run", state.Configuration.Scrub(error)));
        if (reasons.Count == 0)
            reasons.Add(new(outcome.Completion == "complete" ? "Completed" : "Incomplete coverage", "Run",
                outcome.Completion == "complete" ? "Recorded testing finished. Review the verdict and coverage."
                    : "Testing did not establish complete coverage. Review untested requirements and device scenarios."));
        return reasons;
    }

    private static string StopCategory(string reason)
    {
        if (reason.StartsWith("Run stopped after another worker", StringComparison.Ordinal))
            return "Cancelled after another worker stopped";
        if (reason.Contains("locked", StringComparison.OrdinalIgnoreCase))
            return "Device unavailable";
        return reason.Contains("limit", StringComparison.OrdinalIgnoreCase) || reason.Contains("budget", StringComparison.OrdinalIgnoreCase)
            ? "Run limit" : "Device or execution stop";
    }

    private static string Field(JsonElement item, string key, string fallback = "") =>
        item.TryGetProperty(key, out var value) && value.ValueKind != JsonValueKind.Null ? value.ToString() : fallback;
}
