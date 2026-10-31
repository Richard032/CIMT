using System.Text.Json;
using System.Text.Json.Nodes;

namespace Cimt;

/// <summary>Separates worker control fields from observations in each record type.</summary>
public sealed class ExecutionRedactor(JsonTextRedactor json)
{
    public JsonNode? Execution(JsonElement value) => value.ValueKind == JsonValueKind.Null ? null
        : json.Record(value, ["runId"], new()
        {
            ["devices"] = items => json.Items(items, DeviceResult),
            // The ledger contains validated counts, prices, and host pricing metadata only.
            ["budget"] = JsonTextRedactor.Keep
        });

    private JsonNode DeviceResult(JsonElement value) => json.Record(value, ["index"], new()
    {
        ["device"] = item => json.Record(item, ["id", "platform", "type"]),
        ["scenarios"] = items => json.Items(items, Scenario)
    });

    private JsonNode Scenario(JsonElement value) => json.Record(value,
        ["target", "appId", "verdict", "completion"], new()
        {
            ["checks"] = items => json.Items(items, Check),
            ["requirements"] = items => json.Items(items, Requirement),
            ["steps"] = items => json.Items(items, Step),
            ["crashes"] = items => json.Items(items, Crash),
            ["rejectedResponses"] = items => json.Items(items, item =>
                json.Record(item, ["attempt", "step", "status", "screenshot"])),
            ["testPlan"] = item => new PlanningRedactor(json).Plan(item),
            ["exploration"] = item => new PlanningRedactor(json).Exploration(item)
        });

    private JsonNode Check(JsonElement value) => json.Record(value,
        ["source", "status", "requirementId", "step", "screenshot"]);

    private JsonNode Requirement(JsonElement value) => json.Record(value,
        ["id", "status", "startLine", "endLine", "step", "screenshot"]);

    private JsonNode Step(JsonElement value) => json.Record(value,
        ["step", "screenshot", "ui", "planStepId", "sourceState", "destinationState"], new()
    {
        ["action"] = Action,
        ["crash"] = CrashKind
    });

    private JsonNode? Action(JsonElement value) => value.ValueKind == JsonValueKind.String
        ? JsonTextRedactor.Keep(value) // String actions are host-generated step names.
        : json.Record(value, ["action", "ref", "direction", "credential", "field", "completion"], new()
        {
            ["checks"] = items => json.Items(items, Check)
        });

    private JsonNode Crash(JsonElement value) => json.Record(value, ["step", "matchingAttempt"], new()
    {
        ["kind"] = CrashKind,
        ["reproductionSteps"] = items => json.Items(items, Action)
    });

    private JsonNode? CrashKind(JsonElement value)
    {
        // These fixed host classifications must not become a different evidence category.
        return value.ValueKind == JsonValueKind.String && value.GetString() is "confirmed crash report"
            or "unexpected termination / suspected crash" or "unexpected startup termination / suspected crash"
            ? JsonTextRedactor.Keep(value) : json.Text(value);
    }
}
