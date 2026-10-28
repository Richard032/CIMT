using System.Text.Json;
using Cimt;

namespace Cimt.UnitTests;

/// <summary>Small cases verify one identity, paired names, and safe retained reports.</summary>
public sealed class RunIdentityTests
{
    private static readonly DateTimeOffset Started = new(2026, 10, 28, 14, 30, 0, 123, TimeSpan.Zero);

    [Fact]
    public void IdentityUsesUtcWithInvariantMillisecondFormatting()
    {
        var local = Started.ToOffset(TimeSpan.FromHours(2));
        var identity = RunIdentity.At(local);
        Assert.Equal("2026-10-28_14-30-00-123", identity.Id);
        Assert.Equal(TimeSpan.Zero, identity.Started.Offset);
        Assert.Equal("UTC", identity.TimeZone);
    }

    [Fact]
    public void FolderNamesHaveExactlyTheSameTimestamp()
    {
        using var folder = new TestDirectory();
        var pair = Allocate(folder.Path);
        Assert.Equal("work_" + pair.Identity.Id, Path.GetFileName(pair.Work));
        Assert.Equal("report_" + pair.Identity.Id, Path.GetFileName(pair.Report));
        Assert.False(Directory.Exists(pair.Work));
        Assert.True(Directory.Exists(pair.Report));
    }

    [Fact]
    public void ReportCollisionAdvancesBothNamesTogether()
    {
        using var folder = new TestDirectory();
        var first = Allocate(folder.Path);
        File.WriteAllText(Path.Combine(first.Report, "keep.txt"), "keep");
        var second = Allocate(folder.Path);
        Assert.Equal("2026-10-28_14-30-00-124", second.Identity.Id);
        Assert.Equal("work_" + second.Identity.Id, Path.GetFileName(second.Work));
        Assert.Equal("report_" + second.Identity.Id, Path.GetFileName(second.Report));
        Assert.Equal("keep", File.ReadAllText(Path.Combine(first.Report, "keep.txt")));
    }

    [Fact]
    public void OccupiedWorkFolderIsNotReused()
    {
        using var folder = new TestDirectory();
        var occupied = RunFolders.Under(folder.Path, folder.Path, RunIdentity.At(Started));
        Directory.CreateDirectory(occupied.Work);
        File.WriteAllText(Path.Combine(occupied.Work, "keep.txt"), "keep");
        var pair = Allocate(folder.Path);
        Assert.Equal("2026-10-28_14-30-00-124", pair.Identity.Id);
        Assert.True(File.Exists(Path.Combine(occupied.Work, "keep.txt")));
    }

    [Fact]
    public void FileAndDanglingLinkCollisionsAreSkipped()
    {
        using var folder = new TestDirectory();
        var first = RunFolders.Under(folder.Path, folder.Path, RunIdentity.At(Started));
        File.WriteAllText(first.Report, "keep");
        var second = RunFolders.Under(folder.Path, folder.Path, RunIdentity.At(Started).Next());
        File.CreateSymbolicLink(second.Work, Path.Combine(folder.Path, "missing-target"));
        Assert.Equal("2026-10-28_14-30-00-125", Allocate(folder.Path).Identity.Id);
        Assert.Equal("keep", File.ReadAllText(first.Report));
    }

    [Fact]
    public void ReservedReportTimestampIsSkipped()
    {
        using var folder = new TestDirectory();
        var first = RunFolders.Under(folder.Path, folder.Path, RunIdentity.At(Started));
        File.WriteAllText(first.Report + ".reserve", "reserved");
        Assert.Equal("2026-10-28_14-30-00-124", Allocate(folder.Path).Identity.Id);
        Assert.True(File.Exists(first.Report + ".reserve"));
    }

    [Fact]
    public void CollisionDoesNotChangeStartTimeOrDeadline()
    {
        using var folder = new TestDirectory();
        Allocate(folder.Path);
        var pair = Allocate(folder.Path);
        var deadline = new RunDeadline(pair.Identity.Started.AddMinutes(5));
        Assert.Equal(Started, pair.Identity.Started);
        Assert.Equal(Started.AddMinutes(5), deadline.End);
    }

    [Fact]
    public void RetainedIdentityNamesMatchTheAllocatedPair()
    {
        using var folder = new TestDirectory();
        var pair = Allocate(folder.Path);
        using var json = JsonDocument.Parse(File.ReadAllText(Path.Combine(pair.Report, "run-identity.json")));
        Assert.Equal(pair.Identity.Id, json.RootElement.GetProperty("runIdentity").GetProperty("id").GetString());
        Assert.Equal(Path.GetFileName(pair.Work), json.RootElement.GetProperty("workFolder").GetString());
        Assert.Equal(Path.GetFileName(pair.Report), json.RootElement.GetProperty("reportFolder").GetString());
        Assert.Empty(Directory.GetFiles(folder.Path, "*.reserve"));
    }

