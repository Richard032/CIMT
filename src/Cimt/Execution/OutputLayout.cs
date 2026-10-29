namespace Cimt;

/// <summary>Places generated files beside the user's run inputs, not beside the executable.</summary>
public sealed class OutputLayout(string inputFolder)
{
    public string InputFolder { get; } = Path.GetFullPath(inputFolder);
    public string Root => Path.Combine(InputFolder, "CIMT output");
    public string WorkRoot => Path.Combine(Root, "work");
    public string ReportsRoot => Path.Combine(Root, "reports");

    public static OutputLayout ForFile(string file) => new(Path.GetDirectoryName(Path.GetFullPath(file))!);

    public static OutputLayout ForCommand(CommandOptions options)
    {
        // Shared settings may live elsewhere. The run configuration selects the input folder.
        var file = options.Values.GetValueOrDefault("--run-config") ?? options.Values["--config"];
        return ForFile(file);
    }

    public void Check()
    {
        if (!Directory.Exists(InputFolder))
            throw new ConfigurationException("The input folder does not exist.");
        // An existing link must not send generated files outside the input folder.
        RunFolderSafety.Inside(InputFolder, Root);
        RunFolderSafety.Inside(Root, WorkRoot);
        RunFolderSafety.Inside(Root, ReportsRoot);
    }
}
