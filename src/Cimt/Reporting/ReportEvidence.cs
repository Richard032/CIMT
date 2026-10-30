using static Cimt.ReportHtml;

namespace Cimt;

/// <summary>Creates contained local evidence links and explains unavailable files.</summary>
public sealed class ReportEvidence(string report)
{
    public string? RelativePath(string path)
    {
        try
        {
            if (string.IsNullOrWhiteSpace(path) || Path.IsPathRooted(path) || Uri.TryCreate(path, UriKind.Absolute, out _))
                return null;
            var full = Path.GetFullPath(path, report);
            RunFolderSafety.Inside(report, full);
            return File.Exists(full) ? string.Join("/", Path.GetRelativePath(report, full)
                .Split(Path.DirectorySeparatorChar).Select(Uri.EscapeDataString)) : null;
        }
        catch (Exception error) when (error is ConfigurationException or ArgumentException or IOException or UnauthorizedAccessException)
        {
            return null;
        }
    }

    public string Link(string path, string label) => RelativePath(path) is { } href
        ? "<a href=\"" + Encode(href) + "\">" + Encode(label) + "</a>"
        : "<span>" + Encode(label) + ": unavailable or outside this report (" + Encode(path) + ")</span>";

    public string ImageLink(string path, string caption, string group) => PngPath(path) is { } href
        ? "<a class=\"evidence-link\" data-gallery=\"" + Encode(group) + "\" data-caption=\"" + Encode(caption)
            + "\" href=\"" + Encode(href) + "\">View screenshot — " + Encode(caption) + "</a>"
        : "<span>Screenshot unavailable or rejected: " + Encode(path) + "</span>";

    public string Image(string path, string caption, string group)
    {
        var href = PngPath(path);
        if (href is null)
            return "<p>Screenshot unavailable or rejected: " + Encode(path) + ". " + Encode(caption) + "</p>";
        // The normal link still works when the browser cannot open the optional viewer.
        return "<figure><a class=\"evidence-link\" data-gallery=\"" + Encode(group) + "\" href=\"" + Encode(href)
            + "\"><img loading=\"lazy\" src=\"" + Encode(href) + "\" alt=\"" + Encode(caption)
            + "\"></a><figcaption>" + Encode(caption) + "</figcaption></figure>";
    }

    private string? PngPath(string path) => Path.GetExtension(path).Equals(".png", StringComparison.OrdinalIgnoreCase)
        ? RelativePath(path) : null;
}
