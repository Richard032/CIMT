using System.Diagnostics;
using System.Text.RegularExpressions;
using Cimt.Secrets;

namespace Cimt.Build;

public sealed record BuildProcessResult(int Exit, string Output, string Error);

public interface IBuildProcess
{
    Task<BuildProcessResult> Run(IEnumerable<string> arguments, string workingDirectory);
}

/// <summary>Runs dotnet and captures both output streams.</summary>
public sealed class BuildProcess(string executable) : IBuildProcess
{
    public async Task<BuildProcessResult> Run(IEnumerable<string> arguments, string workingDirectory)
    {
        var info = new ProcessStartInfo(executable)
        {
            UseShellExecute = false,
            RedirectStandardOutput = true,
            RedirectStandardError = true,
            WorkingDirectory = workingDirectory
        };
        foreach (var argument in arguments)
            info.ArgumentList.Add(argument);
        using var process = Process.Start(info) ?? throw new InvalidOperationException("Unable to start dotnet.");
        var output = process.StandardOutput.ReadToEndAsync();
        var error = process.StandardError.ReadToEndAsync();
        await process.WaitForExitAsync();
        return new(process.ExitCode, await output, await error);
    }
}

/// <summary>Removes configured signing secrets before writing build diagnostics.</summary>
public sealed class BuildLog(TextWriter output, TextWriter errors)
{
    private SecretText text = new([]);

    public void Configure(Dictionary<string, string> properties)
    {
        text = new SecretText(properties.Where(property => Regex.IsMatch(property.Key, "pass|secret|token|key", RegexOptions.IgnoreCase))
            .Select(property => property.Value));
    }

    public string Scrub(string value) => text.Scrub(value);

    public void ProcessOutput(BuildProcessResult result)
    {
        output.Write(Scrub(result.Output));
        errors.Write(Scrub(result.Error));
    }

    public void Error(string message) => errors.WriteLine(Scrub(message));
}
