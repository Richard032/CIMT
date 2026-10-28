using System.Net;

namespace Cimt;

/// <summary>Always shows the complete requirement matrix and its source text.</summary>
public sealed class RequirementHtmlRenderer(Configuration configuration)
{
    public string Render(RequirementCoverage? coverage)
    {
        if (coverage is null || coverage.Requirements.Count == 0)
            return "<h2>Requirement mapping</h2><p>No requirements were supplied.</p>";
        var body = "<h2>Requirement mapping</h2><p>Catalogue items: " + coverage.Requirements.Count
            + ". Each item retains its original text; all conditions in an item must be checked.</p>";
        body += "<p>Redacted source snapshot SHA-256: " + Safe(coverage.SourceSha256) + ".</p>";
        return body + string.Join("", coverage.Requirements.Select(Requirement));
    }

    private string Requirement(RequirementSummary summary)
    {
        var definition = summary.Definition;
        return "<h3>" + Safe(definition.Id) + " — " + Safe(summary.Status) + "</h3>"
            + "<p>Requirement source lines " + definition.StartLine + "–" + definition.EndLine + ".</p>"
            + "<pre>" + Safe(definition.Text) + "</pre>"
            + string.Join("", summary.Results.Select(Result));
    }

    private string Result(RequirementAssessment row)
    {
        var body = "<details open><summary>" + Safe(row.Scope.Target + " / " + row.Scope.Platform + " / "
            + row.Scope.DeviceName + ": " + row.Status) + "</summary>";
        body += Paragraph("Expected", row.Expected) + Paragraph("Observed", row.Observed)
            + Paragraph("Explanation", row.Reason) + Paragraph("Instruction taking priority", row.InstructionQuote);
        if (row.Step.HasValue)
            body += "<p>Recorded step: " + row.Step + ".</p>";
        if (!string.IsNullOrEmpty(row.Screenshot))
            body += "<p><a href=\"" + Safe(row.Screenshot) + "\">Requirement evidence</a></p>";
        return body + Paragraph("Unavailable evidence", row.EvidenceError) + "</details>";
    }

    private string Paragraph(string label, string value) => string.IsNullOrEmpty(value) ? ""
        : "<p>" + Safe(label) + ": " + Safe(value) + "</p>";
    private string Safe(string value) => WebUtility.HtmlEncode(configuration.Scrub(value));
}
