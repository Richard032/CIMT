using System.Text.Json.Nodes;
using Cimt;

namespace Cimt.UnitTests;

public sealed class RetainedBuildTests
{
    [Fact]
    public async Task ReplayRejectsAnAppFromAnotherDeviceKind()
    {
        using var fixture = new RetainedBuildFixture();
        await fixture.Prepare();
        await fixture.ChangeMetadata(value => value["apps"]![0]!["deviceKind"] = "virtual");
        var replay = fixture.NewState();
        await Assert.ThrowsAsync<ConfigurationException>(() => fixture.Store.Load(replay));
        Assert.Empty(replay.Builds);
    }

    [Fact]
    public async Task ReplayCopiesTheBuiltAppWithoutChangingTheOriginal()
    {
        using var fixture = new RetainedBuildFixture();
        await fixture.Prepare();
        var source = fixture.Built.Builds[0]["artifact"];
        var replay = fixture.NewState();
        await fixture.Store.Load(replay);
        var app = Assert.Single(replay.Builds);
        Assert.NotEqual(source, app["artifact"]);
        Assert.Equal("built app fixture", await File.ReadAllTextAsync(app["artifact"]));
        Assert.Equal("built app fixture", await File.ReadAllTextAsync(source));
        Assert.Equal(fixture.Built.Commit, replay.Commit);
        Assert.Contains(fixture.Built.Identity.Id, System.Text.Json.JsonSerializer.Serialize(replay.Stages));
    }

    [Fact]
    public async Task AFailedBuildDoesNotReplaceTheLastSuccessfulApp()
    {
        using var fixture = new RetainedBuildFixture();
        await fixture.Prepare();
        var original = await File.ReadAllTextAsync(fixture.Manifest);
        await fixture.Store.Save(fixture.NewState());
        Assert.Equal(original, await File.ReadAllTextAsync(fixture.Manifest));
    }

    [Fact]
    public async Task MetadataContainsNoPrivateConfigurationValues()
    {
        using var fixture = new RetainedBuildFixture();
        await fixture.Prepare();
        var metadata = await File.ReadAllTextAsync(fixture.Manifest);
        Assert.DoesNotContain("synthetic-credential", metadata);
        Assert.DoesNotContain("api-key", metadata);
    }

    [Fact]
    public async Task MissingMetadataStopsReplayExplicitly()
    {
        using var fixture = new RetainedBuildFixture();
        await fixture.Prepare();
        File.Delete(fixture.Manifest);
        var error = await Assert.ThrowsAsync<ConfigurationException>(() => fixture.Store.Load(fixture.NewState()));
        Assert.Contains("replay will not clone or build", error.Message);
    }

    [Fact]
    public async Task AChangedBranchCannotSilentlyReuseAnotherBranchsApp()
    {
        using var fixture = new RetainedBuildFixture();
        await fixture.Prepare();
        await fixture.ChangeMetadata(value => value["branch"] = "another-branch");
        var replay = fixture.NewState();
        await Assert.ThrowsAsync<ConfigurationException>(() => fixture.Store.Load(replay));
        Assert.Empty(replay.Builds);
    }

    [Fact]
    public async Task AChangedBuildConfigurationCannotReuseAnIncompatibleApp()
    {
        using var fixture = new RetainedBuildFixture();
        await fixture.Prepare();
        await fixture.ChangeMetadata(value => value["apps"]![0]!["configuration"] = "Debug");
        await Assert.ThrowsAsync<ConfigurationException>(() => fixture.Store.Load(fixture.NewState()));
    }

    [Fact]
    public async Task AChangedArtifactIsRejectedBeforeItCanBeExecuted()
    {
        using var fixture = new RetainedBuildFixture();
        await fixture.Prepare();
        await File.WriteAllTextAsync(fixture.Built.Builds[0]["artifact"], "changed");
        var replay = fixture.NewState();
        var error = await Assert.ThrowsAsync<ConfigurationException>(() => fixture.Store.Load(replay));
        Assert.Contains("changed after its build", error.Message);
        Assert.Empty(replay.Builds);
    }

    [Fact]
    public async Task MissingArtifactDoesNotTriggerAnAutomaticBuild()
    {
        using var fixture = new RetainedBuildFixture();
        await fixture.Prepare();
        File.Delete(fixture.Built.Builds[0]["artifact"]);
        var error = await Assert.ThrowsAsync<ConfigurationException>(() => fixture.Store.Load(fixture.NewState()));
        Assert.Contains("Replay will not rebuild", error.Message);
    }

    [Fact]
    public async Task ArtifactPathsCannotEscapeTheirSourceReport()
    {
        using var fixture = new RetainedBuildFixture();
        await fixture.Prepare();
        await fixture.ChangeMetadata(value => value["apps"]![0]!["artifact"] = "../../other.apk");
        await Assert.ThrowsAsync<ConfigurationException>(() => fixture.Store.Load(fixture.NewState()));
    }

    [Fact]
    public async Task ExpiredReplayDoesNotCopyTheRetainedApp()
    {
        using var fixture = new RetainedBuildFixture();
        await fixture.Prepare();
        var replay = fixture.NewState(new RunDeadline(DateTimeOffset.UtcNow.AddSeconds(-1)));
        await Assert.ThrowsAsync<RunLimitException>(() => fixture.Store.Load(replay));
        Assert.Empty(replay.Builds);
    }
}

internal sealed class RetainedBuildFixture : IDisposable
{
    private readonly InputFolderFixture inputs = new();
    public RetainedBuildStore Store { get; } = new();
    public RunState Built { get; private set; } = null!;
    private Configuration configuration = null!;
    public string Manifest => Path.Combine(configuration.Outputs.Root, "retained-builds.json");

    public async Task Prepare()
    {
        await inputs.Prepare();
        configuration = new ConfigurationLoader().Load(CommandLine.Parse(inputs.Arguments));
        Built = NewState();
        Built.Commit = new string('a', 40);
        var artifact = Path.Combine(Built.Report, "artifacts", "fixture.apk");
        Directory.CreateDirectory(Path.GetDirectoryName(artifact)!);
        await File.WriteAllTextAsync(artifact, "built app fixture");
        Built.Builds.Add(new()
        {
            ["target"] = "fixture", ["platform"] = "android", ["artifact"] = artifact, ["app-id"] = "com.fixture.app"
        });
        await Store.Save(Built);
    }

    public RunState NewState(RunDeadline? deadline = null)
    {
        var pair = new RunFolderAllocator().Create(configuration.WorkspaceRoot, configuration.ReportsRoot, DateTimeOffset.UtcNow);
        return new(configuration, pair, deadline ?? new RunDeadline(DateTimeOffset.UtcNow.AddMinutes(1))) { Command = "replay" };
    }

    public async Task ChangeMetadata(Action<JsonNode> change)
    {
        var value = JsonNode.Parse(await File.ReadAllTextAsync(Manifest))!;
        change(value);
        await File.WriteAllTextAsync(Manifest, value.ToJsonString());
    }

    public void Dispose() => inputs.Dispose();
}
