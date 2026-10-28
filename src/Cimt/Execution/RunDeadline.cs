namespace Cimt;

/// <summary>Measures the time left for the whole run, including builds.</summary>
public sealed class RunDeadline(DateTimeOffset end, TimeProvider? clock = null)
{
    private readonly TimeProvider clock = clock ?? TimeProvider.System;
    public DateTimeOffset End { get; } = end;
    public bool HasExpired => clock.GetUtcNow() >= End;

    /// <summary>Return the smaller time limit, or stop when the whole run has expired.</summary>
    public int RemainingSeconds(int operationLimit)
    {
        var seconds = (int)(End - clock.GetUtcNow()).TotalSeconds;
        if (seconds <= 0)
            throw new RunLimitException("Whole-run time limit reached");
        return Math.Min(operationLimit, seconds);
    }
}

public sealed class RunLimitException(string message) : Exception(message);
