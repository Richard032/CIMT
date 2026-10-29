using Cimt;

namespace Cimt.UnitTests;

/// <summary>Check folder selection without tools, phones, or model calls.</summary>
public sealed class OutputLayoutTests
{
    [Fact]
    public void OutputIsBelowTheInputFolderAndSupportsSpaces()
    {
        var input = Path.Combine(Path.GetTempPath(), "Testing inputs", "FirstRun");
        var layout = OutputLayout.ForFile(Path.Combine(input, "app.yaml"));
        Assert.Equal(Path.Combine(input, "CIMT output"), layout.Root);
        Assert.Equal(Path.Combine(layout.Root, "work"), layout.WorkRoot);
        Assert.Equal(Path.Combine(layout.Root, "reports"), layout.ReportsRoot);
    }

    [Fact]
    public void SharedConfigurationSelectsTheInputFolderWhenUsedAlone()
    {
        var file = Path.Combine(Path.GetTempPath(), "FirstRun", "default.yaml");
        var options = CommandLine.Parse(["run", "--config", file]);
        Assert.Equal(Path.GetDirectoryName(file), OutputLayout.ForCommand(options).InputFolder);
    }

    [Fact]
    public void RunConfigurationSelectsTheFolderEvenWithABranchOverride()
    {
        var input = Path.Combine(Path.GetTempPath(), "FirstRun");
        var options = CommandLine.Parse(["run", "--config", "/shared/default.yaml",
            "--run-config", Path.Combine(input, "app.yaml"), "--branch", "feature/test"]);
        Assert.Equal(input, OutputLayout.ForCommand(options).InputFolder);
    }

    [Fact]
    public void ReadingAndCheckingTheLayoutDoesNotCreateOutput()
    {
        using var folder = new TestDirectory();
        var layout = new OutputLayout(folder.Path);
        layout.Check();
        Assert.False(Directory.Exists(layout.Root));
    }

    [Fact]
    public void MissingInputFolderIsNotCreatedForATypo()
    {
        using var folder = new TestDirectory();
        var layout = new OutputLayout(Path.Combine(folder.Path, "missing"));
        Assert.Throws<ConfigurationException>(layout.Check);
        Assert.False(Directory.Exists(layout.InputFolder));
    }

    [Theory]
    [InlineData("CIMT output")]
    [InlineData("CIMT output/reports")]
    [InlineData("CIMT output/work")]
    public void LinksCannotRedirectOutputOutsideItsParent(string relative)
    {
        using var folder = new TestDirectory();
        var input = Path.Combine(folder.Path, "FirstRun");
        var outside = Path.Combine(folder.Path, "outside");
        Directory.CreateDirectory(input);
        Directory.CreateDirectory(outside);
        var link = Path.Combine(input, relative);
        Directory.CreateDirectory(Path.GetDirectoryName(link)!);
        Directory.CreateSymbolicLink(link, outside);
        Assert.Throws<ConfigurationException>(new OutputLayout(input).Check);
        Assert.Empty(Directory.EnumerateFileSystemEntries(outside));
    }
}
