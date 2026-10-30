using System.Globalization;
using System.Net;
using System.Text.Json;

namespace Cimt;

/// <summary>Renders the overview, stopping reasons, and ordered activity in plain language.</summary>
public sealed class RunDiagnosticsRenderer(Configuration configuration)
{
    public string Render(RunState state, RunOutcome outcome, JsonElement? execution, IReadOnlyList<RunActivityEntry> activity)
    {
        return Overview(state, execution) + Reasons(state, outcome, execution) + Timeline(state.Report, activity);
    }

    private string Overview(RunState state, JsonElement? execution)
    {
        var finished = state.Finished ?? DateTimeOffset.UtcNow;
        var targets = configuration.Root.Get("build")?.Get("targets")?.List ?? [];
        var rows = targets.Select(target => "<li>" + Encoded(target.Value("name") ?? "")
            + " — configuration: " + Encoded(target.Value("configuration") ?? "") + "</li>");
        var devices = state.Devices.Select(device => "<li>" + Encoded(device.GetValueOrDefault("platform", ""))
            + " / " + Safe(device.GetValueOrDefault("name", device.GetValueOrDefault("id", ""))) + "</li>");
        var requests = execution is { } value && value.TryGetProperty("budget", out var budget)
            && budget.TryGetProperty("requests", out var count) ? count.ToString() : "Unavailable; no recorded AI request count";
        return "<h2>Run overview</h2><dl>"
            + Row("Command", state.Command) + Row("Started (UTC)", state.Started.ToUniversalTime().ToString("O"))
            + Row("Finished (UTC)", finished.ToUniversalTime().ToString("O"))
            + Row("Elapsed seconds", Math.Max(0, (finished - state.Started).TotalSeconds).ToString("0.000", CultureInfo.InvariantCulture))
            + Row("Successful app builds available", state.Builds.Count.ToString(CultureInfo.InvariantCulture))
            + Row("AI inference requests", requests) + "</dl>"
            + "<h3>Requested targets and actual build configurations</h3><ul>" + string.Join("", rows) + "</ul>"
            + "<h3>Startup devices</h3><ul>" + string.Join("", devices) + "</ul>"
            + "<p>Install/reset/launch commands and screenshot checks are preparation. They do not establish a passed application test.</p>";
    }

    private string Reasons(RunState state, RunOutcome outcome, JsonElement? execution)
    {
        var reasons = RunDiagnostics.StopReasons(state, execution, outcome);
        return "<h2>Failures and stopping reasons</h2><ul>" + string.Join("", reasons.Select(reason =>
            "<li><strong>" + Encoded(reason.Category) + "</strong> — " + Safe(reason.Scope)
            + ": " + Safe(reason.Message) + "</li>"))
            + "</ul><p>An infrastructure or masking failure is not evidence of an application crash. See recorded findings for crash/termination evidence.</p>";
    }

    private string Timeline(string report, IReadOnlyList<RunActivityEntry> activity)
    {
        var body = "<h2>Chronological activity</h2>";
        if (activity.Count == 0)
            return body + "<p>No timestamped activity was recorded. A detailed timeline cannot be reconstructed from this result.</p>";
        return body + "<p>Times are UTC. Device operations may overlap. Started operations without an outcome were interrupted or have no recorded result.</p><ol>"
            + string.Join("", activity.Select(entry => Entry(report, entry))) + "</ol>"
            + Link(report, "activity.jsonl", "Download the timestamped activity journal");
    }

    private string Entry(string report, RunActivityEntry entry)
    {
        var context = string.Join(" / ", new[] { entry.Platform, entry.Device, entry.Target }.Where(value => !string.IsNullOrEmpty(value)));
        var body = "<li><time>" + Encoded(entry.Timestamp.ToUniversalTime().ToString("O")) + "</time> "
            + "<strong>" + Encoded(entry.Status) + " — " + Encoded(entry.Operation) + "</strong>"
            + (context.Length == 0 ? "" : "<p>" + Encoded(context) + "</p>")
            + (entry.DurationSeconds is { } seconds ? "<p>Duration: " + seconds.ToString("0.000", CultureInfo.InvariantCulture) + " seconds</p>" : "")
            + (string.IsNullOrEmpty(entry.Message) ? "" : "<p>" + Safe(entry.Message) + "</p>");
        if (!string.IsNullOrEmpty(entry.ExceptionType) || !string.IsNullOrEmpty(entry.Details))
            body += "<details><summary>Exception details: " + Encoded(entry.ExceptionType ?? "") + "</summary><pre>"
                + Safe(entry.Details ?? "") + "</pre></details>";
        if (!string.IsNullOrEmpty(entry.Log))
            body += Link(report, entry.Log, "Related diagnostic log");
        return body + "</li>";
    }

    private static string Link(string report, string relative, string label)
    {
        try
        {
            var full = Path.GetFullPath(relative, report);
            RunFolderSafety.Inside(report, full);
            if (!File.Exists(full))
                return "<p>" + Encoded(label) + ": unavailable</p>";
            var href = string.Join("/", Path.GetRelativePath(report, full).Split(Path.DirectorySeparatorChar).Select(Uri.EscapeDataString));
            return "<p><a href=\"" + Encoded(href) + "\">" + Encoded(label) + "</a></p>";
        }
        catch (Exception error) when (error is ConfigurationException or ArgumentException or IOException)
        {
            return "<p>Diagnostic link rejected: it is outside this report or invalid.</p>";
        }
    }

    // Metadata is escaped, while free text is redacted before HTML encoding.
    private static string Row(string label, string value) => "<dt>" + Encoded(label) + "</dt><dd>" + Encoded(value) + "</dd>";
    private string Safe(string value) => Encoded(configuration.Scrub(value));
    private static string Encoded(string value) => WebUtility.HtmlEncode(value);
}
