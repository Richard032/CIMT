namespace Cimt;

/// <summary>Creates real command services at the application boundary.</summary>
public static class Entry
{
    public static async Task<int> Run(string[] arguments)
    {
        using var http = new HttpClient { Timeout = TimeSpan.FromSeconds(20) };
        var readiness = new ReadinessValidator(new CommandRunner(), new TextInputReader(http));
        var application = new CommandApplication(new ConfigurationLoader(), readiness, RunEngine.Execute,
            new CommandReports(), new RunFolderAllocator(), () => new MachineLock(), Console.Out, Console.Error,
            replay: RunEngine.Replay);
        return await application.Run(arguments);
    }
}
