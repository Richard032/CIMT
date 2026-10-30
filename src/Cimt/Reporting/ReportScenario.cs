using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using static Cimt.ReportHtml;

namespace Cimt;

/// <summary>Links one saved scenario to its device and exact recorded steps.</summary>
public sealed record ReportScenario(JsonElement Device, JsonElement Result, int Index)
{
    public JsonElement Identity => Device.TryGetProperty("device", out var value) ? value : default;
    public string Platform => Field(Identity, "platform");
    public string DeviceId => Field(Identity, "id", Field(Identity, "name"));
    public string Name => Field(Identity, "name", DeviceId);
    public string Target => Field(Result, "target");
    public string DeviceLabel => Platform + " / " + Name + " / " + DeviceId;
    public string Label => DeviceLabel + " / " + Target;
    public string Anchor => "scenario-" + Convert.ToHexString(SHA256.HashData(Encoding.UTF8.GetBytes(
        JsonSerializer.Serialize(new[] { Platform, DeviceId, Target, Index.ToString() })))).ToLowerInvariant();
    public JsonElement[] Steps => Rows(Result, "steps");
    public JsonElement[] Crashes => Rows(Result, "crashes");
    public int ConfirmedCrashes => Crashes.Count(crash => Field(crash, "kind") == "confirmed crash report");
    public int SuspectedTerminations => Crashes.Length - ConfirmedCrashes;
    public int ActionCount => Steps.Count(step => Action(step) is "tap" or "swipe" or "text" or "credential" or "back" or "wait");

    public string StepAnchor(int index) => Anchor + "-record-" + index;

    public (JsonElement Step, string Anchor)? FindStep(string id)
    {
        if (id.Length == 0)
            return null;
        var matches = Steps.Select((step, index) => (Step: step, Anchor: StepAnchor(index)))
            .Where(row => Field(row.Step, "step") == id).ToArray();
        // An ambiguous old record must not link to a different observation.
        return matches.Length == 1 ? matches[0] : null;
    }

    public string StepLink(string id) => FindStep(id) is { } step
        ? "<a href=\"#" + step.Anchor + "\">Recorded step " + Encode(id) + "</a>"
        : "Recorded step: " + Encode(id.Length == 0 ? "not recorded" : id) + " (no unique step link available)";

    public static string Action(JsonElement step) => step.TryGetProperty("action", out var action)
        ? action.ValueKind == JsonValueKind.Object ? Field(action, "action") : action.ToString() : "check";

    public static IReadOnlyList<ReportScenario> Read(JsonElement? execution) => execution is { } value
        ? Rows(value, "devices").SelectMany(device => Rows(device, "scenarios")
            .Select((scenario, index) => new ReportScenario(device, scenario, index))).ToArray() : [];
}
