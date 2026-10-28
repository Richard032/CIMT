using System.Text.Encodings.Web;
using System.Text.Json;
using System.Text.RegularExpressions;

namespace Cimt.Secrets;

/// <summary>Removes raw and JSON-escaped secret spellings from free text.</summary>
internal sealed class SecretText
{
    private readonly Regex pattern;

    public SecretText(IEnumerable<string> secrets)
    {
        var spellings = secrets.Where(value => value.Length > 0).SelectMany(Spellings)
            .Append("<redacted>").Distinct(StringComparer.Ordinal)
            .OrderByDescending(value => value.Length).Select(Regex.Escape);
        pattern = new Regex(string.Join("|", spellings));
    }

    // One replacement pass keeps overlapping secrets and existing markers safe.
    public string Scrub(string value) => pattern.Replace(value, "<redacted>");

    private static IEnumerable<string> Spellings(string value)
    {
        yield return value;
        var encoded = JsonSerializer.Serialize(value)[1..^1];
        yield return encoded;
        yield return Regex.Replace(encoded, @"\\u[0-9a-fA-F]{4}", match => match.Value.ToLowerInvariant());
        // This encoder only recognizes other tools' logs. It never writes report HTML or JSON.
        yield return JsonSerializer.Serialize(value, new JsonSerializerOptions
        {
            Encoder = JavaScriptEncoder.UnsafeRelaxedJsonEscaping
        })[1..^1];
    }
}
