using Cimt;

namespace Cimt.UnitTests;

/// <summary>Uses temporary artifact files and a fake command, never real build tools.</summary>
public sealed class BuildIntegrationTests
{
    [Fact]
    public async Task SuccessfulScriptCanUseYamlWithoutAResultFile()
    {
        using var fixture = new BuildFixture();
        var job = fixture.Job("yaml-only");
        await fixture.Builder.Build(fixture.State, job);
        var result = Assert.Single(fixture.State.Builds);
        Assert.True(File.Exists(result["artifact"]));
        Assert.Equal("com.fixture.app", result["app-id"]);
    }

    [Fact]
    public async Task PartialScriptMetadataUsesTheOtherYamlField()
    {
        using var fixture = new BuildFixture();
        var job = fixture.Job("partial");
        File.WriteAllText(job.ResultFile, """{"app-id":"com.script.app"}""");
        await fixture.Builder.Build(fixture.State, job);
        Assert.Equal("com.script.app", Assert.Single(fixture.State.Builds)["app-id"]);
    }

    [Fact]
    public async Task InvalidMetadataDoesNotBlockTheFollowingBuild()
    {
        using var fixture = new BuildFixture();
        var invalid = fixture.Job("invalid");
        File.WriteAllText(invalid.ResultFile, "not JSON");
        await fixture.Builder.Build(fixture.State, invalid);
        await fixture.Builder.Build(fixture.State, fixture.Job("valid"));
        Assert.Equal("valid", Assert.Single(fixture.State.Builds)["target"]);
        Assert.Equal(3, fixture.State.Exit);
    }
}

internal sealed class BuildFixture : IDisposable
{
    private readonly TestDirectory directory = new();
    private readonly string repository;
    public RunState State
    {
        get;
    }
    public ApplicationBuilder Builder
    {
        get;
    }

    public BuildFixture()
    {
        repository = Path.Combine(directory.Path, "repository");
        Directory.CreateDirectory(repository);
        File.WriteAllText(Path.Combine(repository, "app.apk"), "fixture");
        var config = new Configuration(new Node(null, [], null, Path.Combine(directory.Path, "config.yaml")));
        State = new(config, directory.Path, DateTimeOffset.UtcNow, new RunDeadline(DateTimeOffset.UtcNow.AddMinutes(1)));
        Builder = new(new RunProcess(new FakeCommandRunner()), new BuildArtifactStore(), new SilentProgress());
    }

    public BuildJob Job(string target)
    {
        var folder = Path.Combine(directory.Path, target);
        Directory.CreateDirectory(folder);
        return new(target, "android", folder, Path.Combine(folder, "request.json"),
            Path.Combine(folder, "result.json"), "unused-script", repository, "app.apk", "com.fixture.app");
    }

    public void Dispose() => directory.Dispose();
}

internal sealed class SilentProgress : IRunProgress
{
    public void Write(RunState state, string stage)
    {
    }
}
