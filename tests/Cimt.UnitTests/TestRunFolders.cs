using Cimt;

namespace Cimt.UnitTests;

/// <summary>Policy tests use virtual paths. Folder lifecycle tests use the real allocator.</summary>
internal static class TestRunFolders
{
    public static RunFolders At(string report, DateTimeOffset started) =>
        new(RunIdentity.At(started), Path.Combine(Path.GetDirectoryName(report)!, "unused-work"), report);
}
