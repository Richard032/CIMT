using System.Text.Json;
using Cimt;

namespace Cimt.UnitTests;

/// <summary>Use real configuration and report services with a small readiness fake.</summary>
public sealed class InputFolderCommandTests
{
    [Fact]
    public async Task ValidationCreatesOutputWithoutPreparedOutputFolders()
    {
        using var fixture = new InputFolderFixture();
        await fixture.Prepare();
        Assert.False(Directory.Exists(fixture.Layout.Root));
        Assert.Equal(0, await fixture.Execute());
        var report = Assert.Single(Directory.GetDirectories(fixture.Layout.ReportsRoot));
        Assert.True(File.Exists(Path.Combine(report, "index.html")));
        Assert.False(Directory.Exists(fixture.Layout.WorkRoot));
    }

    [Fact]
    public async Task SharedSettingsAndBranchOverrideKeepOutputWithRunInputs()
    {
        using var fixture = new InputFolderFixture();
        await fixture.Prepare();
        var config = new ConfigurationLoader().Load(CommandLine.Parse(fixture.Arguments));
        Assert.Equal(fixture.Layout.InputFolder, config.Outputs.InputFolder);
        Assert.Equal("feature/check", config.Root.Get("repository")!.Value("branch"));
        Assert.Equal(Path.Combine(fixture.Layout.InputFolder, "instructions.txt"),
            config.Root.Get("inputs")!.Get("instructions")!.PathValue);
        Assert.Equal(0, await fixture.Execute());
        Assert.False(Directory.Exists(Path.Combine(fixture.SharedFolder, "CIMT output")));
    }

    [Fact]
    public async Task InvalidYamlKeepsItsErrorReportWithRunInputs()
    {
        using var fixture = new InputFolderFixture();
        await fixture.Prepare();
        await File.WriteAllTextAsync(fixture.RunFile, "inputs: [invalid yaml");
        Assert.Equal(3, await fixture.Execute());
        var report = Assert.Single(Directory.GetDirectories(fixture.Layout.ReportsRoot));
        Assert.True(File.Exists(Path.Combine(report, "index.html")));
        Assert.False(Directory.Exists(fixture.Layout.WorkRoot));
    }

    [Fact]
    public async Task MissingConfigurationStillProducesALocalErrorReport()
    {
        using var fixture = new InputFolderFixture();
        await fixture.Prepare();
        File.Delete(fixture.RunFile);
        Assert.Equal(3, await fixture.Execute());
        Assert.Single(Directory.GetDirectories(fixture.Layout.ReportsRoot));
    }

    [Fact]
    public async Task LegacyRootsAreIgnoredAndRecordedWithoutChangingPrivateSettings()
    {
        using var fixture = new InputFolderFixture();
        await fixture.Prepare();
        var original = await File.ReadAllTextAsync(fixture.SharedFile);
        Assert.Equal(0, await fixture.Execute());
        var report = Assert.Single(Directory.GetDirectories(fixture.Layout.ReportsRoot));
        using var layout = JsonDocument.Parse(await File.ReadAllTextAsync(Path.Combine(report, "output-layout.json")));
        Assert.True(layout.RootElement.GetProperty("legacyRootSettingsIgnored").GetBoolean());
        Assert.Contains("Legacy workspace.root/reports.root", await File.ReadAllTextAsync(Path.Combine(report, "index.html")));
        Assert.Equal(original, await File.ReadAllTextAsync(fixture.SharedFile));
        Assert.False(Directory.Exists(Path.Combine(fixture.SharedFolder, "legacy-reports")));
    }

    [Fact]
    public async Task RepeatedValidationKeepsEarlierReports()
    {
        using var fixture = new InputFolderFixture();
        await fixture.Prepare();
        Assert.Equal(0, await fixture.Execute());
        var first = Assert.Single(Directory.GetDirectories(fixture.Layout.ReportsRoot));
        var original = await File.ReadAllTextAsync(Path.Combine(first, "index.html"));
        Assert.Equal(0, await fixture.Execute());
        Assert.Equal(2, Directory.GetDirectories(fixture.Layout.ReportsRoot).Length);
        Assert.Equal(original, await File.ReadAllTextAsync(Path.Combine(first, "index.html")));
    }

    [Fact]
    public async Task UnsafeOutputDoesNotFallBackToAnotherFolder()
    {
        using var fixture = new InputFolderFixture();
        await fixture.Prepare();
        var outside = Path.Combine(fixture.SharedFolder, "outside");
        Directory.CreateDirectory(outside);
        Directory.CreateSymbolicLink(fixture.Layout.Root, outside);
        Assert.Equal(3, await fixture.Execute());
        Assert.Empty(Directory.EnumerateFileSystemEntries(outside));
        Assert.Contains("could not write an error report", fixture.Errors.ToString());
    }

    [Fact]
    public async Task BlockedOutputDoesNotOverwriteDataOrCreateAFallbackReport()
    {
        using var fixture = new InputFolderFixture();
        await fixture.Prepare();
        await File.WriteAllTextAsync(fixture.Layout.Root, "existing user file");
        Assert.Equal(3, await fixture.Execute());
        Assert.Equal("existing user file", await File.ReadAllTextAsync(fixture.Layout.Root));
        Assert.False(Directory.Exists(fixture.Layout.ReportsRoot));
        Assert.Contains("could not write an error report", fixture.Errors.ToString());
    }
}

internal sealed class InputFolderFixture : IDisposable
{
    private readonly TestDirectory directory = new();
    public string SharedFolder => Path.Combine(directory.Path, "shared");
    public string SharedFile => Path.Combine(SharedFolder, "default.yaml");
    public OutputLayout Layout => new(Path.Combine(directory.Path, "Testing inputs", "FirstRun"));
    public string RunFile => Path.Combine(Layout.InputFolder, "app.yaml");
    public StringWriter Errors { get; } = new();
    public string[] Arguments => ["validate", "--config", SharedFile, "--run-config", RunFile, "--branch", "feature/check"];

    public async Task Prepare()
    {
        Directory.CreateDirectory(SharedFolder);
        Directory.CreateDirectory(Layout.InputFolder);
        await File.WriteAllTextAsync(SharedFile, """
            workspace: {root: ./legacy-work}
            reports: {root: ./legacy-reports}
            repository: {url: 'https://example.invalid/app.git', branch: main, solution: App.sln}
            execution: {time-limit-minutes: 5}
            ai-model: {name: fixture-model, api-key: synthetic-credential}
            ai-budget: {amount: 1, currency: USD}
            inputs: {instructions: ./shared-instructions.txt}
            build: {targets: [{name: fixture, configuration: Release, project: App.csproj, android: {framework: net10.0-android}}]}
            """);
        if (!OperatingSystem.IsWindows())
            File.SetUnixFileMode(SharedFile, UnixFileMode.UserRead | UnixFileMode.UserWrite);
        await File.WriteAllTextAsync(RunFile, "inputs: {instructions: ./instructions.txt}");
        await File.WriteAllTextAsync(Path.Combine(Layout.InputFolder, "instructions.txt"), "Check a button.");
    }

    public async Task<int> Execute()
    {
        var app = new CommandApplication(new ConfigurationLoader(), new IdentityReadiness(),
            (_, _) => Task.FromResult(0), new CommandReports(), new RunFolderAllocator(),
            new RecordingRunLock().Acquire, TextWriter.Null, Errors);
        return await app.Run(Arguments);
    }

    public void Dispose() => directory.Dispose();
}
