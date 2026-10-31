using System.Text.Json;

namespace Cimt.UnitTests;

public sealed class DeviceSelectionTests
{
    [Fact]
    public void ExistingConfigurationSelectsPhysicalDevices()
    {
        var selection = new DeviceSelection(null);
        Assert.Equal(["real"], selection.NativeTypes);
        Assert.False(selection.Accepts(new() { ["id"] = "sim", ["type"] = "simulator" }));
    }

    [Fact]
    public void VirtualSelectionIncludesBothPlatformsAndOnlyRequestedIds()
    {
        var selection = Selection("virtual", "chosen");
        Assert.Equal(["emulator", "simulator"], selection.NativeTypes);
        Assert.True(selection.Accepts(new() { ["id"] = "chosen", ["type"] = "emulator" }));
        Assert.False(selection.Accepts(new() { ["id"] = "other", ["type"] = "simulator" }));
    }

    [Fact]
    public void MissingRequestedDeviceStopsInsteadOfTestingAnotherDevice()
    {
        Assert.Throws<ConfigurationException>(() => Selection("virtual", "missing").Verify(
            [new() { ["id"] = "other" }]));
    }

    [Fact]
    public void DiscoveryKeepsTheNativeDeviceKind()
    {
        var device = JsonSerializer.SerializeToElement(new { platform = "ios", id = "sim", type = "simulator", state = "online" });
        Assert.Equal("simulator", DeviceInventory.ReadDevice(device)!["type"]);
    }

    [Fact]
    public void VirtualIosRequiresAnExplicitSimulatorRuntime()
    {
        var settings = new Node(null, [], null, "/fixture");
        Assert.Throws<ConfigurationException>(() => Selection("virtual", "sim").ValidateBuild("ios", settings));
    }

    private static DeviceSelection Selection(string kind, string id) => new(new Node(null, new()
    {
        ["device-kind"] = new(kind, null, null, "/fixture"),
        ["device-ids"] = new(null, null, [new(id, null, null, "/fixture")], "/fixture")
    }, null, "/fixture"));
}
