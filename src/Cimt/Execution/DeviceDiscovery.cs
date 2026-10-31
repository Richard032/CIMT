using System.Text.Json;

namespace Cimt;

/// <summary>Records selected online devices once, before builds start.</summary>
public sealed class DeviceDiscovery(RunProcess processes, RuntimePaths paths, IRunProgress progress) : IRunStep
{
    public async Task Execute(RunState state)
    {
        var selection = new DeviceSelection(state.Configuration.Root.Get("execution"));
        progress.Write(state, "Taking the " + selection.Kind + "-device snapshot");
        var result = await processes.Invoke(state, "node", DeviceInventory.Arguments(paths.NativeModule, selection), 60);
        if (result.Exit != 0)
            throw new ConfigurationException("Device discovery failed: "
                + state.Configuration.Scrub(result.Stderr.Trim()));
        ReadDevices(state, result.Stdout, selection);
        selection.Verify(state.Devices);
        await File.WriteAllTextAsync(Path.Combine(state.Report, "startup-devices.json"), JsonSerializer.Serialize(state.Devices));
    }

    private static void ReadDevices(RunState state, string json, DeviceSelection selection)
    {
        using var document = JsonDocument.Parse(json);
        state.NativeBinary = document.RootElement.GetProperty("binary").GetString();
        state.Devices.AddRange(DeviceInventory.Read(document.RootElement, selection));
    }
}