    [Fact]
    public void WorkCleanupRetainsReportAndRelativeEvidence()
    {
        using var folder = new TestDirectory();
        var pair = Allocate(folder.Path);
        var manager = new WorkDirectoryManager(Path.Combine(folder.Path, "owned.json"));
        var work = manager.Create(pair);
        var evidence = Path.Combine(pair.Report, "evidence");
        Directory.CreateDirectory(evidence);
        File.WriteAllText(Path.Combine(evidence, "step.txt"), "observed");
        File.WriteAllText(Path.Combine(pair.Report, "index.html"), "<a href=\"evidence/step.txt\">evidence</a>");
        manager.Remove(work);
        Assert.False(Directory.Exists(work));
        Assert.True(File.Exists(Path.Combine(pair.Report, "run-identity.json")));
        Assert.Equal("observed", File.ReadAllText(Path.Combine(evidence, "step.txt")));
    }

    [Fact]
    public void CopiedReportKeepsItsIdentityAndRelativeLinks()
    {
        using var folder = new TestDirectory();
        var pair = Allocate(folder.Path);
        Directory.CreateDirectory(Path.Combine(pair.Report, "evidence"));
        File.WriteAllText(Path.Combine(pair.Report, "evidence", "step.txt"), "observed");
        File.WriteAllText(Path.Combine(pair.Report, "index.html"), "<a href=\"evidence/step.txt\">evidence</a>");
        var archive = Path.Combine(folder.Path, "copied-report");
        CopyReport(pair.Report, archive);
        Assert.Equal(File.ReadAllText(Path.Combine(pair.Report, "run-identity.json")),
            File.ReadAllText(Path.Combine(archive, "run-identity.json")));
        Assert.Contains("evidence/step.txt", File.ReadAllText(Path.Combine(archive, "index.html")));
        Assert.Equal("observed", File.ReadAllText(Path.Combine(archive, "evidence", "step.txt")));
    }

    [Fact]
    public void ConfiguredRootsKeepTheirDeclaringFileOrigin()
    {
        using var folder = new TestDirectory();
        var origin = Path.Combine(folder.Path, "settings", "default.yaml");
        var config = new Configuration(new Node(null, new()
        {
            ["workspace"] = new(null, new()
            {
                ["root"] = new("./work", null, null, origin)
            }, null, origin),
            ["reports"] = new(null, new()
            {
                ["root"] = new("../reports", null, null, origin)
            }, null, origin)
        }, null, origin));
        var pair = new RunFolderAllocator().Create(config.WorkspaceRoot, config.ReportsRoot, Started);
        Assert.Equal(Path.Combine(folder.Path, "settings", "work", "work_" + pair.Identity.Id), pair.Work);
        Assert.Equal(Path.Combine(folder.Path, "reports", "report_" + pair.Identity.Id), pair.Report);
    }

    [Fact]
    public void ReportsCannotBeInsideThePlannedWorkFolder()
    {
        using var folder = new TestDirectory();
        var pair = RunFolders.Under(folder.Path, folder.Path, RunIdentity.At(Started));
        var nested = Path.Combine(pair.Work, "reports");
        Assert.Throws<ConfigurationException>(() => new RunFolderAllocator().Create(folder.Path, nested, Started));
        Assert.False(Directory.Exists(pair.Work));
    }

    [Fact]
    public void ReportAliasesCannotHideAnOwnedWorkAncestor()
    {
        using var folder = new TestDirectory();
        var pair = Allocate(folder.Path);
        var manager = new WorkDirectoryManager(Path.Combine(folder.Path, "owned.json"));
        manager.Create(pair);
        var alias = Path.Combine(folder.Path, "alias");
        Directory.CreateSymbolicLink(alias, pair.Work);
        Assert.Throws<ConfigurationException>(() => new RunFolderAllocator().Create(folder.Path, Path.Combine(alias, "reports"), Started));
        Assert.True(Directory.Exists(pair.Work));
    }

    [Fact]
    public void OccupationAfterAllocationCannotBeAdoptedAsOwnedWork()
    {
        using var folder = new TestDirectory();
        var pair = Allocate(folder.Path);
        Directory.CreateDirectory(pair.Work);
        File.WriteAllText(Path.Combine(pair.Work, "foreign.txt"), "keep");
        var manager = new WorkDirectoryManager(Path.Combine(folder.Path, "owned.json"));
        Assert.Throws<ConfigurationException>(() => manager.Create(pair));
        Assert.True(File.Exists(Path.Combine(pair.Work, "foreign.txt")));
        Assert.False(File.Exists(Path.Combine(folder.Path, "owned.json")));
    }

    [Fact]
    public void InterruptedCleanupCannotDeleteARetainedReport()
    {
        using var folder = new TestDirectory();
        var pair = Allocate(folder.Path);
        var manager = new WorkDirectoryManager(Path.Combine(folder.Path, "owned.json"));
        manager.Create(pair);
        var nested = Path.Combine(pair.Work, "unsafe-report");
        Directory.CreateDirectory(nested);
        Assert.Throws<ConfigurationException>(() => manager.CleanupPrevious(nested));
        Assert.True(Directory.Exists(pair.Work));
        Assert.True(Directory.Exists(nested));
    }

    private static void CopyReport(string source, string destination)
    {
        foreach (var file in Directory.GetFiles(source, "*", SearchOption.AllDirectories))
        {
            var target = Path.Combine(destination, Path.GetRelativePath(source, file));
            Directory.CreateDirectory(Path.GetDirectoryName(target)!);
            File.Copy(file, target);
        }
    }

    private static RunFolders Allocate(string root) => new RunFolderAllocator().Create(root, root, Started);
}
