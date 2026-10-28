using System.Globalization;

namespace Cimt;

/// <summary>One invocation time and one shared UTC timestamp for both run folders.</summary>
public sealed record RunIdentity(DateTimeOffset Started, DateTimeOffset Timestamp)
{
    public string Id => Timestamp.ToUniversalTime().ToString("yyyy-MM-dd_HH-mm-ss-fff", CultureInfo.InvariantCulture);
    public string TimeZone => "UTC";

    public static RunIdentity At(DateTimeOffset started)
    {
        var utc = started.ToUniversalTime();
        var milliseconds = DateTimeOffset.FromUnixTimeMilliseconds(utc.ToUnixTimeMilliseconds());
        return new(utc, milliseconds);
    }

    // A collision changes the shared folder timestamp, never the actual invocation time.
    public RunIdentity Next() => this with { Timestamp = Timestamp.AddMilliseconds(1) };
}

/// <summary>Stores the folder pair selected for this identity. It does not create folders.</summary>
public sealed record RunFolders(RunIdentity Identity, string Work, string Report)
{
    public static RunFolders Under(string workRoot, string reportRoot, RunIdentity identity) =>
        new(identity, Path.Combine(Path.GetFullPath(workRoot), "work_" + identity.Id),
            Path.Combine(Path.GetFullPath(reportRoot), "report_" + identity.Id));
}
