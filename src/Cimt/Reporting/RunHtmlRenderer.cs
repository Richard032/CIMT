using System.Net;
using System.Text.Json;

namespace Cimt;

/// <summary>Converts report data into HTML. It never changes the test result.</summary>
public sealed class RunHtmlRenderer(Configuration configuration)
{
    private const string PageStart = """
        <!doctype html><html lang="en"><meta charset="utf-8"><title>CIMT application test</title>
        <style>body{font:16px system-ui;max-width:1150px;margin:2rem auto;padding:1rem;color:#172333}
        img{max-width:280px;max-height:520px}pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#f1f4f8;padding:1rem}li{margin:.7rem 0}</style>
        """;

    /// <summary>Render saved results while escaping HTML and removing configured secrets.</summary>
    public string Render(RunState state, RunOutcome outcome, JsonElement? execution, RequirementCoverage? coverage = null,
        IReadOnlyList<RunActivityEntry>? activity = null, bool inProgress = false)
    {
        // Redact parsed values first. Never run replacement over JSON or HTML markup.
        JsonElement? safeExecution = execution is { } value
            ? JsonSerializer.SerializeToElement(new ExecutionRedactor(new JsonTextRedactor(configuration.Scrub)).Execution(value))
            : null;
        return PageStart + (inProgress
            ? "<p><strong>Partial report — run in progress or finalization interrupted.</strong> Reload this page for newer saved observations. The run has not been confirmed complete.</p>" : "")
            + Header(state, outcome)
            + new RunDiagnosticsRenderer(configuration).Render(state, outcome, safeExecution,
                activity ?? RunActivityLog.Read(state.Report, configuration.Scrub))
            + Stages(state.Stages) + Inputs(state.Report)
            + new RequirementHtmlRenderer(configuration).Render(coverage, state.RequirementHeadings) + Execution(safeExecution) + "<p><a href=\"result.json\">Machine-readable run result</a></p></html>";
    }

    private string Header(RunState state, RunOutcome outcome)
    {
        return "<h1>CIMT application test</h1><p>Exit: " + outcome.ExitCode
            + " · Verdict: " + Encoded(outcome.Verdict) + " · Completion: " + Encoded(outcome.Completion) + "</p>"
            + "<p>Run: " + Encoded(state.Identity.Id) + " (UTC)</p>"
            + "<p>Branch: " + Encoded(state.Configuration.Root.Get("repository")!.Value("branch")!)
            + " · Commit: " + Encoded(state.Commit) + "</p>"
            + "<p>Only recorded target/device/control paths were exercised. This report does not prove coverage of every possible application state.</p>";
    }

    private string Stages(IEnumerable<object> stages)
    {
        return "<h2>Run stages</h2><ul>" + string.Join("", stages.Select(Stage)) + "</ul>";
    }

    private string Stage(object stage)
    {
        var item = JsonSerializer.SerializeToElement(stage);
        var description = Field(item, "stage") + " " + Field(item, "target") + " "
            + Field(item, "platform") + ": " + Field(item, "result");
        var log = Detail("diagnostics") && item.TryGetProperty("log", out var path)
            ? " — <a href=\"" + Encoded(path.ToString()) + "\">build log</a>" : "";
        return "<li>" + Encoded(description) + log + "</li>";
    }

    private string Inputs(string report)
    {
        var file = Path.Combine(report, "inputs.json");
        if (!Detail("requirements") || !File.Exists(file))
            return "";
        var inputs = JsonSerializer.Deserialize<JsonElement>(File.ReadAllText(file));
        var safe = new JsonTextRedactor(configuration.Scrub).Text(inputs);
        return Details("Testing instructions and requirements", safe!.ToJsonString());
    }

    private string Execution(JsonElement? execution)
    {
        if (execution is not { } value)
            return "<p>No application UI interaction result was produced.</p>";
        var body = "<h2>Device scenarios and coverage</h2>"
            + string.Join("", value.GetProperty("devices").EnumerateArray().Select(Device));
        if (value.TryGetProperty("budget", out var budget))
            body += "<h2>AI budget accounting</h2><pre>" + Encoded(budget.ToString()) + "</pre>";
        if (Detail("diagnostics"))
            body += Details("Execution data", value.ToString());
        return body;
    }

