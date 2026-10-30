using static Cimt.ReportHtml;

namespace Cimt;

/// <summary>Embeds fixed presentation assets so a moved report works without a server.</summary>
public static class ReportPage
{
    private static readonly Lazy<string> Styles = new(() => Asset("report.css"));
    private static readonly Lazy<string> Script = new(() => Asset("report.js"));

    public static string Start(string command, string id) => "<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\">"
        + "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\"><title>CIMT " + Encode(command) + " — "
        + Encode(id) + "</title><style>" + Styles.Value + "</style></head><body>";

    public const string Navigation = "<nav class=\"report-nav\" aria-label=\"Report sections\"><a href=\"#overview\">Overview</a>"
        + "<a href=\"#findings\">Findings</a><a href=\"#devices\">Devices</a><a href=\"#requirements\">Requirements</a><a href=\"#activity\">Activity</a></nav>";

    public static string End => "<dialog id=\"evidence-viewer\" aria-labelledby=\"evidence-title\"><div class=\"viewer-toolbar\">"
        + "<h2 id=\"evidence-title\">Screenshot evidence</h2><button type=\"button\" data-viewer=\"close\">Close evidence</button></div>"
        + "<p id=\"evidence-caption\" aria-live=\"polite\"></p><div class=\"viewer-image\"><img alt=\"\"></div>"
        + "<div class=\"viewer-toolbar\"><button type=\"button\" data-viewer=\"previous\">Previous screenshot</button>"
        + "<button type=\"button\" data-viewer=\"zoom\" aria-pressed=\"false\">Zoom image</button><button type=\"button\" data-viewer=\"next\">Next screenshot</button>"
        + "<a data-viewer=\"original\" target=\"_blank\" rel=\"noopener\">Open original image</a></div></dialog>"
        + "<script type=\"text/javascript\">" + Script.Value + "</script></body></html>";

    private static string Asset(string name)
    {
        using var stream = typeof(ReportPage).Assembly.GetManifestResourceStream("cimt.Reporting.Assets." + name)
            ?? throw new InvalidOperationException("Report asset missing: " + name);
        using var reader = new StreamReader(stream);
        return reader.ReadToEnd();
    }
}
