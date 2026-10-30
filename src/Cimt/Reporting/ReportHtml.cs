using System.Globalization;
using System.Net;
using System.Text.Json;

namespace Cimt;

/// <summary>Shared text formatting for reports. Callers redact free text before encoding it.</summary>
public static class ReportHtml
{
    public static string Encode(string? text) => WebUtility.HtmlEncode(text ?? "");

    public static string Field(JsonElement value, string key, string fallback = "") =>
        value.ValueKind == JsonValueKind.Object && value.TryGetProperty(key, out var field)
        && field.ValueKind != JsonValueKind.Null ? field.ToString() : fallback;

    public static JsonElement[] Rows(JsonElement value, string key) =>
        value.ValueKind == JsonValueKind.Object && value.TryGetProperty(key, out var rows)
        && rows.ValueKind == JsonValueKind.Array ? rows.EnumerateArray().ToArray() : [];

    public static string Details(string title, string body) =>
        "<details><summary>" + Encode(title) + "</summary>" + body + "</details>";

    public static string Row(string label, string value) =>
        "<dt>" + Encode(label) + "</dt><dd>" + Encode(value) + "</dd>";

    public static string Badge(string status) => "<span class=\"status "
        + (status is "failed" or "confirmed crash report" ? "failure" : "") + "\">" + Encode(status) + "</span>";

    public static string Time(DateTimeOffset time) =>
        time.ToUniversalTime().ToString("dd MMM yyyy, HH:mm:ss 'UTC'", CultureInfo.InvariantCulture);

    public static string Duration(double seconds)
    {
        var duration = TimeSpan.FromSeconds(Math.Max(0, seconds));
        return duration.TotalHours >= 1 ? $"{(int)duration.TotalHours} hr {duration.Minutes} min"
            : duration.TotalMinutes >= 1 ? $"{(int)duration.TotalMinutes} min {duration.Seconds} sec"
            : duration.TotalSeconds.ToString("0.###", CultureInfo.InvariantCulture) + " sec";
    }

    public static string Filters(string label) => "<form class=\"report-filters\" hidden aria-label=\""
        + Encode(label) + "\"><label>Device <select data-filter=\"device\"><option value=\"\">All devices</option></select></label>"
        + "<label>Target <select data-filter=\"target\"><option value=\"\">All targets</option></select></label>"
        + "<label>Status <select data-filter=\"status\"><option value=\"\">All statuses</option></select></label>"
        + "<label>Search " + Encode(label) + " <input type=\"search\" data-filter=\"search\"></label>"
        + "<button type=\"reset\">Clear filters</button><output aria-live=\"polite\"></output>"
        + "<p data-no-matches hidden>No records match. Clear filters to see all records.</p></form>";

    public static string Attributes(string device, string target, string status) =>
        " data-report-item data-device=\"" + Encode(device) + "\" data-target=\"" + Encode(target)
        + "\" data-status=\"" + Encode(status) + "\"";
}
