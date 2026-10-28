using System.Text.Json;
using System.Text.Json.Nodes;

namespace Cimt;

/// <summary>Redacts string values before JSON encoding. Property names and numbers stay intact.</summary>
public sealed class JsonTextRedactor(Func<string, string> scrub)
{
    public JsonNode? Text(JsonElement value) => value.ValueKind switch
    {
        JsonValueKind.Object => Record(value, []),
        JsonValueKind.Array => Items(value, Text),
        JsonValueKind.String => JsonValue.Create(scrub(value.GetString()!)),
        _ => Keep(value)
    };

    public JsonObject Record(JsonElement value, string[] metadata,
        Dictionary<string, Func<JsonElement, JsonNode?>>? children = null)
    {
        var result = new JsonObject();
        foreach (var property in value.EnumerateObject())
        {
            if (children?.TryGetValue(property.Name, out var convert) == true)
                result[property.Name] = convert(property.Value);
            else if (metadata.Contains(property.Name))
                result[property.Name] = Scalar(property.Value);
            else
                result[property.Name] = Text(property.Value);
        }
        return result;
    }

    public JsonArray Items(JsonElement values, Func<JsonElement, JsonNode?> convert) =>
        new(values.EnumerateArray().Select(convert).ToArray());

    public static JsonNode? Keep(JsonElement value) => JsonNode.Parse(value.GetRawText());

    private static JsonNode? Scalar(JsonElement value)
    {
        // Metadata exemptions apply to scalar fields, never to an arbitrary nested object.
        if (value.ValueKind is JsonValueKind.Object or JsonValueKind.Array)
            throw new ConfigurationException("A report metadata field must be a scalar.");
        return Keep(value);
    }
}
