using System.Text.Json;

namespace Cimt;

/// <summary>Holds run data. Services perform the work; this object only stores results.</summary>
public sealed class RunState(Configuration configuration, string report, DateTimeOffset started, RunDeadline deadline)
{
    public Configuration Configuration { get; } = configuration;
    public string Report { get; } = report;
    public DateTimeOffset Started { get; } = started;
    public RunDeadline Deadline { get; } = deadline;
    public string Work { get; set; } = "";
    public string Commit { get; set; } = "";
    public string? NativeBinary
    {
        get; set;
    }
    public int Exit
    {
        get; set;
    }
    public int UiExit { get; set; } = 2;
    public List<object> Stages { get; } = [];
    public List<string> Errors { get; } = [];
    public List<Dictionary<string, string>> Builds { get; } = [];
    public List<Dictionary<string, string>> Devices { get; } = [];
    public Dictionary<string, string> Inputs { get; } = [];
    public Dictionary<string, string> Environment
    {
        get;
    } = new()
    {
        ["GIT_TERMINAL_PROMPT"] = "0",
        ["GCM_INTERACTIVE"] = "never"
    };
}

/// <summary>Maps installation paths used by the execution services.</summary>
public sealed class RuntimePaths(string root)
{
    public string NativeModule => Path.Combine(root, "tools/node-packages/lib/node_modules/@mobilenext/mobile-mcp/lib/mobilecli.js");
    public string Worker => Path.Combine(root, "lib/cimt-runtime/run_ui.py");
    public string Python => Path.Combine(root, "tools/python/bin/python");
    public string BuildScript(string platform) => Path.Combine(root, "scripts/build/" + platform + ".sh");
}

/// <summary>Applies the shared deadline to process calls made during a run.</summary>
public sealed class RunProcess(ICommandRunner runner)
{
    public async Task<ProcessResult> Invoke(RunState state, string tool, IEnumerable<string> arguments,
        int maximum = 120, string? input = null)
    {
        try
        {
            return await runner.Run(new(tool, arguments, state.Deadline.RemainingSeconds(maximum),
                state.Environment, Input: input));
        }
        catch (ConfigurationException) when (state.Deadline.HasExpired)
        {
            throw new RunLimitException("Whole-run time limit reached");
        }
    }
}

public interface IRunProgress
{
    void Write(RunState state, string stage);
}

/// <summary>Writes progress without exposing the private runtime request.</summary>
public sealed class RunProgress : IRunProgress
{
    public void Write(RunState state, string stage)
    {
        Console.WriteLine(stage);
        File.WriteAllText(Path.Combine(state.Report, "progress.json"), JsonSerializer.Serialize(new
        {
            stage,
            sourceCommit = state.Commit,
            updated = DateTimeOffset.UtcNow
        }));
    }
}
