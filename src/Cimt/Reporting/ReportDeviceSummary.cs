using System.Text.Json;
using static Cimt.ReportHtml;

namespace Cimt;

public sealed record ReportDeviceResult(string Platform, string DeviceId, string Name, string Target,
    string Verdict, string Completion, int Actions, int Steps, int Confirmed, int Suspected, string Stop, string? Anchor);

/// <summary>Includes expected combinations even when no device scenario started.</summary>
public static class ReportDeviceSummary
{
    public static IReadOnlyList<ReportDeviceResult> Create(RunState state, IReadOnlyList<ReportScenario> scenarios, JsonElement? execution = null)
    {
        var rows = new List<ReportDeviceResult>();
        foreach (var device in state.Devices)
        {
            var platform = device.GetValueOrDefault("platform", "");
            foreach (var target in state.Configuration.Root.Get("build")?.Get("targets")?.List ?? [])
                if (target.Get(platform) is not null)
                    rows.Add(Summarize(state, scenarios, platform, device.GetValueOrDefault("id", ""),
                        device.GetValueOrDefault("name", platform), target.Value("name") ?? "", execution));
        }
        foreach (var scenario in scenarios)
            if (!rows.Any(row => Matches(row, scenario)))
                rows.Add(Summarize(state, scenarios, scenario.Platform, scenario.DeviceId, scenario.Name, scenario.Target, execution));
        return rows;
    }

    private static bool Matches(ReportDeviceResult row, ReportScenario scenario) =>
        row.Platform == scenario.Platform && row.DeviceId == scenario.DeviceId && row.Target == scenario.Target;

    private static ReportDeviceResult Summarize(RunState state, IReadOnlyList<ReportScenario> scenarios,
        string platform, string id, string name, string target, JsonElement? execution)
    {
        var matches = scenarios.Where(row => row.Platform == platform && row.DeviceId == id && row.Target == target).ToArray();
        var statuses = matches.Select(row => Field(row.Result, "verdict", "inconclusive")).ToArray();
        var verdict = statuses.Contains("failed") ? "failed" : statuses.Length == 0 ? "not tested"
            : statuses.All(status => status == "passed") ? "passed" : "inconclusive";
        var completion = matches.Length > 0 && matches.All(row => Field(row.Result, "completion") == "complete") ? "complete" : "incomplete";
        var worker = matches.FirstOrDefault()?.Device ?? (execution is { } saved ? Rows(saved, "devices").FirstOrDefault(device =>
            device.TryGetProperty("device", out var identity) && Field(identity, "id") == id && Field(identity, "platform") == platform) : default);
        var stop = Field(worker, "error");
        if (stop.Length == 0)
            stop = Field(worker, "stoppingReason");
        if (stop.Length == 0 && matches.Length == 0)
            stop = state.Builds.Any(build => build.GetValueOrDefault("target") == target && build.GetValueOrDefault("platform") == platform)
                ? "No scenario started for this device/target." : "No installable build was available for this target/platform.";
        if (stop.Length == 0)
            stop = completion == "complete" ? "Recorded objective completed." : "Objective incomplete; review remaining work and stopping reasons.";
        return new(platform, id, name, target, verdict, completion, matches.Sum(row => row.ActionCount),
            matches.Sum(row => row.Steps.Length), matches.Sum(row => row.ConfirmedCrashes),
            matches.Sum(row => row.SuspectedTerminations), stop, matches.FirstOrDefault()?.Anchor);
    }
}
