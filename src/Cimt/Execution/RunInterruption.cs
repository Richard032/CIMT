using System.Runtime.InteropServices;

namespace Cimt;

/// <summary>Turns terminal interruption into a shared, reportable stop request.</summary>
public sealed class RunInterruption(string report) : IDisposable
{
    private readonly CancellationTokenSource source = new();
    private PosixSignalRegistration? termination;
    private bool listening;
    public CancellationToken Token => source.Token;

    public void Listen()
    {
        Console.CancelKeyPress += OnCancel;
        if (!OperatingSystem.IsWindows())
            termination = PosixSignalRegistration.Create(PosixSignal.SIGTERM, context =>
            {
                context.Cancel = true;
                Request();
            });
        listening = true;
    }

    public void Request()
    {
        if (source.IsCancellationRequested)
            return;
        // The child also checks this marker when terminal signals do not reach it.
        try { File.WriteAllText(Path.Combine(report, "stop-requested"), "User interruption"); }
        catch (IOException) { /* The token still stops the host if storage is unavailable. */ }
        catch (UnauthorizedAccessException) { /* Report writing will explain inaccessible storage. */ }
        source.Cancel();
        try { Console.Error.WriteLine("CIMT stop requested. Saving partial results and the report."); }
        catch (IOException) { /* The report can still be written if the terminal has closed. */ }
    }

    private void OnCancel(object? sender, ConsoleCancelEventArgs args)
    {
        args.Cancel = true;
        Request();
    }

    public void Dispose()
    {
        if (listening)
            Console.CancelKeyPress -= OnCancel;
        termination?.Dispose();
        source.Dispose();
    }
}
