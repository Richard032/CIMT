using System.Text.Json;

namespace Cimt;

/// <summary>Shares native discovery and device filtering between validation and execution.</summary>
public static class DeviceInventory
{
    public static string[] Arguments(string module, DeviceSelection selection) => ["-e",
        "const {Mobilecli}=require(process.argv[1]);const c=new Mobilecli();const devices=JSON.parse(process.argv[2]).flatMap(type=>c.getDevices({type}).data.devices);console.log(JSON.stringify({devices:{data:{devices}},binary:c.getPath()}));",
        module, JsonSerializer.Serialize(selection.NativeTypes)];

    public static List<Dictionary<string, string>> Read(JsonElement snapshot, DeviceSelection selection)
    {
        var result = new List<Dictionary<string, string>>();
        foreach (var device in snapshot.GetProperty("devices").GetProperty("data").GetProperty("devices").EnumerateArray())
            if (ReadDevice(device) is { } supported && selection.Accepts(supported))
                result.Add(supported);
        return result;
    }

    public static Dictionary<string, string>? ReadDevice(JsonElement device)
    {
        var platform = device.GetProperty("platform").GetString()!;
        if (device.GetProperty("state").GetString() != "online" || platform is not ("android" or "ios"))
            return null;
        return new()
        {
            ["type"] = device.TryGetProperty("type", out var kind) ? kind.GetString() ?? "real" : "real",
            ["platform"] = platform,
            ["id"] = device.GetProperty("id").GetString()!,
            ["name"] = device.TryGetProperty("name", out var name) ? name.GetString() ?? platform : platform
        };
    }
}
