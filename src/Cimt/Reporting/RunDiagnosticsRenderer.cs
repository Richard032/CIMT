using System.Globalization;
using System.Text.Json;
using static Cimt.ReportHtml;

namespace Cimt;

/// <summary>Renders saved outcome summaries, stopping reasons and activity.</summary>
public sealed class RunDiagnosticsRenderer(Configuration configuration)
{
    public string Render(RunState state, RunOutcome outcome, JsonElement? execution, IReadOnlyList<RunActivityEntry> activity) =>
        Overview(state, outcome, execution, ReportScenario.Read(execution)) + Reasons(state, outcome, execution) + Timeline(state.Report, activity);

    public string Overview(RunState state, RunOutcome outcome, JsonElement? execution, IReadOnlyList<ReportScenario> scenarios) =>
        "<section id=\"overview\" aria-labelledby=\"overview-title\"><h2 id=\"overview-title\">Run overview</h2>"
        + "<p class=\"outcome\">" + Badge(outcome.Verdict) + " " + Badge(outcome.Completion) + "</p>"
        + "<p class=\"outcome-explanation\">" + Encode(Explanation(state, outcome, execution, scenarios)) + "</p>"
        + "<h3>Devices and targets</h3>" + DeviceTable(ReportDeviceSummary.Create(state, scenarios, execution)) + Facts(state, execution)
        + "<p>Only recorded target/device/control paths were exercised. This report does not prove coverage of every possible application state.</p></section>";

    private static string Explanation(RunState state, RunOutcome outcome, JsonElement? execution, IReadOnlyList<ReportScenario> scenarios)
    {
        var confirmed = scenarios.Sum(row => row.ConfirmedCrashes);
        var suspected = scenarios.Sum(row => row.SuspectedTerminations);
        var failures = scenarios.Sum(row => Rows(row.Result, "checks").Count(check => ReportChecks.Failed(row.Result, check)));
        var observations = $"Recorded {confirmed} confirmed crash occurrences, {suspected} suspected terminations and {failures} effective failed checks. ";
        var interrupted = RunDiagnostics.StopReasons(state, execution, outcome).Any(reason => reason.Category == "User interruption"
            || reason.Message.StartsWith("User interrupted", StringComparison.Ordinal));
        return observations + (interrupted ? "Testing remained incomplete because the user stopped execution."
            : outcome.Completion == "complete" ? "Recorded testing completed; review the verdict and scoped requirement results."
            : "Testing is incomplete. Review failures, stopping reasons and remaining work.");
    }

    private string DeviceTable(IReadOnlyList<ReportDeviceResult> rows) => rows.Count == 0
        ? "<p>No compatible device/target combination was recorded. Review discovery and configuration errors.</p>"
        : "<table class=\"device-overview\"><caption>Whole-run outcomes — all recorded and expected device/target combinations</caption>"
            + "<thead><tr>" + string.Join("", new[] { "Device / target", "Verdict / completion", "Actions / records", "Crash evidence", "Stop reason / investigate" }
                .Select(label => "<th scope=\"col\">" + label + "</th>")) + "</tr></thead><tbody>" + string.Join("", rows.Select(DeviceRow))
            + "</tbody></table><p>Counts describe saved records. No recorded crash is not proof of a crash-free application.</p>";

    private string DeviceRow(ReportDeviceResult row) => "<tr>"
        + Cell("Device / target", Encode(row.Platform) + " / " + Safe(row.Name) + "<br><small>" + Encode(row.DeviceId) + " / " + Encode(row.Target) + "</small>")
        + Cell("Verdict / completion", Badge(row.Verdict) + " " + Badge(row.Completion))
        + Cell("Actions / records", row.Actions + " actions / " + row.Steps + " records")
        + Cell("Crash evidence", row.Confirmed + " confirmed / " + row.Suspected + " suspected")
        + Cell("Stop reason / investigate", Safe(row.Stop) + (row.Anchor is null ? "" : "<br><a href=\"#" + row.Anchor + "\">View device steps</a>")) + "</tr>";

    private static string Cell(string label, string html) => "<td data-label=\"" + Encode(label) + "\">" + html + "</td>";

