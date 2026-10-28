using System.Net;

namespace Cimt;

/// <summary>Always shows the complete requirement matrix and its source text.</summary>
public sealed class RequirementHtmlRenderer(Configuration configuration)
{
    public string Render(RequirementCoverage? coverage, IReadOnlyList<RequirementHeading>? headings = null)
    {
        var context = Headings(headings ?? []);
        if (coverage is null || coverage.Requirements.Count == 0)
            return "<h2>Requirement mapping</h2>" + context + (headings?.Count > 0
                ? "<p>Only document headings were supplied; there are no requirement entries to evaluate.</p>"
                : "<p>No requirements were supplied.</p>");
        var body = "<h2>Requirement mapping</h2><p>Catalogue items: " + coverage.Requirements.Count
            + ". Each item retains its original text; all conditions in an item must be checked.</p>";
        body += "<p>Redacted source snapshot SHA-256: " + Encoded(coverage.SourceSha256) + ".</p>";
        return body + context + string.Join("", coverage.Requirements.Select(Requirement));
    }

    private string Headings(IReadOnlyList<RequirementHeading> headings)
    {
        if (headings.Count == 0)
            return "";
        return "<h3>Document headings (context)</h3><p>Headings have no test status and do not block completion.</p>"
            + string.Join("", headings.Select(heading => "<p>Source lines " + heading.StartLine + "–"
                + heading.EndLine + ".</p><pre>" + Safe(heading.Text) + "</pre>"));
    }

    private string Requirement(RequirementSummary summary)
    {
        var definition = summary.Definition;
        return "<h3>" + Encoded(definition.Id) + " — " + Encoded(summary.Status) + "</h3>"
            + "<p>Requirement source lines " + definition.StartLine + "–" + definition.EndLine + ".</p>"
            + Paragraph("Section context", definition.HeadingContext)
            + "<pre>" + Safe(definition.Text) + "</pre>"
            + string.Join("", summary.Results.Select(Result));
    }

    private string Result(RequirementAssessment row)
    {
        var body = "<details open><summary>" + Encoded(row.Scope.Target + " / " + row.Scope.Platform + " / ")
            + Safe(row.Scope.DeviceName) + ": " + Encoded(row.Status) + "</summary>";
        body += Paragraph("Expected", row.Expected) + Paragraph("Observed", row.Observed)
            + Paragraph("Explanation", row.Reason) + Paragraph("Instruction taking priority", row.InstructionQuote);
        if (row.Step.HasValue)
            body += "<p>Recorded step: " + row.Step + ".</p>";
        if (!string.IsNullOrEmpty(row.Screenshot))
            body += "<p><a href=\"" + Encoded(row.Screenshot) + "\">Requirement evidence</a></p>";
        return body + Paragraph("Unavailable evidence", row.EvidenceError) + "</details>";
    }

    private string Paragraph(string label, string value) => string.IsNullOrEmpty(value) ? ""
        : "<p>" + Encoded(label) + ": " + Safe(value) + "</p>";
    private string Safe(string value) => WebUtility.HtmlEncode(configuration.Scrub(value));
    private static string Encoded(string value) => WebUtility.HtmlEncode(value);
}
