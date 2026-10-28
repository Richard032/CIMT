using System.Text.Json;
using System.Text.Json.Nodes;

namespace Cimt;

/// <summary>Builds a safe report snapshot without changing identity, decisions, or evidence links.</summary>
public sealed class RunReportRedactor(JsonTextRedactor json)
{
    public JsonNode Run(JsonElement value) => json.Record(value,
        ["command", "sourceBranch", "sourceCommit", "started", "finished", "exitCode", "verdict", "completion"], new()
        {
            // These values come from the host, not from credential text.
            ["runIdentity"] = JsonTextRedactor.Keep,
            ["stages"] = items => json.Items(items,
                item => json.Record(item, ["stage", "target", "platform", "result", "log"])),
            ["builds"] = items => json.Items(items,
                item => json.Record(item, ["target", "platform", "artifact", "app-id"])),
            ["requirementCoverage"] = Coverage,
            ["execution"] = new ExecutionRedactor(json).Execution
        });

    private JsonNode Coverage(JsonElement value) => json.Record(value, ["sourceSha256"], new()
    {
        ["requirements"] = items => json.Items(items, Summary)
    });

    private JsonNode Summary(JsonElement value) => json.Record(value, ["status"], new()
    {
        ["definition"] = item => json.Record(item, ["id", "startLine", "endLine"]),
        ["results"] = items => json.Items(items, Assessment)
    });

    private JsonNode Assessment(JsonElement value) => json.Record(value, ["status", "step", "screenshot"], new()
    {
        ["scope"] = item => json.Record(item, ["target", "platform", "deviceId"])
    });
}
