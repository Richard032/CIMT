using System.Text.Json;
using System.Text.Json.Nodes;

namespace Cimt;

/// <summary>Reads the atomic worker result envelope and the latest budget ledger.</summary>
public static class RuntimeResults
{
    public const int ProtocolVersion = 1;

    public static JsonElement? Read(string report)
    {
        var path = Path.Combine(report, "ui-results.json");
        if (!File.Exists(path))
            return null;
        try
        {
            var data = JsonNode.Parse(File.ReadAllText(path)) as JsonObject;
            if (data is null)
                throw new ConfigurationException("Worker results must be a JSON object.");
            if (data.TryGetPropertyValue("protocolVersion", out var version)
                && (version is not JsonValue number || !number.TryGetValue<int>(out var value) || value != ProtocolVersion))
                throw new ConfigurationException("Unsupported worker results protocol version. Install matching CIMT host and runtime.");
            ValidateDevices(data["devices"]);
            var budget = Path.Combine(report, "ai-budget.json");
            if (File.Exists(budget))
                data["budget"] = JsonNode.Parse(File.ReadAllText(budget)) as JsonObject
                    ?? throw new ConfigurationException("The worker budget ledger must be a JSON object.");
            else if (data["budget"] is not null and not JsonObject)
                throw new ConfigurationException("The worker budget snapshot must be a JSON object.");
            return JsonSerializer.SerializeToElement(data);
        }
        catch (JsonException)
        {
            throw new ConfigurationException("Worker results or budget ledger contain invalid JSON.");
        }
    }

    private static void ValidateDevices(JsonNode? value)
    {
        if (value is not JsonArray devices)
            throw new ConfigurationException("Worker results require a devices array.");
        for (var deviceIndex = 0; deviceIndex < devices.Count; deviceIndex++)
        {
            if (devices[deviceIndex] is not JsonObject device || device["device"] is not JsonObject
                || device["scenarios"] is not JsonArray scenarios)
                throw new ConfigurationException($"Worker results device {deviceIndex + 1} requires an identity object and a scenarios array.");
            for (var scenarioIndex = 0; scenarioIndex < scenarios.Count; scenarioIndex++)
            {
                if (scenarios[scenarioIndex] is not JsonObject scenario
                    || scenario["crashes"] is not JsonArray
                    || scenario["completion"] is not JsonValue completion || !completion.TryGetValue<string>(out _)
                    || (scenario.ContainsKey("verdict")
                        && (scenario["verdict"] is not JsonValue verdict || !verdict.TryGetValue<string>(out _)))
                    || (scenario.ContainsKey("remaining") && scenario["remaining"] is not JsonArray)
                    || (scenario.ContainsKey("requirements") && (scenario["requirements"] is not JsonArray requirements
                        || requirements.Any(row => row is not JsonObject))))
                    throw new ConfigurationException(
                        $"Worker results device {deviceIndex + 1}, scenario {scenarioIndex + 1} has invalid outcome or diagnostic fields.");
            }
        }
    }
}
