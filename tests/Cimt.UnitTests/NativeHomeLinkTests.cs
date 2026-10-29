using System.Net.Sockets;
using System.Text;
using Cimt;

namespace Cimt.UnitTests;

/// <summary>Check real local links and sockets without starting CIMT or using a phone.</summary>
public sealed class NativeHomeLinkTests
{
    [Fact]
    public void ShortAddressBindsASocketStoredInALongRunFolder()
    {
        using var folder = new TestDirectory();
        var home = Path.Combine(folder.Path, new string('a', 100), "CIMT output", "mobilecli");
        Directory.CreateDirectory(home);
        var link = new NativeHomeLink(Path.Combine(folder.Path, "owned.json"));
        link.Create(home);
        try
        {
            var address = Path.Combine(link.LinkPath, "daemon.sock");
            Assert.True(Encoding.UTF8.GetByteCount(address) <= 103);
            using var socket = new Socket(AddressFamily.Unix, SocketType.Stream, ProtocolType.Unspecified);
            socket.Bind(new UnixDomainSocketEndPoint(address));
            Assert.True(File.Exists(Path.Combine(home, "daemon.sock")));
        }
        finally { link.Remove(home); }
    }

    [Fact]
    public async Task ExistingFileIsNotReusedOrOverwritten()
    {
        using var folder = new TestDirectory();
        var link = new NativeHomeLink(Path.Combine(folder.Path, "owned.json"));
        await File.WriteAllTextAsync(link.LinkPath, "keep");
        try
        {
            Assert.Throws<ConfigurationException>(() => link.Create(folder.Path));
            Assert.Equal("keep", await File.ReadAllTextAsync(link.LinkPath));
        }
        finally { File.Delete(link.LinkPath); }
    }

    [Fact]
    public void ExistingLinkIsNeverAdopted()
    {
        using var folder = new TestDirectory();
        var link = new NativeHomeLink(Path.Combine(folder.Path, "owned.json"));
        link.Create(folder.Path);
        try { Assert.Throws<ConfigurationException>(() => link.Create(folder.Path)); }
        finally { link.Remove(folder.Path); }
    }

    [Fact]
    public void CleanupRejectsADifferentTarget()
    {
        using var folder = new TestDirectory();
        var link = new NativeHomeLink(Path.Combine(folder.Path, "owned.json"));
        link.Create(folder.Path);
        try
        {
            Assert.Throws<IOException>(() => link.Remove(Path.Combine(folder.Path, "other")));
            Assert.Equal(folder.Path, new DirectoryInfo(link.LinkPath).LinkTarget);
        }
        finally { link.Remove(folder.Path); }
    }

    [Fact]
    public async Task RemovingTheLinkKeepsTargetFiles()
    {
        using var folder = new TestDirectory();
        var keep = Path.Combine(folder.Path, "keep.txt");
        await File.WriteAllTextAsync(keep, "keep");
        var link = new NativeHomeLink(Path.Combine(folder.Path, "owned.json"));
        link.Create(folder.Path);
        link.Remove(folder.Path);
        Assert.Null(new DirectoryInfo(link.LinkPath).LinkTarget);
        Assert.Equal("keep", await File.ReadAllTextAsync(keep));
    }

    [Fact]
    public void MissingLinkNeedsNoCleanup()
    {
        using var folder = new TestDirectory();
        var link = new NativeHomeLink(Path.Combine(folder.Path, "owned.json"));
        link.Remove(folder.Path);
        Assert.Null(new DirectoryInfo(link.LinkPath).LinkTarget);
    }

    [Fact]
    public void CleanupRemovesALinkWhoseTargetWasAlreadyDeleted()
    {
        using var folder = new TestDirectory();
        var home = Path.Combine(folder.Path, "gone");
        Directory.CreateDirectory(home);
        var link = new NativeHomeLink(Path.Combine(folder.Path, "owned.json"));
        link.Create(home);
        try
        {
            Directory.Delete(home);
            link.Remove(home);
            Assert.Null(new DirectoryInfo(link.LinkPath).LinkTarget);
        }
        finally
        {
            if (new DirectoryInfo(link.LinkPath).LinkTarget is not null)
                link.Remove(home);
        }
    }

    [Fact]
    public async Task CleanupDoesNotDeleteAnUnrelatedFileAtTheLinkAddress()
    {
        using var folder = new TestDirectory();
        var link = new NativeHomeLink(Path.Combine(folder.Path, "owned.json"));
        await File.WriteAllTextAsync(link.LinkPath, "keep");
        try
        {
            Assert.Throws<IOException>(() => link.Remove(folder.Path));
            Assert.Equal("keep", await File.ReadAllTextAsync(link.LinkPath));
        }
        finally { File.Delete(link.LinkPath); }
    }

    [Fact]
    public void InterruptedWorkCleanupRemovesItsLinkAndKeepsItsReport()
    {
        using var folder = new TestDirectory();
        var registry = Path.Combine(folder.Path, "owned.json");
        var manager = new WorkDirectoryManager(registry);
        var pair = new RunFolderAllocator().Create(folder.Path, folder.Path, DateTimeOffset.UtcNow);
        manager.Create(pair);
        var address = manager.PrepareNativeHome(pair.Work);
        manager.CleanupPrevious();
        Assert.Null(new DirectoryInfo(address).LinkTarget);
        Assert.False(Directory.Exists(pair.Work));
        Assert.True(Directory.Exists(pair.Report));
    }

    [Fact]
    public async Task RuntimeReceivesTheSameShortAddressAsHostCommands()
    {
        using var folder = new TestDirectory();
        var manager = new WorkDirectoryManager(Path.Combine(folder.Path, "owned.json"));
        var config = new Configuration(new Node(null, [], null, Path.Combine(folder.Path, "app.yaml")));
        var pair = new RunFolderAllocator().Create(folder.Path, folder.Path, DateTimeOffset.UtcNow);
        var state = new RunState(config, pair, new RunDeadline(DateTimeOffset.UtcNow.AddMinutes(1)));
        await new WorkPreparation(manager, new FakeCommandRunner(), new RuntimePaths(folder.Path)).Execute(state);
        try
        {
            Assert.Equal(state.Environment["MOBILECLI_HOME"], RuntimeRequest.Create(state)["nativeHome"]);
            Assert.Equal(Path.Combine(state.Work, "mobilecli"),
                new DirectoryInfo(state.Environment["MOBILECLI_HOME"]).LinkTarget);
        }
        finally { manager.Remove(state.Work); }
    }
}
