using System.Text.Json;

namespace Cimt;

/// <summary>Writes the final machine result and its HTML view.</summary>
public sealed class RunReportWriter : IRunReportWriter
{
    public int Write(RunState state)
    {
        var execution = ReadExecution(state.Report);
        var coverage = RequirementReportBuilder.Build(state.Requirements, RequirementScopes.Create(state),
            execution, state.Inputs.GetValueOrDefault("instructions", ""),
            RequirementCatalogue.Hash(state.Inputs.GetValueOrDefault("requirements", "")));
        var outcome = RunOutcomePolicy.Evaluate(state.Exit, execution, coverage);
        state.Activity.Record("Run finished", "finished", "Exit " + outcome.ExitCode
            + "; verdict " + outcome.Verdict + "; completion " + outcome.Completion);
        state.Finished = DateTimeOffset.UtcNow;
        var activity = RunActivityLog.Read(state.Report, state.Configuration.Scrub);
        WriteMachineResult(state, outcome, execution, coverage, activity);
        var renderer = new RunHtmlRenderer(state.Configuration);
        File.WriteAllText(Path.Combine(state.Report, "index.html"), renderer.Render(state, outcome, execution, coverage, activity));
        Console.WriteLine("CIMT " + state.Command + " finished with exit " + outcome.ExitCode + ". Report: " + Path.Combine(state.Report, "index.html"));
        return outcome.ExitCode;
    }

    private static JsonElement? ReadExecution(string report)
    {
        var path = Path.Combine(report, "ui-results.json");
        return File.Exists(path) ? JsonSerializer.Deserialize<JsonElement>(File.ReadAllText(path)) : null;
    }

    private static void WriteMachineResult(RunState state, RunOutcome outcome, JsonElement? execution, RequirementCoverage coverage,
        IReadOnlyList<RunActivityEntry> activity)
    {
        var value = new
        {
            command = state.Command,
            runIdentity = state.Identity,
            sourceBranch = state.Configuration.Root.Get("repository")!.Value("branch"),
            sourceCommit = state.Commit,
            started = state.Started,
            finished = state.Finished,
            durationSeconds = Math.Max(0, (state.Finished!.Value - state.Started).TotalSeconds),
            exitCode = outcome.ExitCode,
            verdict = outcome.Verdict,
            completion = outcome.Completion,
            stages = state.Stages,
            builds = state.Builds,
            errors = state.Errors,
            stoppingReasons = RunDiagnostics.StopReasons(state, execution, outcome),
            activity,
            requirementHeadings = state.RequirementHeadings,
            requirementCoverage = coverage,
            execution
        };
        var options = new JsonSerializerOptions { WriteIndented = true, PropertyNamingPolicy = JsonNamingPolicy.CamelCase };
        var source = JsonSerializer.SerializeToElement(value, options);
        var safe = new RunReportRedactor(new JsonTextRedactor(state.Configuration.Scrub)).Run(source);
        File.WriteAllText(Path.Combine(state.Report, "result.json"), safe.ToJsonString(options));
    }
}
