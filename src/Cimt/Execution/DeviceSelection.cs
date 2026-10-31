namespace Cimt;

/// <summary>Selects one execution environment without changing the test workflow.</summary>
public sealed class DeviceSelection(Node? execution)
{
    public string Kind => execution?.Value("device-kind") ?? "physical";
    public string[] NativeTypes => Kind == "virtual" ? ["emulator", "simulator"] : ["real"];
    public string[] Ids => execution?.Get("device-ids")?.List?.Select(item => item.Text).ToArray() ?? [];

    public bool Accepts(Dictionary<string, string> device) =>
        NativeTypes.Contains(device["type"]) && (Ids.Length == 0 || Ids.Contains(device["id"]));

    public void ValidateBuild(string platform, Node settings)
    {
        if (platform != "ios")
            return;
        var runtime = settings.Get("properties")?.Value("RuntimeIdentifier") ?? "";
        if (Kind == "virtual" && !runtime.StartsWith("iossimulator-", StringComparison.Ordinal))
            throw new ConfigurationException("Virtual iOS builds require an explicit properties.RuntimeIdentifier, such as iossimulator-x64 on Intel Macs.");
        if (Kind == "physical" && runtime.StartsWith("iossimulator-", StringComparison.Ordinal))
            throw new ConfigurationException("An iOS Simulator build cannot run on a physical iPhone.");
    }

    public void Verify(IEnumerable<Dictionary<string, string>> devices)
    {
        var found = devices.Select(device => device["id"]).ToHashSet();
        if (Ids.Any(id => !found.Contains(id)))
            throw new ConfigurationException("A selected device is not online in the requested execution environment.");
        if (found.Count == 0)
            throw new ConfigurationException("No supported " + Kind + " devices are online. Start or connect the selected devices before running CIMT.");
    }
}
