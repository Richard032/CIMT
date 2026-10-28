using System.Text.Json.Serialization;
using System.Text.RegularExpressions;

namespace Cimt;

/// <summary>Keeps document structure without giving it a test result.</summary>
public sealed record RequirementHeading(
    [property: JsonPropertyName("text")] string Text,
    [property: JsonPropertyName("level")] int Level,
    [property: JsonPropertyName("startLine")] int StartLine,
    [property: JsonPropertyName("endLine")] int EndLine);

/// <summary>Recognizes explicit Markdown headings, without guessing from normal prose.</summary>
public static class RequirementHeadingReader
{
    public static IReadOnlyList<RequirementHeading> ReadAll(string[] lines)
    {
        var result = new List<RequirementHeading>();
        var fence = "";
        for (var index = 0; index < lines.Length; index++)
        {
            var marker = Regex.Match(lines[index], @"^ {0,3}(`{3,}|~{3,})(.*)$");
            if (fence.Length > 0)
            {
                if (marker.Success && marker.Groups[1].Value[0] == fence[0]
                    && marker.Groups[1].Length >= fence.Length && marker.Groups[2].Value.Trim().Length == 0)
                    fence = "";
                continue;
            }
            if (marker.Success)
            {
                // A heading shown inside a code example is source text, not document structure.
                fence = marker.Groups[1].Value;
                continue;
            }
            var heading = Read(lines, index);
            if (heading is null)
                continue;
            result.Add(heading);
            index = heading.EndLine - 1;
        }
        return result;
    }

    private static RequirementHeading? Read(string[] lines, int index)
    {
        if (lines[index].StartsWith("    ") || lines[index].StartsWith('\t'))
            return null;
        var title = lines[index].Trim();
        var prefix = Regex.Match(title, @"^(#{1,6})(?:\s+.*|$)");
        if (prefix.Success)
            return new(lines[index], prefix.Groups[1].Length, index + 1, index + 1);
        if (title.Length == 0 || index + 1 >= lines.Length)
            return null;
        var underline = lines[index + 1].Trim();
        if (!Regex.IsMatch(underline, @"^(?:=+|-+)$"))
            return null;
        // A list item followed by a rule is still a list item, not a title.
        if (Regex.IsMatch(title, @"^(?:[-*+]\s+|\d+[.)]\s+|\|)"))
            return null;
        return new(lines[index] + "\n" + lines[index + 1], underline[0] == '=' ? 1 : 2,
            index + 1, index + 2);
    }
}
