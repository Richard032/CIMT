using System.Text.Json;
using static Cimt.ReportHtml;

namespace Cimt;

/// <summary>Shows recorded plans and navigation without treating visits as passed tests.</summary>
public sealed class PlanningHtmlRenderer(Configuration configuration)
{
    public string Render(ReportScenario context)
    {
        var scenario = context.Result;
        if (!scenario.TryGetProperty("testPlan", out var plan))
            return "";
        var redactor = new PlanningRedactor(new JsonTextRedactor(configuration.Scrub));
        plan = JsonSerializer.SerializeToElement(redactor.Plan(plan));
        var body = "<h4>Testing plan</h4><p>Instructions define scope; requirements define expected behavior. "
            + "Visited paths do not prove passed tests. Tested tasks can have failed results.</p>";
        body += Table("Source-linked testing tasks", ["Task", "Source", "Work status", "Test result", "Expected behavior", "Reason"],
            Rows(plan, "tasks").Select(task => new[] { Field(task, "subject"), Source(task), Field(task, "status"),
                Field(task, "result"), Field(task, "expected"), Field(task, "reason") }));
        if (!scenario.TryGetProperty("exploration", out var exploration))
            return body;
        exploration = JsonSerializer.SerializeToElement(redactor.Exploration(exploration));
        var paths = Rows(exploration, "paths");
        body += "<h4>Discovered application paths</h4><p>" + paths.Count(row => Field(row, "attempts", "0") != "0")
            + " visited; " + paths.Count(row => Field(row, "scope") == "out of scope")
            + " outside scope. Unclassified paths still need a scope decision. Counts describe discovered paths only.</p>";
        body += Details("Path scope and observed outcomes", Table("Discovered paths", ["Control", "Input kind", "Scope", "Attempts", "Outcome", "Scope reason"],
            paths.Select(path => new[] { Field(path, "label"), Field(path, "kind"), Field(path, "scope"),
                Field(path, "attempts"), Field(path, "lastOutcome", "Not visited"), Field(path, "reason") })));
        if (exploration.TryGetProperty("applicationMap", out var map))
        {
            body += "<h4>Observed application map</h4><p>" + Rows(map, "states").Length + " states and "
                + Rows(map, "transitions").Length + " recorded transitions. Configuration is last-observed context, "
                + "not proof of persistence or correct behavior.</p>";
            body += Details("States, configuration and transitions", Table("Observed states", ["State", "Screen", "Last-observed configuration"],
                Rows(map, "states").Select(state => new[] { Field(state, "id"), Field(state, "label"), Settings(state) }))
                + Table("Observed transitions", ["From", "To", "Action", "Observation", "Observation completed"],
                    Rows(map, "transitions").Select(edge => new[] { Field(edge, "source"), Field(edge, "destination"),
                        Field(edge, "action"), Field(edge, "outcome"), Field(edge, "verified") })));
        }
        return body;
    }

    private static string Source(JsonElement task) => Field(task, "source") == "requirements"
        ? "Requirement " + Field(task, "requirementId") : "Instructions: " + Field(task, "instructionQuote");

    private static string Settings(JsonElement state) => state.TryGetProperty("configuration", out var settings)
        ? string.Join("; ", settings.EnumerateObject().Select(setting => setting.Name + " = " + Field(setting.Value, "value")
            + " (observed at " + Field(setting.Value, "observedAt") + ")")) : "";

    private string Table(string caption, string[] headings, IEnumerable<string[]> rows) =>
        "<table><caption>" + Encode(caption) + "</caption><thead><tr>"
        + string.Join("", headings.Select(heading => "<th scope=\"col\">" + Encode(heading) + "</th>"))
        + "</tr></thead><tbody>" + string.Join("", rows.Select(row => "<tr>"
            + string.Join("", row.Select(cell => "<td>" + Encode(cell) + "</td>")) + "</tr>")) + "</tbody></table>";
}
