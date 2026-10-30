using System.Text.Json;

namespace Cimt.RequirementDemo;

/// <summary>Exercise the real input, catalogue, matrix, and report services with synthetic observations.</summary>
public static class MappingDemo
{
    public static async Task<int> Run(string example)
    {
        var configuration = Configuration(example);
        var folders = new RunFolderAllocator().Create(Path.Combine(example, "work"), Path.Combine(example, "reports"), DateTimeOffset.UtcNow);
        var report = folders.Report;
        var state = new RunState(configuration, folders,
            new RunDeadline(folders.Identity.Started.AddMinutes(1)));
        state.Activity.Record("Prepare synthetic mapping example", "started",
            "Offline demonstration. No app, device, or API is used.");
        using var http = new HttpClient();
        await new TextInputLoader(new TextInputReader(http)).Execute(state);
        if (state.Requirements.Count != 5)
            throw new InvalidOperationException("The demo needs its five example requirements.");
        state.Devices.Add(new()
        {
            ["id"] = "synthetic-device",
            ["platform"] = "android",
            ["name"] = "Simulated phone"
        });
        var execution = DemoObservations.Execution(state.Requirements);
        state.Activity.Record("Record synthetic requirement observations", "completed",
            "Five example requirements include an expected failure and unresolved work.", "Demo", "android", "synthetic-device");
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
            ["android"] = Mapping(origin, [])
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
}
