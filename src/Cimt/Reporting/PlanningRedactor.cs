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

    private JsonNode Map(JsonElement value) => json.Record(value, [], new()
    {
        ["states"] = rows => json.Items(rows, row => json.Record(row, ["id", "screen"], new()
        {
            ["configuration"] = Configuration
        })),
        ["transitions"] = rows => json.Items(rows, row => json.Record(row, ["source", "destination", "control", "action"])),
        ["configuration"] = Configuration
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
