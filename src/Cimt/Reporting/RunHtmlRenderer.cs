using System.Text.Json;
using static Cimt.ReportHtml;

namespace Cimt;

/// <summary>Composes a portable report from saved data without changing test outcomes.</summary>
public sealed class RunHtmlRenderer(Configuration configuration)
{
    public string Render(RunState state, RunOutcome outcome, JsonElement? execution, RequirementCoverage? coverage = null,
        IReadOnlyList<RunActivityEntry>? activity = null, bool inProgress = false)
    {
        // Redact parsed values first. Never run secret replacement over markup or scripts.
        JsonElement? safeExecution = execution is { } value
            ? JsonSerializer.SerializeToElement(new ExecutionRedactor(new JsonTextRedactor(configuration.Scrub)).Execution(value)) : null;
        var scenarios = ReportScenario.Read(safeExecution);
        var evidence = new ReportEvidence(state.Report);
        var diagnostics = new RunDiagnosticsRenderer(configuration);
        return ReportPage.Start(state.Command, state.Identity.Id) + Header(state, outcome, inProgress) + ReportPage.Navigation
            + "<main id=\"report-content\">" + diagnostics.Overview(state, outcome, safeExecution, scenarios)
            + "<section id=\"findings\" aria-labelledby=\"findings-title\"><h2 id=\"findings-title\">Findings</h2>"
            + new FindingHtmlRenderer(configuration, evidence).Render(scenarios) + diagnostics.Reasons(state, outcome, safeExecution) + "</section>"
            + new ScenarioHtmlRenderer(configuration, evidence).Render(scenarios)
            + "<section id=\"requirements\" aria-label=\"Requirements\">"
            + new RequirementHtmlRenderer(configuration).Render(coverage, state.RequirementHeadings, scenarios, evidence) + "</section>"
            + "<section id=\"activity\" aria-labelledby=\"activity-title\"><h2 id=\"activity-title\">Activity</h2>"
            + diagnostics.Timeline(state.Report, activity ?? RunActivityLog.Read(state.Report, configuration.Scrub))
            + Stages(state, evidence) + Inputs(state.Report) + Downloads(evidence) + "</section></main>" + ReportPage.End;
    }

    private string Header(RunState state, RunOutcome outcome, bool inProgress) =>
        "<a class=\"skip-link\" href=\"#report-content\">Skip to report content</a><header class=\"report-header\"><h1>CIMT application test</h1>"
        + "<p>Command: " + Encode(state.Command) + " · Run: " + Encode(state.Identity.Id) + " (UTC)</p>"
        + "<p>Branch: " + Encode(configuration.Root.Get("repository")?.Value("branch")) + " · Commit: " + Encode(state.Commit) + "</p>"
        + "<p>Exit: " + outcome.ExitCode + " · Verdict: " + Encode(outcome.Verdict) + " · Completion: " + Encode(outcome.Completion) + "</p>"
        + (inProgress ? "<p class=\"partial\"><strong>Partial report — run in progress or finalization interrupted.</strong> "
            + "Reload this page for newer saved observations. The run has not been confirmed complete.</p>" : "") + "</header>";

    private string Stages(RunState state, ReportEvidence evidence) => Details("Run stages and build provenance", "<ul>"
        + string.Join("", state.Stages.Select(stage => Stage(stage, evidence))) + "</ul>");

    private string Stage(object stage, ReportEvidence evidence)
    {
        var item = JsonSerializer.SerializeToElement(stage);
        var body = "<li>" + Encode(configuration.Scrub(string.Join(" / ", new[] { "stage", "target", "platform", "result" }.Select(key => Field(item, key)))));
        if (Field(item, "log").Length > 0)
            body += " — " + evidence.Link(Field(item, "log"), "Build log");
        return body + "</li>";
    }

    private string Inputs(string report)
    {
        var sections = configuration.Root.Get("reports")?.Get("sections")?.List;
        if (sections is not null && !sections.Any(section => section.Text == "requirements"))
            return "";
        var path = Path.Combine(report, "inputs.json");
        if (!File.Exists(path))
            return "";
        var inputs = JsonSerializer.Deserialize<JsonElement>(File.ReadAllText(path));
        var safe = new JsonTextRedactor(configuration.Scrub).Text(inputs);
        return Details("Testing instructions and requirements (redacted input snapshot)", "<pre>" + Encode(safe!.ToJsonString()) + "</pre>");
    }

    private static string Downloads(ReportEvidence evidence) => "<h3>Technical records</h3><ul>"
        + string.Join("", new[] { ("result.json", "Machine-readable run result"), ("ai-budget.json", "Conservative budget ledger"),
            ("logs/execution-worker.log", "Execution worker log"), ("logs/native-daemon.log", "Native helper log") }
            .Select(file => "<li>" + evidence.Link(file.Item1, file.Item2) + "</li>")) + "</ul>";
}
