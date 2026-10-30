using System.Diagnostics;

namespace Cimt;

/// <summary>Describes one process call. Input can contain secrets and must not be logged.</summary>
public sealed record ProcessCommand(string Executable, IEnumerable<string> Arguments, int TimeoutSeconds,
    Dictionary<string, string>? Environment = null, string? WorkingDirectory = null, string? Input = null,
    Action<string>? OutputLine = null);

public sealed record ProcessResult(int Exit, string Stdout, string Stderr);

/// <summary>Tests replace this boundary so they do not start real tools.</summary>
public interface ICommandRunner
{
    Task<ProcessResult> Run(ProcessCommand command);
}

/// <summary>Starts operating-system processes and collects their output.</summary>
public sealed class CommandRunner : ICommandRunner
{
    public async Task<ProcessResult> Run(ProcessCommand command)
    {
        using var process = Process.Start(CreateStartInfo(command))
            ?? throw new ConfigurationException("Unable to start a required tool.");
        // Read both streams together. A full error stream must not block the child.
        var stdout = Read(process.StandardOutput, command.OutputLine);
        var stderr = Read(process.StandardError, command.OutputLine);
        await WaitForCompletion(process, command);
        return new(process.ExitCode, await stdout, await stderr);
    }

    private static async Task<string> Read(StreamReader reader, Action<string>? output)
    {
        if (output is null)
            return await reader.ReadToEndAsync();
        var text = new System.Text.StringBuilder();
        while (await reader.ReadLineAsync() is { } line)
        {
            text.AppendLine(line);
            output(line);
        }
        return text.ToString();
    }

    private static ProcessStartInfo CreateStartInfo(ProcessCommand command)
    {
        var info = new ProcessStartInfo(command.Executable)
        {
            UseShellExecute = false,
            RedirectStandardOutput = true,
            RedirectStandardError = true,
            RedirectStandardInput = command.Input is not null
        };
        if (command.WorkingDirectory is not null)
            info.WorkingDirectory = command.WorkingDirectory;
        foreach (var argument in command.Arguments)
            info.ArgumentList.Add(argument);
        if (command.Environment is not null)
            foreach (var (key, value) in command.Environment)
                info.Environment[key] = value;
        return info;
    }

    private static async Task WaitForCompletion(Process process, ProcessCommand command)
    {
        using var cancellation = new CancellationTokenSource(TimeSpan.FromSeconds(command.TimeoutSeconds));
        try
        {
            if (command.Input is not null)
            {
                await process.StandardInput.WriteAsync(command.Input.AsMemory(), cancellation.Token);
                process.StandardInput.Close();
            }
            await process.WaitForExitAsync(cancellation.Token);
        }
        catch (OperationCanceledException)
        {
            process.Kill(entireProcessTree: true);
            await process.WaitForExitAsync();
            throw new ConfigurationException("A required operation timed out.");
        }
    }
}
