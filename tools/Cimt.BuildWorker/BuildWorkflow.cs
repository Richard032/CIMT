namespace Cimt.Build;

/// <summary>Orders publish, artifact selection, and metadata output for one build.</summary>
public sealed class BuildWorkflow(IBuildProcess process, BuildLog log)
{
    /// <summary>Publish one target and write success metadata only after its artifact is verified.</summary>
    public async Task<int> Execute(BuildRequest request)
    {
        var output = CreateOutputFolder(request);
        Console.WriteLine("Publishing configured " + request.Platform + " application target.");
        var built = await process.Run(BuildCommands.Publish(request, output), request.Repository);
        log.ProcessOutput(built);
        if (built.Exit != 0)
            return built.Exit;
        var artifact = BuildArtifacts.Resolve(request, output);
        var metadata = await process.Run(BuildCommands.Metadata(request), request.Repository);
        var appId = AppIdResolver.Resolve(metadata, request.AppIdFallback);
        await BuildResultWriter.Write(request.ResultFile, artifact, appId);
        Console.WriteLine("Build result written: " + request.ResultFile);
        return 0;
    }

    private static string CreateOutputFolder(BuildRequest request)
    {
        var folder = Path.Combine(Path.GetDirectoryName(request.ResultFile)!,
            "build_" + request.Platform + "_" + Guid.NewGuid().ToString("N"));
        Directory.CreateDirectory(folder);
        return folder;
    }
}

/// <summary>Connects production build services and handles command failures.</summary>
public static class BuildEntry
{
    public static async Task<int> Run(string[] arguments)
    {
        var log = new BuildLog(Console.Out, Console.Error);
        try
        {
            var request = LoadRequest(arguments);
            log.Configure(request.Properties);
            var executable = Environment.GetEnvironmentVariable("CIMT_DOTNET_EXECUTABLE") ?? "dotnet";
            return await new BuildWorkflow(new BuildProcess(executable), log).Execute(request);
        }
        catch (Exception error)
        {
            log.Error(error.Message);
            return 3;
        }
    }

    private static BuildRequest LoadRequest(string[] arguments)
    {
        if (arguments.Length != 1 || arguments[0] is not ("android" or "ios"))
            throw new InvalidOperationException("Build platform must be android or ios.");
        var loader = new BuildRequestLoader(Environment.GetEnvironmentVariable);
        var resultFile = Path.GetFullPath(loader.RequiredEnvironment("CIMT_BUILD_RESULT"));
        // Remove old success metadata before reading or building the new request.
        if (File.Exists(resultFile))
            File.Delete(resultFile);
        return loader.Load(arguments[0], resultFile);
    }
}
