using System.Diagnostics;
using System.Globalization;
using System.Text.Json;

namespace Cimt;

public sealed record RunActivityEntry(DateTimeOffset Timestamp, string Operation, string Status,
    string Message = "", string Target = "", string Platform = "", string Device = "",
    double? DurationSeconds = null, string Log = "", string ExceptionType = "", string Details = "");

/// <summary>Saves safe activity records. Process arguments and private requests never enter this log.</summary>
public sealed class RunActivityLog(string report, Func<string, string> scrub)
{
    private static readonly JsonSerializerOptions Options = new()
    {
        PropertyNamingPolicy = JsonNamingPolicy.CamelCase,
        PropertyNameCaseInsensitive = true
    };
    private readonly object gate = new();

    public void Record(string operation, string status, string message = "", string target = "",
        string platform = "", string device = "", double? seconds = null, string log = "",
        Exception? error = null)
    {
        var entry = Safe(new(DateTimeOffset.UtcNow, operation, status, message, target, platform,
            device, seconds, log, error?.GetType().Name ?? "", error?.StackTrace ?? ""), scrub);
        lock (gate)
            File.AppendAllText(Path.Combine(report, "activity.jsonl"), JsonSerializer.Serialize(entry, Options) + "\n");
        Console.WriteLine("CIMT activity: " + entry.Timestamp.ToString("O", CultureInfo.InvariantCulture)
            + " [" + platform + "][" + target + "][" + device + "] " + operation + " — " + status
            + (seconds is { } elapsed ? " (" + elapsed.ToString("0.000", CultureInfo.InvariantCulture) + " seconds)" : "")
            + (entry.Message.Length == 0 ? "" : ": " + entry.Message));
    }

    public async Task Run(string operation, Func<Task> execute)
    {
        Record(operation, "started");
        var started = Stopwatch.GetTimestamp();
        try
        {
            await execute();
            Record(operation, "completed", seconds: Stopwatch.GetElapsedTime(started).TotalSeconds);
        }
        catch (Exception error)
        {
            Record(operation, error is RunLimitException ? "stopped" : "failed", error.Message,
                seconds: Stopwatch.GetElapsedTime(started).TotalSeconds, error: error);
            throw;
        }
    }

    public static IReadOnlyList<RunActivityEntry> Read(string report, Func<string, string> scrub)
    {
        var path = Path.Combine(report, "activity.jsonl");
        if (!File.Exists(path))
            return [];
        var entries = new List<RunActivityEntry>();
        var lineNumber = 0;
        foreach (var line in File.ReadLines(path))
        {
            lineNumber++;
            try
            {
                var entry = JsonSerializer.Deserialize<RunActivityEntry>(line, Options);
                if (entry is null || string.IsNullOrWhiteSpace(entry.Operation) || string.IsNullOrWhiteSpace(entry.Status))
                    throw new JsonException();
                entries.Add(Safe(entry, scrub));
            }
            catch (JsonException)
            {
                // A killed worker can leave its last line unfinished. Keep earlier evidence readable.
                entries.Add(new(DateTimeOffset.UtcNow, "Read activity journal", "warning",
                    "Activity record " + lineNumber + " is incomplete or invalid; its details are unavailable."));
            }
        }
        return entries.OrderBy(entry => entry.Timestamp).ToArray();
    }

    private static RunActivityEntry Safe(RunActivityEntry entry, Func<string, string> scrub) =>
        entry with { Message = scrub(entry.Message ?? ""), Details = scrub(entry.Details ?? "") };
}
