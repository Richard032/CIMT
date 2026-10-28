using System.Text.Json;

namespace Cimt;

/// <summary>Builds traceability from the host catalogue, even when UI execution is missing.</summary>
public static class RequirementReportBuilder
{
    public static RequirementCoverage Build(IReadOnlyList<RequirementDefinition> definitions,
        IReadOnlyList<RequirementScope> scopes, JsonElement? execution, string instructions, string sourceSha256 = "")
    {
        return new(definitions.Select(definition => Summary(definition, scopes, execution, instructions)).ToArray(), sourceSha256);
    }

    private static RequirementSummary Summary(RequirementDefinition definition, IReadOnlyList<RequirementScope> scopes,
        JsonElement? execution, string instructions)
    {
        var results = scopes.Select(scope => Read(definition.Id, scope, execution, instructions)).ToArray();
        return new(definition, RequirementStatus.Combine(results.Select(row => row.Status)), results);
    }

    private static RequirementAssessment Read(string id, RequirementScope scope, JsonElement? execution, string instructions)
    {
        var rows = FindResults(id, scope, execution).ToArray();
        var found = rows.FirstOrDefault(row => Text(row, "status") == "failed");
        if (found.ValueKind == JsonValueKind.Undefined)
            found = rows.LastOrDefault();
        if (found.ValueKind == JsonValueKind.Undefined)
            return Missing(scope, StoppingReason(scope, execution));
        var status = ValidStatus(found, instructions);
        var reason = Text(found, "reason");
        if (status is "not tested" or "inconclusive")
            reason = string.Join(" ", new[] { reason, StoppingReason(scope, execution) }.Where(value => value.Length > 0));
        if (status == "inconclusive" && string.IsNullOrWhiteSpace(reason))
            reason = "The worker result did not establish a valid requirement decision.";
        return new(scope, status, Text(found, "expected"), Text(found, "observed"), reason,
            Text(found, "instructionQuote"), Step(found), Text(found, "screenshot"), EvidenceError(found));
    }

    private static IEnumerable<JsonElement> FindResults(string id, RequirementScope scope, JsonElement? execution)
    {
        if (execution is not { } value || !value.TryGetProperty("devices", out var devices))
            yield break;
        foreach (var device in devices.EnumerateArray())
        {
            var identity = device.GetProperty("device");
            if (Text(identity, "id") != scope.DeviceId || Text(identity, "platform") != scope.Platform)
                continue;
            foreach (var scenario in device.GetProperty("scenarios").EnumerateArray())
                if (Text(scenario, "target") == scope.Target && scenario.TryGetProperty("requirements", out var requirements))
                    foreach (var row in requirements.EnumerateArray())
                        if (Text(row, "id") == id)
                            yield return row;
        }
    }

    private static string ValidStatus(JsonElement row, string instructions)
    {
        var status = Text(row, "status");
        if (status is "passed" or "failed")
            return Has(row, "expected") && Has(row, "observed") ? status : "inconclusive";
        if (status is "not tested" or "inconclusive")
            return Has(row, "reason") ? status : "inconclusive";
        if (status == "overridden" && Has(row, "reason") && Has(row, "instructionQuote")
            && instructions.Contains(Text(row, "instructionQuote"), StringComparison.Ordinal))
            return status;
        return "inconclusive";
    }

    private static RequirementAssessment Missing(RequirementScope scope, string stoppingReason) =>
        new(scope, "not tested", "", "", stoppingReason.Length > 0 ? stoppingReason : scope.UnavailableReason, "", null, "", "No observation or screenshot was produced.");

    private static string StoppingReason(RequirementScope scope, JsonElement? execution)
    {
        if (execution is not { } value || !value.TryGetProperty("devices", out var devices))
            return "";
        foreach (var device in devices.EnumerateArray())
        {
            var identity = device.GetProperty("device");
            if (Text(identity, "id") == scope.DeviceId && Text(identity, "platform") == scope.Platform)
                return string.Join(" ", new[] { Text(device, "stoppingReason"), Text(device, "error") }
                    .Where(reason => !string.IsNullOrWhiteSpace(reason)));
        }
        return "";
    }

    private static string EvidenceError(JsonElement row) => Has(row, "screenshot") ? ""
        : Has(row, "evidenceError") ? Text(row, "evidenceError") : "Screenshot evidence is unavailable; see execution errors.";

    private static int? Step(JsonElement row) => row.TryGetProperty("step", out var step) && step.ValueKind == JsonValueKind.Number && step.TryGetInt32(out var number) ? number : null;
    private static bool Has(JsonElement row, string key) => !string.IsNullOrWhiteSpace(Text(row, key));
    private static string Text(JsonElement row, string key) => row.TryGetProperty(key, out var value) ? value.ToString() : "";
}
