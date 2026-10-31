using System.Text.Json;

namespace Cimt.RequirementDemo;

/// <summary>Exercise the real input, catalogue, matrix, and report services with synthetic observations.</summary>
public static class MappingDemo
{
    public static async Task<int> Run(string example)
    {
        var configuration = Configuration(example);
        var folders = new RunFolderAllocator().Create(Path.Combine(example, "CIMT output", "work"),
            Path.Combine(example, "CIMT output", "reports"), DateTimeOffset.UtcNow);
        var report = folders.Report;
        var state = new RunState(configuration, folders,
            new RunDeadline(folders.Identity.Started.AddMinutes(1)));
        state.Activity.Record("Prepare synthetic mapping example", "started",
            "Offline demonstration. No app, device, or API is used.");
        using var http = new HttpClient();
        await new TextInputLoader(new TextInputReader(http)).Execute(state);
        if (state.Requirements.Count != 5)
            throw new InvalidOperationException("The demo needs its five example requirements.");
        foreach (var platform in new[] { "android", "ios" })
        {
            state.Devices.Add(new() { ["id"] = "synthetic-" + platform, ["platform"] = platform, ["name"] = "Simulated " + platform + " phone" });
            WriteEvidence(report, platform);
        }
        var execution = DemoObservations.Execution(state.Requirements);
        foreach (var platform in new[] { "android", "ios" })
            state.Activity.Record("Record synthetic requirement observations", "completed",
                "Five example requirements include an expected failure and unresolved work.", "Demo", platform, "synthetic-" + platform);
        await File.WriteAllTextAsync(Path.Combine(report, "ui-results.json"), JsonSerializer.Serialize(execution));
        Console.WriteLine("Synthetic requirement-mapping demo. No app, device, or API was used.");
        return new RunReportWriter().Write(state);
    }

    private static Configuration Configuration(string example)
    {
        var origin = Path.Combine(example, "demo-inputs.yaml");
        var target = Mapping(origin, new()
        {
            ["name"] = Text("Demo", origin),
            ["android"] = Mapping(origin, []),
            ["ios"] = Mapping(origin, [])
        });
        return new(Mapping(origin, new()
        {
            ["repository"] = Mapping(origin, new()
            {
                ["branch"] = Text("synthetic-demo", origin)
            }),
            ["build"] = Mapping(origin, new()
            {
                ["targets"] = new(null, null, [target], origin)
            }),
            ["inputs"] = Mapping(origin, new()
            {
                ["instructions"] = Text("./instructions.txt", origin),
                ["requirements"] = Text("./requirements.txt", origin)
            })
        }));
    }

    private static Node Mapping(string origin, Dictionary<string, Node> values) => new(null, values, null, origin);
    private static Node Text(string value, string origin) => new(value, null, null, origin);

    private static void WriteEvidence(string report, string platform)
    {
        // An opaque checkerboard exercises image links without pretending to capture an app.
        const string png = "iVBORw0KGgoAAAANSUhEUgAAAKAAAADwCAIAAAAII/iNAAAC60lEQVR4nO3asQ2AMBAEQddJTBEUS0RIFbSAHCCxHunzsbXpjfO6p2/bj+njfuOO1T68mitw3BU47gocdwWOuwLHXYHjrsBxV+C4K3DcFTjuChx3BY67AsddgeOuwHFX4LgrcNwVOO6OPz6a+/4EjrsCx12B467AcVfguCtw3BU47gocdwWOuwLHXYHjrsBxV+C4K3DcFTjuChx3BY67AsddgeOu0V3cFTjuChx3BY67AsddgeOuwHFX4LgrcNwVOO4KHHcFjrsCx12B467AcVfguCtw3BU47gocdwWOu0Z3cVfguCtw3BU47gocdwWOuwLHXYHjrsBxV+C4K3DcFTjuChx3BY67AsddgeOuwHFX4LgrcNwVOO4a3cVdgeOuwHFX4LgrcNwVOO4KHHcFjrsCx12B467AcVfguCtw3BU47gocdwWOuwLHXYHjrsBxV+C4a3QXdwWOuwLHXYHjrsBxV+C4K3DcFTjuChx3BY67AsddgeOuwHFX4LgrcNwVOO4KHHcFjrsCx12B467RXdwVOO4KHHcFjrsCx12B467AcVfguCtw3BU47gocdwWOuwLHXYHjrsBxV+C4K3DcFTjuChx3BY67RndxV+C4K3DcFTjuChx3BY67AsddgeOuwHFX4LgrcNwVOO4KHHcFjrsCx12B467AcVfguCtw3BU47hrdxV2B467AcVfguCtw3BU47gocdwWOuwLHXYHjrsBxV+C4K3DcFTjuChx3BY67AsddgeOuwHFX4LhrdBd3BY67AsddgeOuwHFX4LgrcNwVOO4KHHcFjrsCx12B467AcVfguCtw3BU47gocdwWOuwLHXYHjrtFd3BU47gocdwWOuwLHXYHjrsBxV+C4K3DcFTjuChx3BY67AsddgeOuwHFX4LgrcNwVOO4KHHcFjrtGd3FX4LgrcNwVOO4KHHcFjrsCx12B467AcVfguCtw3BU47gocdwWOuwLHXYHjrsBxV+C4K3DcFTjuPigEGv+HFp/iAAAAAElFTkSuQmCC";
        var folder = Path.Combine(report, "devices", platform);
        Directory.CreateDirectory(folder);
        File.WriteAllBytes(Path.Combine(folder, "step-0.png"), Convert.FromBase64String(png));
        File.WriteAllBytes(Path.Combine(folder, "step-1.png"), Convert.FromBase64String(png));
    }
}
