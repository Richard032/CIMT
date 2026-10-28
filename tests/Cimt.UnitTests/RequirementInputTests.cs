using Cimt;
using System.Text.Json;

namespace Cimt.UnitTests;

/// <summary>Use local text files to check the handoff, without credentials or devices.</summary>
public sealed class RequirementInputTests
{
    [Fact]
    public async Task LoadedCatalogueIsSavedBeforeExecution()
    {
        using var folder = new TestDirectory();
        var text = Path.Combine(folder.Path, "requirements.txt");
        File.WriteAllText(text, "Save shall work.\nBack shall work.");
        var origin = Path.Combine(folder.Path, "config.yaml");
        var config = new Configuration(new Node(null, new()
        {
            ["inputs"] = new(null, new()
            {
                ["requirements"] = new("requirements.txt", null, null, origin)
            }, null, origin)
        }, null, origin));
        var state = new RunState(config, folder.Path, DateTimeOffset.UtcNow, new RunDeadline(DateTimeOffset.UtcNow.AddMinutes(1)));
        using var http = new HttpClient();
        await new TextInputLoader(new TextInputReader(http)).Execute(state);
        Assert.Equal(2, state.Requirements.Count);
        using var json = JsonDocument.Parse(File.ReadAllText(Path.Combine(folder.Path, "requirements.json")));
        Assert.Equal("REQ-0001", json.RootElement.GetProperty("items")[0].GetProperty("id").GetString());
        Assert.Equal(2, json.RootElement.GetProperty("items")[1].GetProperty("startLine").GetInt32());
    }

    [Fact]
    public void UnbuiltTargetStillGetsARequirementScope()
    {
        const string origin = "/fixture/config.yaml";
        var target = new Node(null, new()
        {
            ["name"] = new("Release", null, null, origin),
            ["android"] = new(null, [], null, origin)
        }, null, origin);
        var config = new Configuration(new Node(null, new()
        {
            ["build"] = new(null, new()
            {
                ["targets"] = new(null, null, [target], origin)
            }, null, origin)
        }, null, origin));
        var state = new RunState(config, "/unused", DateTimeOffset.UtcNow, new RunDeadline(DateTimeOffset.UtcNow.AddMinutes(1)));
        state.Devices.Add(new()
        {
            ["id"] = "phone-a",
            ["platform"] = "android",
            ["name"] = "Phone A"
        });
        var scope = Assert.Single(RequirementScopes.Create(state));
        Assert.Equal("Release", scope.Target);
        Assert.Contains("No installable build", scope.UnavailableReason);
    }
}
