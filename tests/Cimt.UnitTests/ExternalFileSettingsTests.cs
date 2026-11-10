using System.Text.Json;

namespace Cimt.UnitTests;

public sealed class ExternalFileSettingsTests : IDisposable
{
    private readonly string directory = Path.Combine(Path.GetTempPath(), "cimt-files-" + Guid.NewGuid().ToString("N"));

    public ExternalFileSettingsTests() => Directory.CreateDirectory(directory);
    public void Dispose() => Directory.Delete(directory, true);

    [Fact]
    public void RelativeSourceUsesTheConfigurationFolder()
    {
        var file = Assert.Single(ExternalFileSettings.Read(Settings("./test.xpa", "Documents/test.xpa")));
        Assert.Equal(Path.Combine(directory, "test.xpa"), file.Source);
        Assert.Equal("Documents/test.xpa", file.Destination);
    }

    [Fact]
    public void InheritedFilesKeepTheFolderThatDeclaredThem()
    {
        var original = Settings("./test.xpa", "Documents/test.xpa");
        var other = new Node(null, [], null, Path.Combine(directory, "nested", "override.yaml"));
        Assert.Equal(Path.Combine(directory, "test.xpa"), Assert.Single(ExternalFileSettings.Read(Node.Merge(original, other))).Source);
    }

    [Theory]
    [InlineData("../test.xpa")]
    [InlineData("/tmp/test.xpa")]
    [InlineData("C:\\test.xpa")]
    [InlineData("https://example.invalid/test.xpa")]
    public void SourcesOutsideTheTestFolderAreRejected(string source)
    {
        Assert.Throws<ConfigurationException>(() => ExternalFileSettings.Read(Settings(source, "Documents/test.xpa")));
    }

    [Theory]
    [InlineData("../test.xpa")]
    [InlineData("Documents/../test.xpa")]
    [InlineData("/Documents/test.xpa")]
    [InlineData("C:/test.xpa")]
    [InlineData("Documents//test.xpa")]
    [InlineData("Documents/./test.xpa")]
    [InlineData("Documents/test\n.xpa")]
    public void InvalidContainerPathsAreRejected(string destination)
    {
        Assert.Throws<ConfigurationException>(() => ExternalFileSettings.Read(Settings("./test.xpa", destination)));
    }

    [Fact]
    public void BackslashDestinationIsNormalized()
    {
        Assert.Equal("Documents/test.xpa", Assert.Single(ExternalFileSettings.Read(Settings("./test.xpa", @"Documents\test.xpa"))).Destination);
    }

    [Fact]
    public void MissingSourceIsRejectedBeforeTesting()
    {
        Assert.Throws<ConfigurationException>(() => ExternalFileSettings.CheckSources(Settings("./missing.xpa", "Documents/test.xpa")));
    }

    [Fact]
    public void ADirectoryCannotBeProvidedAsAnExternalFile()
    {
        Assert.Throws<ConfigurationException>(() => ExternalFileSettings.CheckSources(Settings(".", "Documents/test.xpa")));
    }

    [Fact]
    public void ReadableBinaryFileIsAcceptedWithoutChangingIt()
    {
        byte[] bytes = [0, 255, 1, 2];
        var file = Path.Combine(directory, "test.xpa");
        File.WriteAllBytes(file, bytes);
        ExternalFileSettings.CheckSources(Settings("./test.xpa", "Documents/test.xpa"));
        Assert.Equal(bytes, File.ReadAllBytes(file));
    }

    [Fact]
    public void DuplicateDestinationsAreRejectedForTheSamePlatform()
    {
        var root = Settings("./test.xpa", "Documents/test.xpa");
        var files = root.Get("external-files")!.List!;
        files.Add(files[0]);
        Assert.Throws<ConfigurationException>(() => ExternalFileSettings.Read(root));
    }

    [Fact]
    public void IosDestinationsCannotDifferOnlyByCase()
    {
        var root = Settings("./test.xpa", "Documents/test.xpa");
        var other = Settings("./other.xpa", "Documents/TEST.xpa");
        root.Get("external-files")!.List!.Add(other.Get("external-files")!.List![0]);
        Assert.Throws<ConfigurationException>(() => ExternalFileSettings.Read(root));
    }

    [Theory]
    [InlineData("windows")]
    [InlineData("")]
    public void UnsupportedPlatformIsRejected(string platform)
    {
        Assert.Throws<ConfigurationException>(() => ExternalFileSettings.Read(Settings("./test.xpa", "Documents/test.xpa", platform)));
    }

    [Fact]
    public void UnknownExternalFileSettingIsRejected()
    {
        var root = Settings("./test.xpa", "Documents/test.xpa");
        root.Get("external-files")!.List![0].Map!["unexpected"] = Scalar("value");
        Assert.Throws<ConfigurationException>(() => ExternalFileSettings.Read(root));
    }

    [Fact]
    public void NoExternalFilesPreservesExistingConfigurations()
    {
        Assert.Empty(ExternalFileSettings.Read(new Node(null, [], null, Path.Combine(directory, "config.yaml"))));
    }

    [Fact]
    public void RuntimeReceivesAbsolutePathAndMetadataWithoutReadingContents()
    {
        var root = Settings("./test.xpa", "Documents/test.xpa");
        var json = JsonSerializer.SerializeToElement(RuntimeRequest.ExternalFiles(root));
        Assert.Equal(Path.Combine(directory, "test.xpa"), json[0].GetProperty("source").GetString());
        Assert.Equal("ios", json[0].GetProperty("platform").GetString());
        Assert.Equal(3, json[0].EnumerateObject().Count());
    }

    [Fact]
    public async Task ConfiguredFilesRejectAnOlderInstalledRuntime()
    {
        var paths = new RuntimePaths(directory);
        Directory.CreateDirectory(Path.GetDirectoryName(paths.Worker)!);
        Directory.CreateDirectory(Path.GetDirectoryName(paths.Python)!);
        File.WriteAllText(paths.Worker, "fixture");
        File.WriteAllText(paths.Python, "fixture");
        var folders = new RunFolderAllocator().Create(directory, directory, DateTimeOffset.UtcNow);
        var state = new RunState(new Configuration(Settings("./test.xpa", "Documents/test.xpa")),
            folders, new RunDeadline(DateTimeOffset.UtcNow.AddMinutes(1)));
        var check = new RuntimeFilesCheck(paths);
        await Assert.ThrowsAsync<ConfigurationException>(() => check.Execute(state));

        var module = Path.Combine(Path.GetDirectoryName(paths.Worker)!, "device_adapter", "external_files.py");
        Directory.CreateDirectory(Path.GetDirectoryName(module)!);
        File.WriteAllText(module, "fixture");
        await check.Execute(state);
    }

    private Node Scalar(string value) => new(value, null, null, Path.Combine(directory, "config.yaml"));
    private Node Settings(string source, string destination, string platform = "ios") => new(null, new()
    {
        ["external-files"] = new(null, null, [new(null, new()
        {
            ["source"] = Scalar(source), ["destination"] = Scalar(destination), ["platform"] = Scalar(platform)
        }, null, Path.Combine(directory, "config.yaml"))], Path.Combine(directory, "config.yaml"))
    }, null, Path.Combine(directory, "config.yaml"));
}
