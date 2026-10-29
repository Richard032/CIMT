using Cimt.Build;

namespace Cimt.UnitTests;

public sealed class BuildWorkerTests
{
    [Fact]
    public void AndroidPreservesAnExplicitPackageFormat()
    {
        var request = Request("android") with
        {
            Properties = new()
            {
                ["AndroidPackageFormats"] = "aab"
            }
        };
        var arguments = BuildCommands.Publish(request, "/output");
        Assert.Contains("-p:AndroidPackageFormats=aab", arguments);
        Assert.DoesNotContain("-p:AndroidPackageFormats=apk", arguments);
        Assert.Equal("aab", request.Properties["AndroidPackageFormats"]);
    }

    [Theory]
    [InlineData("android")]
    [InlineData("ios")]
    public void MissingPropertiesAreLeftToTheProjectForBothCommands(string platform)
    {
        var request = Request(platform);
        foreach (var arguments in new[] { BuildCommands.Publish(request, "/output"), BuildCommands.Metadata(request) })
        {
            Assert.DoesNotContain(arguments, argument => argument.StartsWith("-p:")
                && !argument.StartsWith("-p:Configuration=") && !argument.StartsWith("-p:TargetFramework="));
        }
    }

    [Fact]
    public void IosPreservesExplicitRuntimeAndArchiveSettings()
    {
        var request = Request("ios") with
        {
            Properties = new()
            {
                ["RuntimeIdentifier"] = "iossimulator-x64",
                ["BuildIpa"] = "false",
                ["ArchiveOnBuild"] = "false"
            }
        };
        foreach (var arguments in new[] { BuildCommands.Publish(request, "/output"), BuildCommands.Metadata(request) })
        {
            Assert.Contains("-p:RuntimeIdentifier=iossimulator-x64", arguments);
            Assert.Contains("-p:BuildIpa=false", arguments);
            Assert.Contains("-p:ArchiveOnBuild=false", arguments);
        }
    }

    [Fact]
    public void MissingInstallableOutputExplainsHowToConfigureTheBuild()
    {
        using var temporary = new TestDirectory();
        File.WriteAllText(Path.Combine(temporary.Path, "app.aab"), "fixture");
        var error = Assert.Throws<InvalidOperationException>(() => BuildArtifacts.Resolve(Request("android"), temporary.Path));
        Assert.Contains("No installable APK", error.Message);
        Assert.Contains("did not override", error.Message);
    }

    [Theory]
    [InlineData(0, "com.example.actual", "com.example.fallback", "com.example.actual")]
    [InlineData(1, "com.example.actual", "com.example.fallback", "com.example.fallback")]
    [InlineData(0, "unusable output with spaces", "com.example.fallback", "com.example.fallback")]
    public void MetadataHasPriorityOnlyWhenItIsValid(int exit, string output, string fallback, string expected)
    {
        Assert.Equal(expected, AppIdResolver.Resolve(new(exit, output, ""), fallback));
    }

    [Fact]
    public void InvalidMetadataAndFallbackAreRejected()
    {
        Assert.Throws<InvalidOperationException>(() => AppIdResolver.Resolve(new(0, "", ""), "not an id"));
    }

    [Fact]
    public void BuildLogRemovesConfiguredSecretsFromBothStreams()
    {
        var output = new StringWriter();
        var errors = new StringWriter();
        var log = new BuildLog(output, errors);
        log.Configure(new()
        {
            ["CodesignKey"] = "synthetic-signing-secret"
        });
        log.ProcessOutput(new(1, "output synthetic-signing-secret", "error synthetic-signing-secret"));
        Assert.DoesNotContain("synthetic-signing-secret", output.ToString() + errors);
    }

    [Fact]
    public void BuildLogKeepsExistingRedactionMarkers()
    {
        var log = new BuildLog(TextWriter.Null, TextWriter.Null);
        log.Configure(new() { ["Password"] = "e" });
        Assert.Equal("s<redacted>cr<redacted>t", log.Scrub(log.Scrub("secret")));
    }

    [Fact]
    public void BuildLogRemovesEscapedSigningSecret()
    {
        var log = new BuildLog(TextWriter.Null, TextWriter.Null);
        log.Configure(new() { ["Password"] = "a\"b" });
        Assert.Equal("log <redacted>", log.Scrub("log a\\u0022b"));
    }

    [Fact]
    public async Task FailedPublishDoesNotQueryMetadataOrWriteSuccess()
    {
        using var temporary = new TestDirectory();
        var request = Request("android") with
        {
            Repository = temporary.Path,
            ResultFile = System.IO.Path.Combine(temporary.Path, "result.json")
        };
        var process = new FailingBuildProcess();
        var workflow = new BuildWorkflow(process, new BuildLog(TextWriter.Null, TextWriter.Null));
        Assert.Equal(42, await workflow.Execute(request));
        Assert.Equal(1, process.Calls);
        Assert.False(File.Exists(request.ResultFile));
    }

    [Fact]
    public void AmbiguousArtifactsAreRejectedWithoutAFallback()
    {
        using var temporary = new TestDirectory();
        File.WriteAllText(System.IO.Path.Combine(temporary.Path, "one-Signed.apk"), "fixture");
        File.WriteAllText(System.IO.Path.Combine(temporary.Path, "two-Signed.apk"), "fixture");
        Assert.Throws<InvalidOperationException>(() => BuildArtifacts.Resolve(Request("android"), temporary.Path));
    }

    private static BuildRequest Request(string platform) => new(platform, "/fixture", "/fixture/result.json", "/fixture/App.csproj",
        "Release", "net10.0-" + platform, [], "", "com.example.fallback");
}

internal sealed class FailingBuildProcess : IBuildProcess
{
    public int Calls
    {
        get; private set;
    }
    public Task<BuildProcessResult> Run(IEnumerable<string> arguments, string workingDirectory)
    {
        Calls++;
        return Task.FromResult(new BuildProcessResult(42, "fixture", ""));
    }
}

internal sealed class TestDirectory : IDisposable
{
    public string Path { get; } = System.IO.Path.Combine(System.IO.Path.GetTempPath(), "cimt-unit-" + Guid.NewGuid().ToString("N"));
    public TestDirectory() => Directory.CreateDirectory(Path);
    public void Dispose() => Directory.Delete(Path, recursive: true);
}