    private string Device(JsonElement device)
    {
        var identity = device.GetProperty("device");
        var name = Field(identity, "name", Field(identity, "platform"));
        return "<h3>" + Safe(name) + "</h3>" + Notes(device, ["error", "stoppingReason"])
            + string.Join("", device.GetProperty("scenarios").EnumerateArray().Select(Scenario));
    }

    private string Scenario(JsonElement scenario)
    {
        var body = "<h4>" + Encoded(Field(scenario, "target")) + " — "
            + Encoded(Field(scenario, "verdict", "inconclusive")) + " / " + Encoded(Field(scenario, "completion")) + "</h4>";
        body += Coverage(scenario) + Exploration(scenario) + Findings(scenario) + Checks(scenario) + RejectedResponses(scenario);
        if (!HasScreenshot(scenario, "steps") && !HasScreenshot(scenario, "rejectedResponses"))
            body += "<p>No verified screenshot was saved for this scenario. See failures and stopping reasons.</p>";
        if (scenario.TryGetProperty("remaining", out var remaining) && remaining.GetArrayLength() > 0)
            body += "<p>Remaining/blocked work:</p><pre>" + Encoded(remaining.ToString()) + "</pre>";
        if (Detail("interpretations") && scenario.TryGetProperty("interpretation", out var interpretation))
            body += "<p>Interpretation: " + Safe(interpretation.ToString()) + "</p>";
        if (Detail("scenarios"))
            body += "<details open><summary>Steps and observed behaviour</summary><ol>"
                + string.Join("", scenario.GetProperty("steps").EnumerateArray().Select(Step)) + "</ol></details>";
        return body;
    }

    private static bool HasScreenshot(JsonElement scenario, string collection) =>
        scenario.TryGetProperty(collection, out var rows)
        && rows.EnumerateArray().Any(row => Field(row, "screenshot").Length > 0);

    private string Coverage(JsonElement scenario)
    {
        if (!scenario.TryGetProperty("coverage", out var coverage))
            return "";
        return "<p>Observed control/state combinations: " + Encoded(Field(coverage, "observedControls", "0"))
            + "; activated: " + Encoded(Field(coverage, "attemptedControls", "0"))
            + "; outstanding: " + Encoded(Field(coverage, "outstandingObservedControls", "0")) + ".</p>";
    }

    private string RejectedResponses(JsonElement scenario)
    {
        if (!scenario.TryGetProperty("rejectedResponses", out var responses) || responses.GetArrayLength() == 0)
            return "";
        // Keep these diagnostics visible even when optional report sections are disabled.
        return "<h5>Unaccepted AI responses</h5><p>These responses failed validation. Their proposed actions were not executed, "
            + "and their observations are unverified and are not used for the test verdict.</p>"
            + string.Join("", responses.EnumerateArray().Select(response =>
                Details("Attempt " + Field(response, "attempt") + ": " + Field(response, "error"), response.ToString())
                + (response.TryGetProperty("screenshot", out var screenshot) ? Image(screenshot.ToString())
                    : "<p>No screenshot was saved for this rejected response.</p>")));
    }

    private string Exploration(JsonElement scenario)
    {
        if (!scenario.TryGetProperty("exploration", out var memory))
            return "";
        var count = memory.TryGetProperty("paths", out var paths) ? paths.GetArrayLength() : 0;
        return "<p>Remembered exploration paths: " + count + ". Repeated unchanged actions are redirected; this does not prove exhaustive coverage.</p>"
            + (Detail("scenarios") ? Details("Exploration memory and observed outcomes", memory.ToString()) : "");
    }

    private string Findings(JsonElement scenario)
    {
        if (!scenario.TryGetProperty("crashes", out var crashes) || crashes.GetArrayLength() == 0)
            return "";
        return "<p>Crash/termination findings: " + crashes.GetArrayLength() + ".</p>"
            + (Detail("findings") ? Details("Findings and reproduction", crashes.ToString()) : "");
    }

