using Cimt;

namespace Cimt.UnitTests;

/// <summary>Test one metadata rule at a time without creating files.</summary>
public sealed class BuildResultTests
{
    private readonly string repository = Path.GetFullPath(Path.Combine(Path.GetTempPath(), "fixture-repository"));

    [Fact]
    public void CompleteScriptResultOverridesBothYamlValues()
    {
        var artifact = Path.Combine(repository, "script.apk");
        var script = new Dictionary<string, string> { ["artifact"] = artifact, ["app-id"] = "com.script.app" };
        var result = BuildResultResolver.Resolve(script, repository, "yaml.apk", "com.yaml.app");
        Assert.Equal(new ResolvedBuildResult(artifact, "com.script.app"), result);
    }

    [Fact]
    public void MissingArtifactUsesYamlRelativeToCloneRoot()
    {
        var script = new Dictionary<string, string> { ["app-id"] = "com.script.app" };
        var result = BuildResultResolver.Resolve(script, repository, "artifacts/app.apk", "com.yaml.app");
        Assert.Equal(Path.Combine(repository, "artifacts/app.apk"), result.Artifact);
        Assert.Equal("com.script.app", result.AppId);
    }

    [Fact]
    public void MissingAppIdUsesYaml()
    {
        var script = new Dictionary<string, string> { ["artifact"] = Path.Combine(repository, "app.apk") };
        Assert.Equal("com.yaml.app", BuildResultResolver.Resolve(script, repository, null, "com.yaml.app").AppId);
    }

    [Fact]
    public void MissingResultUsesBothYamlValues()
    {
        var result = BuildResultResolver.Resolve(new Dictionary<string, string>(), repository, "app.apk", "com.yaml.app");
        Assert.Equal(new ResolvedBuildResult(Path.Combine(repository, "app.apk"), "com.yaml.app"), result);
    }

    [Fact]
    public void InvalidScriptAppIdIsNotHiddenByYaml()
    {
        var script = new Dictionary<string, string> { ["app-id"] = "not an id" };
        Assert.Throws<ConfigurationException>(() => BuildResultResolver.Resolve(script, repository, "app.apk", "com.valid.app"));
    }

    [Fact]
    public void RelativeScriptArtifactIsRejected()
    {
        var script = new Dictionary<string, string> { ["artifact"] = "relative.apk" };
        Assert.Throws<ConfigurationException>(() => BuildResultResolver.Resolve(script, repository, "valid.apk", "com.valid.app"));
    }

    [Fact]
    public void MissingArtifactAndFallbackAreRejected()
    {
        Assert.Throws<ConfigurationException>(() => BuildResultResolver.Resolve(new Dictionary<string, string>(), repository, null, "com.valid.app"));
    }
}
