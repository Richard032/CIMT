namespace Cimt.UnitTests;

public sealed class RuntimeEnvironmentTests
{
    [Fact]
    public void InstalledCommandDirectoriesPrecedeTheInheritedPath()
    {
        var root = Path.Combine(Path.GetTempPath(), "CIMT installation");
        var inherited = Path.Combine(Path.GetTempPath(), "user tools");
        var path = new RuntimePaths(root).ExecutablePath(inherited).Split(Path.PathSeparator);
        Assert.Equal(new[] { Path.Combine(root, "bin"), Path.Combine(root, "tools/node-packages/bin"),
            Path.Combine(root, "tools/node-packages/lib/node_modules/.bin"), inherited }, path);
    }

    [Fact]
    public async Task ChildProcessesFindTheInstalledAdapterWithoutManualPathSetup()
    {
        if (OperatingSystem.IsWindows())
            return;
        using var temporary = new TestDirectory();
        var commands = Path.Combine(temporary.Path, "tools/node-packages/lib/node_modules/.bin");
        Directory.CreateDirectory(commands);
        var adapter = Path.Combine(commands, "mcp-server-mobile");
        File.WriteAllText(adapter, "#!/bin/sh\nprintf 'fixture adapter'\n");
        File.SetUnixFileMode(adapter, UnixFileMode.UserRead | UnixFileMode.UserWrite | UnixFileMode.UserExecute);
        var result = await new CommandRunner().Run(new("/bin/sh", ["-c", "mcp-server-mobile"], 10,
            new() { ["CIMT_INSTALL_ROOT"] = temporary.Path, ["PATH"] = "/usr/bin:/bin" }));
        Assert.Equal(0, result.Exit);
        Assert.Equal("fixture adapter", result.Stdout);
    }

    [Theory]
    [InlineData(null)]
    [InlineData("")]
    public void MissingInheritedPathDoesNotAddTheCurrentDirectory(string? inherited)
    {
        var path = new RuntimePaths(Path.GetTempPath()).ExecutablePath(inherited).Split(Path.PathSeparator);
        Assert.Equal(3, path.Length);
        Assert.DoesNotContain("", path);
    }
}
