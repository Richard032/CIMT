using System.Text.Json;
using static Cimt.ReportHtml;

namespace Cimt;

/// <summary>Shows complete observed batch paths separately from AI interpretations.</summary>
public sealed class BatchFeedbackHtmlRenderer(Configuration configuration, ReportEvidence evidence)
{
    public string Render(ReportScenario context)
    {
        var body = Warnings(context.Result);
        if (!context.Result.TryGetProperty("batchFeedback", out var feedback))
            return body;
        var batches = Rows(feedback, "batches");
        if (batches.Length == 0)
            return body;
        body += "<h4>Ordered batch results</h4><p>One initial observation is followed by each command and its result. "
            + "Unchanged steps and independent observations remain in order. Executed commands do not prove passed tests.</p>";
        foreach (var batch in batches)
            body += Batch(context, batch);
        return body;
    }

    private string Warnings(JsonElement scenario)
    {
        var warnings = Rows(scenario, "warnings");
        if (warnings.Length == 0)
            return "";
        return "<h4>Operating-system warnings</h4><p>ANR warnings alone do not establish a crash or end testing.</p>"
            + "<table><caption>Recorded warnings</caption><thead><tr><th scope=\"col\">ID</th><th scope=\"col\">UTC time</th>"
            + "<th scope=\"col\">Device</th><th scope=\"col\">Step</th><th scope=\"col\">Warning</th></tr></thead><tbody>"
            + string.Join("", warnings.Select(row => "<tr><td>" + Encode(Field(row, "id")) + "</td><td>" + Safe(Field(row, "timestamp"))
                + "</td><td>" + Safe(Field(row, "device")) + "</td><td>" + Encode(Field(row, "step"))
                + "</td><td>" + Badge("warning") + " " + Safe(Field(row, "message")) + "</td></tr>"))
            + "</tbody></table>";
    }

    private string Batch(ReportScenario context, JsonElement batch)
    {
        var observations = Rows(batch, "observations");
        var initial = observations.FirstOrDefault(row => Field(row, "id") == Field(batch, "initialObservation"));
        var body = "<h5>Batch " + Encode(Field(batch, "id")) + "</h5><p>Delivery: "
            + Encode(Field(batch, "delivery")) + ". Initial observation: " + Observation(initial) + ". "
            + Evidence(context, initial) + "</p>"
            + "<table><caption>Complete execution path</caption><thead><tr>"
            + string.Join("", new[] { "Order", "Command or event", "Target", "Execution state", "UI result", "Resulting observation", "Evidence", "Warnings or error" }
                .Select(name => "<th scope=\"col\">" + Encode(name) + "</th>")) + "</tr></thead><tbody>";
        var index = 0;
        foreach (var row in Rows(batch, "path"))
        {
            var observed = observations.FirstOrDefault(item => Field(item, "id") == Field(row, "observation"));
            var warningIds = row.TryGetProperty("warnings", out var ids) ? ids.ToString() : "[]";
            body += "<tr><td>" + index++ + "</td><td>" + Safe(Field(row, "action", "Independent observation"))
                + "</td><td>" + Target(row) + "</td><td>" + Encode(Field(row, "status", "observed"))
                + "</td><td>" + Encode(Field(row, "uiChange", "independent change"))
                + "</td><td>" + Observation(observed) + "</td><td>" + Evidence(context, observed)
                + "</td><td>" + Safe("Warnings: " + warningIds + "; " + Field(row, "error")) + "</td></tr>";
        }
        return body + "</tbody></table>";
    }

    private string Evidence(ReportScenario context, JsonElement observation)
    {
        if (observation.ValueKind == JsonValueKind.Undefined)
            return "Observation unavailable";
        var body = evidence.ImageLink(Field(observation, "screenshot"), "Observation " + Field(observation, "id"), context.Anchor);
        if (Field(observation, "ui").Length > 0)
            body += " " + evidence.Link(Field(observation, "ui"), "Masked UI record");
        return body;
    }

    private string Observation(JsonElement row) => row.ValueKind == JsonValueKind.Undefined
        ? "Observation unavailable" : Safe(Field(row, "id") + " (screen " + Field(row, "screen") + ")");

    private string Target(JsonElement row) => Safe(Field(row, "targetLabel"))
        + (row.TryGetProperty("target", out var target) ? " " + Safe(target.ToString()) : "");

    private string Safe(string text) => Encode(configuration.Scrub(text));
}
