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
    public string Render(RunState state, RunOutcome outcome, JsonElement? execution, RequirementCoverage? coverage = null)
    {
        return PageStart + Header(state, outcome) + Stages(state.Stages) + Inputs(state.Report)
            + new RequirementHtmlRenderer(configuration).Render(coverage, state.RequirementHeadings) + Execution(execution) + "<p><a href=\"result.json\">Machine-readable run result</a></p></html>";
    }

    private string Header(RunState state, RunOutcome outcome)
    {
        return "<h1>CIMT application test</h1><p>Exit: " + outcome.ExitCode
            + " · Verdict: " + Safe(outcome.Verdict) + " · Completion: " + Safe(outcome.Completion) + "</p>"
            + "<p>Run: " + Safe(state.Identity.Id) + " (UTC)</p>"
            + "<p>Branch: " + Safe(state.Configuration.Root.Get("repository")!.Value("branch")!)
            + " · Commit: " + Safe(state.Commit) + "</p><h2>Stopping reasons and coverage limits</h2><ul>"
            + string.Join("", state.Errors.Select(error => "<li>" + Safe(error) + "</li>"))
            + "</ul><p>Only recorded target/device/control paths were exercised. This report does not prove coverage of every possible application state.</p>";
    }

    private string Stages(IEnumerable<object> stages)
    {
        return "<h2>Build stages</h2><ul>" + string.Join("", stages.Select(Stage)) + "</ul>";
    }

    private string Stage(object stage)
    {
        var item = JsonSerializer.SerializeToElement(stage);
        var description = Field(item, "stage") + " " + Field(item, "target") + " "
            + Field(item, "platform") + ": " + Field(item, "result");
        var log = Detail("diagnostics") && item.TryGetProperty("log", out var path)
            ? " — <a href=\"" + Safe(path.ToString()) + "\">build log</a>" : "";
        return "<li>" + Safe(description) + log + "</li>";
    }

    private string Inputs(string report)
    {
        var file = Path.Combine(report, "inputs.json");
        return Detail("requirements") && File.Exists(file)
            ? Details("Testing instructions and requirements", File.ReadAllText(file)) : "";
    }

    private string Execution(JsonElement? execution)
    {
        if (execution is not { } value)
            return "<p>No application UI interaction result was produced.</p>";
        var body = "<h2>Device scenarios and coverage</h2>"
            + string.Join("", value.GetProperty("devices").EnumerateArray().Select(Device));
        if (value.TryGetProperty("budget", out var budget))
            body += "<h2>AI budget accounting</h2><pre>" + Safe(budget.ToString()) + "</pre>";
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
        var body = "<h4>" + Safe(Field(scenario, "target")) + " — "
            + Safe(Field(scenario, "verdict", "inconclusive")) + " / " + Safe(Field(scenario, "completion")) + "</h4>";
        body += Coverage(scenario) + Findings(scenario) + Checks(scenario);
        if (scenario.TryGetProperty("remaining", out var remaining) && remaining.GetArrayLength() > 0)
            body += "<p>Remaining/blocked work:</p><pre>" + Safe(remaining.ToString()) + "</pre>";
        if (Detail("interpretations") && scenario.TryGetProperty("interpretation", out var interpretation))
            body += "<p>Interpretation: " + Safe(interpretation.ToString()) + "</p>";
        if (Detail("scenarios"))
            body += "<details open><summary>Steps and observed behaviour</summary><ol>"
                + string.Join("", scenario.GetProperty("steps").EnumerateArray().Select(Step)) + "</ol></details>";
        return body;
    }

    private string Coverage(JsonElement scenario)
    {
        if (!scenario.TryGetProperty("coverage", out var coverage))
            return "";
        return "<p>Observed control/state combinations: " + Safe(Field(coverage, "observedControls", "0"))
            + "; activated: " + Safe(Field(coverage, "attemptedControls", "0"))
            + "; outstanding: " + Safe(Field(coverage, "outstandingObservedControls", "0")) + ".</p>";
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
            + Safe(Field(check, "status")) + "</summary>";
        if (overridden)
            body += "<p>Historical observation: testing instructions override this requirement. See the requirement mapping for the effective decision.</p>";
        foreach (var field in new[] { "source", "requirementId", "expected", "observed", "reason", "instructionQuote" })
            body += "<p>" + Safe(field) + ": " + Safe(Field(check, field)) + "</p>";
        if (check.TryGetProperty("screenshot", out var screenshot))
            body += "<p><a href=\"" + Safe(screenshot.ToString()) + "\">Check evidence</a></p>";
        return body + "</details>";
    }

    private string Step(JsonElement step)
    {
        var action = step.TryGetProperty("action", out var value)
            ? value.ValueKind == JsonValueKind.Object ? Field(value, "action") : value.ToString() : "check";
        var body = "<li><p>" + Safe(action + ": " + Field(step, "observation")) + "</p>"
            + Notes(step, ["actionError", "crash", "recovery", "navigation", "evidenceError"]);
        if (step.TryGetProperty("screenshot", out var screenshot))
            body += Image(screenshot.ToString());
        return body + "</li>";
    }

    private string Image(string path) => "<a href=\"" + Safe(path) + "\"><img loading=\"lazy\" src=\""
        + Safe(path) + "\" alt=\"Step evidence\"></a>";

    private string Notes(JsonElement item, IEnumerable<string> keys)
    {
        return string.Join("", keys.Where(key => item.TryGetProperty(key, out var value) && value.ValueKind != JsonValueKind.Null)
            .Select(key => "<p>" + Safe(item.GetProperty(key).ToString()) + "</p>"));
    }

    private string Details(string title, string value) => "<details><summary>" + Safe(title)
        + "</summary><pre>" + Safe(value) + "</pre></details>";

    private bool Detail(string section) => configuration.Root.Get("reports")?.Get("sections")?.List is not { } sections
        || sections.Any(item => item.Text == section);

    // Encode only after redaction so both secrets and HTML text remain safe.
    private string Safe(string value) => WebUtility.HtmlEncode(configuration.Scrub(value));

    private static string Field(JsonElement item, string key, string fallback = "") =>
        item.ValueKind == JsonValueKind.Object && item.TryGetProperty(key, out var field) ? field.ToString() : fallback;
}
