using System.Text.Json;
using static Cimt.ReportHtml;

namespace Cimt;

/// <summary>Presents device-scoped outcomes, remaining work, checks and step detail.</summary>
public sealed class ScenarioHtmlRenderer(Configuration configuration, ReportEvidence evidence)
{
    public string Render(IReadOnlyList<ReportScenario> scenarios)
    {
        return "<section id=\"devices\" aria-labelledby=\"devices-title\"><h2 id=\"devices-title\">Devices</h2>"
            + "<div data-filter-area>" + Filters("device scenarios")
            + (scenarios.Count == 0 ? "<p>No application UI interaction result was produced. Review preparation and stopping reasons.</p>"
                : string.Join("", scenarios.Select(Scenario))) + "</div></section>";
    }

    private string Scenario(ReportScenario context)
    {
        var scenario = context.Result;
        var body = "<article id=\"" + context.Anchor + "\" class=\"scenario\""
            + Attributes(context.DeviceLabel, context.Target, Field(scenario, "verdict", "inconclusive")) + ">"
            + "<h3>" + Encode(context.Label) + "</h3><p>" + Badge(Field(scenario, "verdict", "inconclusive"))
            + " " + Badge(Field(scenario, "completion", "incomplete")) + "</p>";
        body += "<p>Device actions: " + context.ActionCount + "; recorded steps: " + context.Steps.Length
            + "; confirmed crashes: " + context.ConfirmedCrashes + "; suspected terminations: " + context.SuspectedTerminations + ".</p>";
        body += Remaining(scenario) + new PlanningHtmlRenderer(configuration).Render(context)
            + Coverage(scenario) + Checks(context) + Exploration(scenario);
        if (Detail("interpretations") && Field(scenario, "interpretation").Length > 0)
            body += "<p>Interpretation: " + Safe(Field(scenario, "interpretation")) + "</p>";
        if (!context.Steps.Any(step => Field(step, "screenshot").Length > 0)
            && !Rows(scenario, "rejectedResponses").Any(row => Field(row, "screenshot").Length > 0))
            body += "<p>No verified screenshot was saved for this scenario. See failures and stopping reasons.</p>";
        // Exact records remain reachable from mandatory failures even when optional detail is disabled.
        body += Details("Steps and observed behaviour", new StepHtmlRenderer(configuration, evidence).Render(context));
        return body + "</article>";
    }

    private string Remaining(JsonElement scenario)
    {
        var remaining = Rows(scenario, "remaining");
        return "<h4>Remaining/blocked work:</h4><p>Latest recorded worker plan for this device/scenario; not a whole-run task inventory.</p>"
            + (remaining.Length == 0 ? "<p>" + (Field(scenario, "completion") == "complete"
                ? "No remaining work was recorded." : "Testing objective has not finished; coverage is not confirmed.") + "</p>"
                : "<ul>" + string.Join("", remaining.Select(item => "<li>" + Safe(item.ToString()) + "</li>")) + "</ul>");
    }

    private string Coverage(JsonElement scenario)
    {
        if (!scenario.TryGetProperty("coverage", out var coverage))
            return "";
        return "<h4>Recorded control coverage</h4><p>Observed control/state combinations: "
            + Encode(Field(coverage, "observedControls", "not recorded")) + "; activated: "
            + Encode(Field(coverage, "attemptedControls", "not recorded")) + "; outstanding: "
            + Encode(Field(coverage, "outstandingObservedControls", "not recorded"))
            + ". These are combinations, not distinct buttons or an application coverage percentage.</p>";
    }

    private string Checks(ReportScenario context)
    {
        var checks = Rows(context.Result, "checks");
        var failed = checks.Count(check => ReportChecks.Failed(context.Result, check));
        var body = "<p>Recorded checks: " + checks.Length + "; failed: " + failed + ".</p>";
        if (!Detail("requirements"))
            return body;
        return body + string.Join("", checks.Where(check => !ReportChecks.Failed(context.Result, check)).Select(check => Check(context, check)));
    }

    private string Check(ReportScenario context, JsonElement check)
    {
        var body = ReportChecks.Overridden(context.Result, check)
            ? "<p>Historical observation: testing instructions override this requirement.</p>" : "";
        body += "<dl>" + CheckFields(check) + "</dl>" + context.StepLink(Field(check, "step"));
        if (Field(check, "screenshot").Length > 0)
            body += "<p>" + evidence.ImageLink(Field(check, "screenshot"), context.Label + " / check evidence / step "
                + Field(check, "step", "not recorded"), context.Anchor + "-checks") + "</p>";
        return Details(Field(check, "subject") + ": " + Field(check, "status"), body);
    }

    private string CheckFields(JsonElement check) => string.Join("", new[] { "source", "requirementId", "expected", "observed", "reason", "instructionQuote" }
        .Select(key => "<dt>" + Encode(key) + "</dt><dd>" + (key is "source" or "requirementId" ? Encode(Field(check, key)) : Safe(Field(check, key))) + "</dd>"));

    private string Exploration(JsonElement scenario)
    {
        if (!Detail("scenarios") || !scenario.TryGetProperty("exploration", out var value))
            return "";
        return Details("Exploration memory and observed outcomes", "<pre>" + Encode(value.ToString()) + "</pre>");
    }

    private bool Detail(string section) => configuration.Root.Get("reports")?.Get("sections")?.List is not { } sections
        || sections.Any(item => item.Text == section);
    private string Safe(string value) => Encode(configuration.Scrub(value));
}
