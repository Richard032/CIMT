using System.Text.Json.Serialization;
using System.Security.Cryptography;
using System.Text;
using System.Text.RegularExpressions;

namespace Cimt;

/// <summary>Keeps a stable internal ID and the original requirement text and line range.</summary>
public sealed record RequirementDefinition(
    [property: JsonPropertyName("id")] string Id,
    [property: JsonPropertyName("text")] string Text,
    [property: JsonPropertyName("startLine")] int StartLine,
    [property: JsonPropertyName("endLine")] int EndLine,
    [property: JsonPropertyName("headingContext")] string HeadingContext = "");

/// <summary>Separates test expectations from document headings while retaining both.</summary>
public sealed record RequirementDocument(
    IReadOnlyList<RequirementDefinition> Items, IReadOnlyList<RequirementHeading> Headings);

/// <summary>Groups plain text without dropping source content or needing an AI call.</summary>
public static class RequirementCatalogue
{
    /// <summary>Identify the redacted input snapshot used by this catalogue.</summary>
    public static string Hash(string text) => Convert.ToHexStringLower(SHA256.HashData(Encoding.UTF8.GetBytes(text)));

    public static IReadOnlyList<RequirementDefinition> Read(string text) => Parse(text).Items;

    public static RequirementDocument Parse(string text)
    {
        var result = new List<RequirementDefinition>();
        var headings = new List<RequirementHeading>();
        var activeHeadings = new List<RequirementHeading>();
        var pending = new List<string>();
        var start = 0;
        var lines = text.Replace("\r\n", "\n").Replace('\r', '\n').Split('\n');
        var headingsByLine = RequirementHeadingReader.ReadAll(lines).ToDictionary(heading => heading.StartLine);
        for (var index = 0; index < lines.Length; index++)
        {
            var heading = headingsByLine.GetValueOrDefault(index + 1);
            if (heading is not null)
            {
                Flush(result, pending, start, index, activeHeadings);
                headings.Add(heading);
                // A new section replaces its sibling and any deeper section.
                activeHeadings.RemoveAll(item => item.Level >= heading.Level);
                activeHeadings.Add(heading);
                index = heading.EndLine - 1;
                continue;
            }
            var line = lines[index].Trim();
            if (line.Length == 0 || StartsItem(line) || EndsSentence(pending))
                Flush(result, pending, start, index, activeHeadings);
            if (line.Length == 0)
                continue;
            if (pending.Count == 0)
                start = index + 1;
            pending.Add(lines[index]);
        }
        Flush(result, pending, start, lines.Length, activeHeadings);
        return new(result, headings);
    }

    private static bool StartsItem(string line) => Regex.IsMatch(line,
        @"^(?:[-*+]\s+|\d+[.)]\s+|[A-Za-z][A-Za-z0-9_.-]*-\d+\b|\|)");

    private static bool EndsSentence(List<string> pending) => pending.Count > 0
        && Regex.IsMatch(pending[^1].TrimEnd(), @"[.!?]$");

    private static void Flush(List<RequirementDefinition> result, List<string> pending, int start, int end,
        List<RequirementHeading> headings)
    {
        if (pending.Count == 0)
            return;
        // Keep section meaning beside each expectation, without testing the heading itself.
        result.Add(new("REQ-" + (result.Count + 1).ToString("D4"), string.Join("\n", pending).Trim(), start, end,
            string.Join("\n", headings.Select(heading => heading.Text))));
        pending.Clear();
    }
}
