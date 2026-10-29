using System.Text.Json;

namespace Cimt;

/// <summary>Records supported physical devices once, before builds start.</summary>
public sealed class DeviceDiscovery(RunProcess processes, RuntimePaths paths, IRunProgress progress) : IRunStep
{
    public async Task Execute(RunState state)
    {
        progress.Write(state, "Taking the physical-device snapshot");
        var result = await processes.Invoke(state, "node", ["-e",
            "const {Mobilecli}=require(process.argv[1]);const c=new Mobilecli();console.log(JSON.stringify({devices:c.getDevices({type:'real'}),binary:c.getPath()}));",
            paths.NativeModule], 30);
        if (result.Exit != 0)
            throw new ConfigurationException("Physical-device discovery failed: "
                + state.Configuration.Scrub(result.Stderr.Trim()));
        ReadDevices(state, result.Stdout);
        if (state.Devices.Count == 0)
            throw new ConfigurationException("No supported physical devices are connected.");
        await File.WriteAllTextAsync(Path.Combine(state.Report, "startup-devices.json"), JsonSerializer.Serialize(state.Devices));
    }

    private static void ReadDevices(RunState state, string json)
    {
        using var document = JsonDocument.Parse(json);
        state.NativeBinary = document.RootElement.GetProperty("binary").GetString();
        var devices = document.RootElement.GetProperty("devices").GetProperty("data").GetProperty("devices");
        foreach (var device in devices.EnumerateArray())
            if (ReadDevice(device) is { } supported)
                state.Devices.Add(supported);
    }

    public static Dictionary<string, string>? ReadDevice(JsonElement device)
    {
        var platform = device.GetProperty("platform").GetString()!;
        if (device.GetProperty("state").GetString() != "online" || platform is not ("android" or "ios"))
            return null;
        return new()
        {
            ["platform"] = platform,
            ["id"] = device.GetProperty("id").GetString()!,
            ["name"] = device.TryGetProperty("name", out var name) ? name.GetString() ?? platform : platform
        };
    }
}
