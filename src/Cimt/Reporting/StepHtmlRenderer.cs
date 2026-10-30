using System.Text.Json;
using static Cimt.ReportHtml;

namespace Cimt;

/// <summary>Displays exact saved step identities and their observed evidence.</summary>
public sealed class StepHtmlRenderer(Configuration configuration, ReportEvidence evidence)
{
    public string Render(ReportScenario context)
    {
        var steps = context.Steps;
        return "<div data-filter-area>" + Filters("recorded steps")
            + (steps.Length == 0 ? "<p>No steps were recorded for this scenario.</p>"
                : string.Join("", steps.Select((step, index) => Step(context, step, index)))) + "</div>";
    }

    private string Step(ReportScenario context, JsonElement step, int index)
    {
        var id = Field(step, "step");
        var title = (id.Length == 0 ? "Unnumbered record" : "Step " + id) + " — " + ReportScenario.Action(step);
        var status = Field(step, "crash").Length > 0 ? Field(step, "crash")
            : Field(step, "actionError").Length > 0 ? "action error" : "recorded";
        var body = "<details id=\"" + context.StepAnchor(index) + "\""
            + Attributes(context.DeviceLabel, context.Target, status) + "><summary>" + Encode(title)
            + " — " + Safe(Field(step, "controlLabel")) + " " + Badge(status) + "</summary>";
        body += "<dl>" + Note(step, "observation", "Decision observation")
            + Note(step, "observedOutcome", "Observed outcome") + Note(step, "actionError", "Action error")
            + Note(step, "crash", "Crash/termination evidence") + Note(step, "recovery", "Recovery")
            + Note(step, "navigation", "Navigation") + Note(step, "evidenceError", "Unavailable evidence") + "</dl>";
        if (Field(step, "screenshot").Length > 0)
            body += evidence.Image(Field(step, "screenshot"), context.Label + " / " + (id.Length == 0 ? "unnumbered record" : "step " + id), context.Anchor);
        else
            body += "<p>No screenshot was saved for this record.</p>";
        return body + "</details>";
    }

    private string Note(JsonElement step, string key, string label) => Field(step, key).Length == 0 ? ""
        : "<dt>" + Encode(label) + "</dt><dd>" + Safe(Field(step, key)) + "</dd>";

    private string Safe(string value) => Encode(configuration.Scrub(value));
}
