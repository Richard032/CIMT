using System.Text.Json;
using Cimt;

namespace Cimt.UnitTests;

/// <summary>Readiness and error reports use the identity selected by the command.</summary>
public sealed class CommandIdentityReportTests
{
    [Fact]
    public async Task ErrorResultAndHtmlKeepTheAllocatedIdentity()
    {
        using var folder = new TestDirectory();
        var started = DateTimeOffset.UnixEpoch;
        var pair = new RunFolderAllocator().Create(folder.Path, folder.Path, started);
        var session = new CommandSession(started) { Folders = pair };
        session.Messages.Add("fixture error");
        await new CommandReports().Write(session, "inconclusive", "incomplete", 3);
        using var json = JsonDocument.Parse(File.ReadAllText(Path.Combine(pair.Report, "result.json")));
        Assert.Equal(pair.Identity.Id, json.RootElement.GetProperty("runIdentity").GetProperty("id").GetString());
        Assert.Contains(pair.Identity.Id, File.ReadAllText(Path.Combine(pair.Report, "index.html")));
        Assert.False(Directory.Exists(pair.Work));
    }
}
