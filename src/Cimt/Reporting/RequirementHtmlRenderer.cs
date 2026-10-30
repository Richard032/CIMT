using System.Net;

namespace Cimt;

/// <summary>Always shows the complete requirement matrix and its source text.</summary>
public sealed class RequirementHtmlRenderer(Configuration configuration)
{
    public string Render(RequirementCoverage? coverage, IReadOnlyList<RequirementHeading>? headings = null,
        IReadOnlyList<ReportScenario>? scenarios = null, ReportEvidence? evidence = null)
    {
        var context = Headings(headings ?? []);
        if (coverage is null || coverage.Requirements.Count == 0)
            return "<h2>Requirement mapping</h2>" + context + (headings?.Count > 0
                ? "<p>Only document headings were supplied; there are no requirement entries to evaluate.</p>"
                : "<p>No requirements were supplied.</p>");
        var body = "<h2>Requirement mapping</h2><p>Catalogue items: " + coverage.Requirements.Count
            + ". Each item retains its original text; all conditions in an item must be checked.</p>";
        body += "<p>Redacted source snapshot SHA-256: " + Encoded(coverage.SourceSha256) + ".</p>";
        var totals = string.Join("; ", coverage.Requirements.GroupBy(row => row.Status).Select(group => group.Key + ": " + group.Count()));
        return body + "<p>Catalogue result summary: " + Encoded(totals) + ". Expand each device/target for its own decision.</p>" + context
            + "<div data-filter-area>" + ReportHtml.Filters("requirement results")
            + string.Join("", coverage.Requirements.Select(summary => Requirement(summary, scenarios ?? [], evidence))) + "</div>";
    }

    private string Headings(IReadOnlyList<RequirementHeading> headings)
    {
        if (headings.Count == 0)
            return "";
        return "<h3>Document headings (context)</h3><p>Headings have no test status and do not block completion.</p>"
            + string.Join("", headings.Select(heading => "<p>Source lines " + heading.StartLine + "–"
                + heading.EndLine + ".</p><pre>" + Safe(heading.Text) + "</pre>"));
    }

    private string Requirement(RequirementSummary summary, IReadOnlyList<ReportScenario> scenarios, ReportEvidence? evidence)
    {
        var definition = summary.Definition;
        return "<article data-filter-container><h3>" + Encoded(definition.Id) + " — " + Encoded(summary.Status) + "</h3>"
            + "<details><summary>Requirement source text</summary><p>Requirement source lines " + definition.StartLine + "–" + definition.EndLine + ".</p>"
            + Paragraph("Section context", definition.HeadingContext)
            + "<pre>" + Safe(definition.Text) + "</pre></details>"
            + string.Join("", summary.Results.Select(row => Result(row, scenarios, evidence))) + "</article>";
    }

    private string Result(RequirementAssessment row, IReadOnlyList<ReportScenario> scenarios, ReportEvidence? evidence)
    {
        var body = "<details" + ReportHtml.Attributes(row.Scope.Platform + " / " + configuration.Scrub(row.Scope.DeviceName) + " / " + row.Scope.DeviceId,
            row.Scope.Target, row.Status) + "><summary>" + Encoded(row.Scope.Target + " / " + row.Scope.Platform + " / ")
            + Safe(row.Scope.DeviceName) + ": " + Encoded(row.Status) + "</summary>";
        body += Paragraph("Expected", row.Expected) + Paragraph("Observed", row.Observed)
            + Paragraph("Explanation", row.Reason) + Paragraph("Instruction taking priority", row.InstructionQuote);
        if (row.Step.HasValue)
        {
            var matches = scenarios.Where(context => context.Target == row.Scope.Target && context.Platform == row.Scope.Platform
                && context.DeviceId == row.Scope.DeviceId && context.FindStep(row.Step.Value.ToString()) is not null).ToArray();
            body += "<p>" + (matches.Length == 1 ? matches[0].StepLink(row.Step.Value.ToString())
                : "Recorded step: " + row.Step + ". No unique saved step link is available.") + "</p>";
        }
        if (!string.IsNullOrEmpty(row.Screenshot))
        {
            var contexts = scenarios.Where(context => context.Target == row.Scope.Target && context.Platform == row.Scope.Platform
                && context.DeviceId == row.Scope.DeviceId).ToArray();
            var group = contexts.Length == 1 ? contexts[0].Anchor + "-checks" : "requirement-" + row.Screenshot;
            body += "<p>" + (evidence?.ImageLink(row.Screenshot, row.Scope.Platform + " / " + configuration.Scrub(row.Scope.DeviceName)
                + " / " + row.Scope.Target + " / requirement evidence / step " + (row.Step?.ToString() ?? "not recorded"), group)
                ?? "Requirement evidence: " + Encoded(row.Screenshot)) + "</p>";
        }
        return body + Paragraph("Unavailable evidence", row.EvidenceError) + "</details>";
    }

    private string Paragraph(string label, string value) => string.IsNullOrEmpty(value) ? ""
        : "<p>" + Encoded(label) + ": " + Safe(value) + "</p>";
    private string Safe(string value) => WebUtility.HtmlEncode(configuration.Scrub(value));
    private static string Encoded(string value) => WebUtility.HtmlEncode(value);
}
