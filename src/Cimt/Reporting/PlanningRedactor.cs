using System.Text.Json;
using System.Text.Json.Nodes;

namespace Cimt;

/// <summary>Keeps generated map identities and validated plan states separate from private text.</summary>
public sealed class PlanningRedactor(JsonTextRedactor json)
{
    public JsonNode Plan(JsonElement value) => json.Record(value, ["activeTaskId", "nextTaskId"], new()
    {
        ["tasks"] = rows => json.Items(rows, row => json.Record(row,
            ["id", "source", "requirementId", "status", "result", "targetState"]))
    });

    public JsonNode Exploration(JsonElement value) => json.Record(value, [], new()
    {
        ["paths"] = rows => json.Items(rows, row => json.Record(row,
            ["id", "screen", "control", "action", "kind", "scope", "planStepId"])),
        ["transitions"] = rows => json.Items(rows, row => json.Record(row, ["source", "destination"])),
        ["applicationMap"] = Map
    });

    public JsonNode? ContextSelection(JsonElement value) => value.ValueKind == JsonValueKind.Null ? null
        : json.Record(value, [], new()
        {
            ["includeAll"] = rows => json.Items(rows, JsonTextRedactor.Keep),
            ["records"] = rows => json.Items(rows, row => json.Record(row, ["collection", "id"]))
        });

    public JsonNode Recovery(JsonElement value) => json.Record(value, ["id", "step", "kind", "status", "decision"]);

    private JsonNode Map(JsonElement value) => json.Record(value, [], new()
    {
        ["states"] = rows => json.Items(rows, row => json.Record(row, ["id", "screen"], new()
        {
            ["configuration"] = Configuration,
            ["observations"] = rows => json.Items(rows, JsonTextRedactor.Keep)
        })),
        ["transitions"] = rows => json.Items(rows, row => json.Record(row, ["source", "destination", "control", "action", "destinationObservation"])),
        ["configuration"] = Configuration,
        ["refinements"] = JsonTextRedactor.Keep,
        ["observations"] = rows => json.Items(rows, row => json.Record(row, ["id", "state"], new()
        {
            ["elements"] = elements => json.Items(elements, element => json.Record(element, ["ref", "type", "enabled"]))
        }))
    });

    private JsonNode Configuration(JsonElement value)
    {
        var result = new JsonObject();
        foreach (var setting in value.EnumerateObject())
        {
            var name = json.Text(JsonSerializer.SerializeToElement(setting.Name))!.GetValue<string>();
            result[name] = json.Record(setting.Value, ["control", "observedAt"]);
        }
        return result;
    }
}
