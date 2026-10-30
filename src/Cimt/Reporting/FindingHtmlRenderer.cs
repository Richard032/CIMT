using System.Text.Json;
using static Cimt.ReportHtml;

namespace Cimt;

/// <summary>Keeps readable failure evidence available independently of optional detail.</summary>
public sealed class FindingHtmlRenderer(Configuration configuration, ReportEvidence evidence)
{
    public string Render(IReadOnlyList<ReportScenario> scenarios)
    {
        var cards = scenarios.SelectMany(context => context.Crashes.Select(crash => Crash(context, crash))
            .Concat(Rows(context.Result, "checks").Where(check => ReportChecks.Failed(context.Result, check))
                .Select(check => Check(context, check)))
            .Concat(Rows(context.Result, "requirements").Where(row => Field(row, "status") == "failed"
                && !Rows(context.Result, "checks").Any(check => Field(check, "requirementId") == Field(row, "id")
                    && ReportChecks.Failed(context.Result, check))).Select(row => Check(context, row)))).ToArray();
        return "<div data-filter-area>" + Filters("findings")
            + (cards.Length == 0 ? "<p>No effective application failures were recorded. This does not establish that testing passed.</p>" : string.Join("", cards))
            + "</div>" + string.Join("", scenarios.Select(Rejected));
    }

    private string Crash(ReportScenario context, JsonElement crash)
    {
        var step = context.FindStep(Field(crash, "step"));
        var title = step is { } record ? Field(record.Step, "controlLabel", "Application termination") : "Application termination";
        return CardStart(context, title, Field(crash, "kind", "termination observation"))
            + "<p>Observed trigger: " + Safe(Field(crash, "point", "not recorded")) + "</p>"
            + "<p>Matching attempt at this point: " + Encode(Field(crash, "matchingAttempt", "not recorded")) + ". A shared root cause is not established.</p>"
            + Evidence(context, crash) + Reproduction(crash)
            + (Rows(crash, "diagnostics").Length == 0 ? "<p>No matching native crash diagnostic was recorded.</p>"
                : Details("Native crash diagnostics", "<pre>" + Encode(crash.GetProperty("diagnostics").ToString()) + "</pre>")) + "</article>";
    }

    private string Check(ReportScenario context, JsonElement check) =>
        CardStart(context, Field(check, "subject", "Requirement " + Field(check, "id", "check failed")), "failed")
        + "<dl>" + Row("Check source", Field(check, "source", "requirements")) + Row("Requirement ID", Field(check, "requirementId", Field(check, "id")))
        + TextRow("Expected", Field(check, "expected")) + TextRow("Observed", Field(check, "observed"))
        + TextRow("Explanation", Field(check, "reason")) + "</dl>" + Evidence(context, check) + "</article>";

    private string CardStart(ReportScenario context, string title, string status) =>
        "<article class=\"finding\"" + Attributes(context.DeviceLabel, context.Target, status) + "><h3>" + Safe(title)
        + "</h3><p>" + Encode(context.Label) + "</p>" + Badge(status);

    private string Evidence(ReportScenario context, JsonElement record)
    {
        var stepId = Field(record, "step");
        var step = context.FindStep(stepId);
        var screenshot = Field(record, "screenshot", step is { } found ? Field(found.Step, "screenshot") : "");
        return "<p>" + context.StepLink(stepId) + "</p>" + (screenshot.Length == 0 ? "<p>No screenshot reference was recorded for this finding.</p>"
            : "<p>" + evidence.ImageLink(screenshot, context.Label + " / "
                + (Field(record, "screenshot").Length > 0 ? "check evidence / " : "") + "recorded step " + stepId,
                context.Anchor + (Field(record, "screenshot").Length > 0 ? "-checks" : "")) + "</p>");
    }

    private string Reproduction(JsonElement crash)
    {
        var rows = Rows(crash, "reproductionSteps");
        return rows.Length == 0 ? "<p>Reproduction actions were not recorded.</p>" : Details("Recorded reproduction actions",
            "<ol>" + string.Join("", rows.Select(action => "<li>" + Safe(string.Join(" · ", new[] { "action", "controlLabel", "ref", "direction", "text", "credential", "field" }
                .Select(key => Field(action, key)).Where(value => value.Length > 0))) + "</li>")) + "</ol>");
    }

    private string Rejected(ReportScenario context)
    {
        var rows = Rows(context.Result, "rejectedResponses");
        if (rows.Length == 0)
            return "";
        return "<h3>Unaccepted AI responses</h3><p>" + Encode(context.Label)
            + ". These responses failed validation. Their proposed actions were not executed, and their observations are unverified and are not used for the test verdict.</p>"
            + string.Join("", rows.Select(row => Details("Attempt " + Field(row, "attempt") + ": " + Field(row, "error"),
                "<pre>" + Encode(row.ToString()) + "</pre>" + (Field(row, "screenshot").Length == 0
                    ? "<p>No screenshot was saved for this rejected response.</p>"
                    : evidence.Image(Field(row, "screenshot"), context.Label + " / rejected response attempt " + Field(row, "attempt")
                        + " / decision step " + Field(row, "step", "not recorded"), context.Anchor + "-rejected")))));
    }

    private string TextRow(string label, string value) => "<dt>" + Encode(label) + "</dt><dd>" + Safe(value) + "</dd>";
    private string Safe(string value) => Encode(configuration.Scrub(value));
}
