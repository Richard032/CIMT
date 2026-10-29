namespace Cimt;

/// <summary>Stops the native helper at the caller's owned address.</summary>
public static class NativeHelperStop
{
    public static Task<ProcessResult> Execute(ICommandRunner runner, RuntimePaths paths,
        Dictionary<string, string> environment) => runner.Run(new("node", ["-e",
            "const {Mobilecli}=require(process.argv[1]);console.log(new Mobilecli().executeCommand(['daemon','stop'],15000));",
            paths.NativeModule], 20, environment));
}