    private string Facts(RunState state, JsonElement? execution)
    {
        var finished = state.Finished ?? DateTimeOffset.UtcNow;
        var targets = configuration.Root.Get("build")?.Get("targets")?.List ?? [];
        var provenance = state.Stages.Select(stage => JsonSerializer.SerializeToElement(stage)).Where(stage => Field(stage, "sourceRunId").Length > 0);
        return "<h3>Run facts</h3><dl class=\"facts\">" + Row("Command", state.Command)
            + Row("Device environment", new DeviceSelection(configuration.Root.Get("execution")).Kind)
            + Row("Started (UTC)", Time(state.Started)) + Row(state.Finished is null ? "Snapshot updated (UTC)" : "Finished (UTC)", Time(finished))
            + Row("Elapsed", Duration((finished - state.Started).TotalSeconds)) + Row("Successful app builds available", state.Builds.Count.ToString(CultureInfo.InvariantCulture)) + "</dl>"
            + Budget(execution) + string.Join("", provenance.Select(stage => "<dl>" + Row("Source build run", Field(stage, "sourceRunId")) + Row("Source build commit", Field(stage, "sourceCommit")) + "</dl>"))
            + Details("Exact timestamps and build configurations", "<dl>" + Row("Started (UTC)", state.Started.ToUniversalTime().ToString("O"))
                + Row("Snapshot / finish (UTC)", finished.ToUniversalTime().ToString("O"))
                + Row("Elapsed seconds", Math.Max(0, (finished - state.Started).TotalSeconds).ToString("0.000", CultureInfo.InvariantCulture)) + "</dl><h4>Requested targets and actual build configurations</h4><ul>"
                + string.Join("", targets.Select(target => "<li>" + Encode(target.Value("name")) + " — configuration: " + Encode(target.Value("configuration")) + "</li>"))
                + "</ul><h4>Startup devices</h4><ul>" + string.Join("", state.Devices.Select(device => "<li>" + Encode(device.GetValueOrDefault("platform")) + " / " + Encode(device.GetValueOrDefault("type", "real")) + " / " + Safe(device.GetValueOrDefault("name", "")) + "</li>")) + "</ul>")
            + "<p>Install/reset/launch commands and screenshot checks are preparation. They do not establish a passed application test.</p>";
    }

    public string Budget(JsonElement? execution)
    {
        if (execution is not { } value || !value.TryGetProperty("budget", out var budget))
            return "<p>AI inference requests: Unavailable; no recorded AI request count or cost ledger.</p>";
        return "<dl class=\"facts\">" + Row("Model", Field(budget, "model", configuration.Root.Get("ai-model")?.Value("name") ?? "Not recorded"))
            + Row("AI inference requests", Field(budget, "requests", "Not recorded")) + Row("Accounted upper cost", Money(budget, "accountedUpperCost"))
            + Row("Uncertain upper cost", Money(budget, "uncertainUpperCost")) + Row("Pending reservations", Money(budget, "pendingUpperCost"))
            + Row("Input tokens", Field(budget, "inputTokens", "Not recorded"))
            + Row("Output tokens", Field(budget, "outputTokens", "Not recorded"))
            + Row("Recorded cached input tokens", Field(budget, "cachedInputTokens", "Not recorded"))
            + Row("Requests with cache usage details", Field(budget, "cacheUsageRequests", "Not recorded"))
            + Row("Budget limit", Money(budget, "limit")) + "</dl><p>Conservative cost accounting, not a verified provider invoice. Pending and uncertain costs remain reserved separately.</p>"
            + RequestUsage(budget);
    }

    private static string RequestUsage(JsonElement budget)
    {
        var rows = Rows(budget, "requestUsage");
        if (rows.Length == 0)
            return "";
        return Details("AI request token usage", "<table><caption>Completed request usage records</caption><thead><tr>"
            + "<th scope=\"col\">Purpose</th><th scope=\"col\">Usage status</th><th scope=\"col\">Input tokens</th>"
            + "<th scope=\"col\">Output tokens</th><th scope=\"col\">Cached input tokens</th></tr></thead><tbody>"
            + string.Join("", rows.Select(row => "<tr>" + string.Join("", new[] { "kind", "status", "inputTokens", "outputTokens", "cachedInputTokens" }
                .Select(key => "<td>" + Encode(Field(row, key, "Not recorded")) + "</td>")) + "</tr>")) + "</tbody></table>");
    }

    private static string Money(JsonElement budget, string key) => decimal.TryParse(Field(budget, key), NumberStyles.Number, CultureInfo.InvariantCulture, out var amount)
        ? amount.ToString("0.########", CultureInfo.InvariantCulture) + " " + Field(budget, "currency", "currency not recorded") : "Not recorded";

