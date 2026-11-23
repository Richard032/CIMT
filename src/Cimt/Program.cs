using Cimt;

#if DEBUG
if (Environment.GetEnvironmentVariable("CIMT_WAIT_FOR_DEBUGGER") == "1")
{
    Console.Error.WriteLine($"CIMT host PID {Environment.ProcessId} is waiting for a C# debugger.");
    while (!System.Diagnostics.Debugger.IsAttached)
        await Task.Delay(100);
}
#endif

return await Entry.Run(args);
