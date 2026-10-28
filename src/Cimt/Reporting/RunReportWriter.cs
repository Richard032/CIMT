using System.Text.Json;

namespace Cimt;

/// <summary>Writes the final machine result and its HTML view.</summary>
public sealed class RunReportWriter : IRunReportWriter
{
    public int Write(RunState state)
    {
        var execution = ReadExecution(state.Report);
        var outcome = RunOutcomePolicy.Evaluate(state.Exit, execution);
        WriteMachineResult(state, outcome, execution);
        var renderer = new RunHtmlRenderer(state.Configuration);
        File.WriteAllText(Path.Combine(state.Report, "index.html"), renderer.Render(state, outcome, execution));
        Console.WriteLine("CIMT run finished with exit " + outcome.ExitCode + ". Report: " + Path.Combine(state.Report, "index.html"));
        return outcome.ExitCode;
    }

    private static JsonElement? ReadExecution(string report)
    {
        var path = Path.Combine(report, "ui-results.json");
        return File.Exists(path) ? JsonSerializer.Deserialize<JsonElement>(File.ReadAllText(path)) : null;
    }

    private static void WriteMachineResult(RunState state, RunOutcome outcome, JsonElement? execution)
    {
        var value = new
        {
            command = "run",
            sourceBranch = state.Configuration.Root.Get("repository")!.Value("branch"),
            sourceCommit = state.Commit,
            started = state.Started,
            finished = DateTimeOffset.UtcNow,
            exitCode = outcome.ExitCode,
            verdict = outcome.Verdict,
            completion = outcome.Completion,
            stages = state.Stages,
            builds = state.Builds,
            errors = state.Errors,
            execution
        };
        var json = JsonSerializer.Serialize(value, new JsonSerializerOptions { WriteIndented = true });
        File.WriteAllText(Path.Combine(state.Report, "result.json"), state.Configuration.Scrub(json));
    }
}