    public string Reasons(RunState state, RunOutcome outcome, JsonElement? execution)
    {
        var reasons = RunDiagnostics.StopReasons(state, execution, outcome);
        return "<h3>Failures and stopping reasons</h3><ul>" + string.Join("", reasons.Where(reason => reason.Category != "Remaining or blocked work").Select(Reason)) + "</ul>"
            + (reasons.Any(reason => reason.Category == "Remaining or blocked work") ? Details("Remaining or blocked work by device/scenario", "<ul>"
                + string.Join("", reasons.Where(reason => reason.Category == "Remaining or blocked work").Select(Reason)) + "</ul>") : "")
            + "<p>An infrastructure or masking failure is not evidence of an application crash.</p>";
    }

    private string Reason(RunStopReason reason) => "<li><strong>" + Encode(reason.Category) + "</strong> — " + Safe(reason.Scope) + ": " + Safe(reason.Message) + "</li>";

    public string Timeline(string report, IReadOnlyList<RunActivityEntry> activity)
    {
        if (activity.Count == 0)
            return "<h3>Chronological activity</h3><p>No timestamped activity was recorded. A detailed timeline cannot be reconstructed from this result.</p>";
        return "<h3>Chronological activity</h3><p>" + activity.Count + " records. Times are UTC. Device operations may overlap. Started operations without an outcome were interrupted or have no recorded result.</p>"
            + "<p>Compact rows group recorded statuses; repeated operations are not assumed to be paired.</p>" + Compact(activity)
            + Details("Full chronological journal (" + activity.Count + " records)", "<div data-filter-area>" + Filters("activity") + "<ol>"
                + string.Join("", activity.OrderBy(entry => entry.Timestamp).Select(entry => Entry(report, entry))) + "</ol></div>")
            + "<p>" + new ReportEvidence(report).Link("activity.jsonl", "Download the timestamped activity journal") + "</p>";
    }

    private string Compact(IReadOnlyList<RunActivityEntry> activity) => Details("Compact operation summary", "<ul>"
        + string.Join("", activity.GroupBy(entry => (entry.Operation, entry.Platform, entry.Device, entry.Target)).Select(group => "<li><strong>" + Encode(group.Key.Operation)
            + "</strong> — " + Encode(string.Join(" / ", new[] { group.Key.Platform, group.Key.Device, group.Key.Target }.Where(value => value.Length > 0)))
            + ": " + Encode(string.Join("; ", group.GroupBy(entry => entry.Status).Select(status => status.Key + ": " + status.Count()))) + "</li>")) + "</ul>");

    private string Entry(string report, RunActivityEntry entry)
    {
        var context = string.Join(" / ", new[] { entry.Platform, entry.Device, entry.Target }.Where(value => !string.IsNullOrEmpty(value)));
        var body = "<li" + Attributes(entry.Platform + " / " + entry.Device, entry.Target, entry.Status) + "><time datetime=\"" + Encode(entry.Timestamp.ToUniversalTime().ToString("O"))
            + "\">" + Encode(Time(entry.Timestamp)) + "</time> <strong>" + Encode(entry.Status) + " — " + Encode(entry.Operation) + "</strong><p>" + Encode(context) + "</p>"
            + (entry.DurationSeconds is { } seconds ? "<p>Duration: " + Encode(Duration(seconds)) + " (" + seconds.ToString("0.000", CultureInfo.InvariantCulture) + " seconds)</p>" : "")
            + (string.IsNullOrEmpty(entry.Message) ? "" : "<p>" + Safe(entry.Message) + "</p>");
        if (!string.IsNullOrEmpty(entry.ExceptionType) || !string.IsNullOrEmpty(entry.Details))
            body += Details("Exception details: " + entry.ExceptionType, "<pre>" + Safe(entry.Details) + "</pre>");
        if (!string.IsNullOrEmpty(entry.Log))
            body += "<p>" + (new ReportEvidence(report).RelativePath(entry.Log) is null ? "Diagnostic link rejected: unavailable, outside this report or invalid."
                : new ReportEvidence(report).Link(entry.Log, "Related diagnostic log")) + "</p>";
        return body + "</li>";
    }

    private string Safe(string value) => Encode(configuration.Scrub(value));
}