    private string Checks(JsonElement scenario)
    {
        if (!scenario.TryGetProperty("checks", out var checks) || checks.GetArrayLength() == 0)
            return "";
        var rows = checks.EnumerateArray().ToArray();
        var overridden = OverriddenRequirements(scenario);
        var failed = rows.Count(check => IsEffectiveFailure(check, overridden));
        var summary = "<p>Recorded checks: " + rows.Length + "; failed: " + failed + ".</p>";
        var visible = Detail("requirements") ? rows
            : Detail("findings") ? rows.Where(check => IsEffectiveFailure(check, overridden)).ToArray() : [];
        return summary + string.Join("", visible.Select(check => Check(check, overridden.Contains(Field(check, "requirementId")))));
    }

    private static HashSet<string> OverriddenRequirements(JsonElement scenario)
    {
        if (!scenario.TryGetProperty("requirements", out var requirements))
            return [];
        return requirements.EnumerateArray().Where(row => Field(row, "status") == "overridden")
            .Select(row => Field(row, "id")).ToHashSet(StringComparer.Ordinal);
    }

    private static bool IsEffectiveFailure(JsonElement check, HashSet<string> overridden) =>
        Field(check, "status") == "failed" && !overridden.Contains(Field(check, "requirementId"));

    private string Check(JsonElement check, bool overridden)
    {
        var body = "<details><summary>" + Safe(Field(check, "subject")) + ": "
            + Encoded(Field(check, "status")) + "</summary>";
        if (overridden)
            body += "<p>Historical observation: testing instructions override this requirement. See the requirement mapping for the effective decision.</p>";
        foreach (var field in new[] { "source", "requirementId", "expected", "observed", "reason", "instructionQuote" })
            body += "<p>" + Encoded(field) + ": " + (field is "source" or "requirementId"
                ? Encoded(Field(check, field)) : Safe(Field(check, field))) + "</p>";
        if (check.TryGetProperty("screenshot", out var screenshot))
            body += "<p><a href=\"" + Encoded(screenshot.ToString()) + "\">Check evidence</a></p>";
        return body + "</details>";
    }

    private string Step(JsonElement step)
    {
        var action = step.TryGetProperty("action", out var value)
            ? value.ValueKind == JsonValueKind.Object ? Field(value, "action") : value.ToString() : "check";
        var body = "<li><p>" + Encoded(action) + ": " + Safe(Field(step, "observation")) + "</p>"
            + Notes(step, ["controlLabel", "observedOutcome", "actionError", "crash", "recovery", "navigation", "evidenceError"]);
        if (step.TryGetProperty("screenshot", out var screenshot))
            body += Image(screenshot.ToString());
        return body + "</li>";
    }

    private string Image(string path) => "<a href=\"" + Encoded(path) + "\"><img loading=\"lazy\" src=\""
        + Encoded(path) + "\" alt=\"Step evidence\"></a>";

    private string Notes(JsonElement item, IEnumerable<string> keys)
    {
        return string.Join("", keys.Where(key => item.TryGetProperty(key, out var value) && value.ValueKind != JsonValueKind.Null)
            .Select(key => "<p>" + Safe(item.GetProperty(key).ToString()) + "</p>"));
    }

    private static string Details(string title, string value) => "<details><summary>" + Encoded(title)
        + "</summary><pre>" + Encoded(value) + "</pre></details>";

    private bool Detail(string section) => configuration.Root.Get("reports")?.Get("sections")?.List is not { } sections
        || sections.Any(item => item.Text == section);

    // Encode only after redaction so both secrets and HTML text remain safe.
    private string Safe(string value) => WebUtility.HtmlEncode(configuration.Scrub(value));
    private static string Encoded(string value) => WebUtility.HtmlEncode(value);

    private static string Field(JsonElement item, string key, string fallback = "") =>
        item.ValueKind == JsonValueKind.Object && item.TryGetProperty(key, out var field) ? field.ToString() : fallback;
}
