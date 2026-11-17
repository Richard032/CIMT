using System.Text.Json;

namespace Cimt;

/// <summary>Writes partial and final machine results and their HTML view.</summary>
public sealed class RunReportWriter : IRunReportWriter
{
    public void Write(RunState state, RunReportData data)
    {
        var (outcome, execution, coverage, final) = data;
        var activity = RunActivityLog.Read(state.Report, state.Configuration.Scrub);
        WriteMachineResult(state, outcome, execution, coverage, activity, final);
        var renderer = new RunHtmlRenderer(state.Configuration);
        WriteAtomic(Path.Combine(state.Report, "index.html"), renderer.Render(state, outcome, execution, coverage, activity, !final));
        if (final)
            Console.WriteLine("CIMT " + state.Command + " finished with exit " + outcome.ExitCode + ". Report: " + Path.Combine(state.Report, "index.html"));
    }

    private static void WriteMachineResult(RunState state, RunOutcome outcome, JsonElement? execution, RequirementCoverage coverage,
        IReadOnlyList<RunActivityEntry> activity, bool final)
    {
        var value = new
        {
            command = state.Command,
            runIdentity = state.Identity,
            sourceBranch = state.Configuration.Root.Get("repository")!.Value("branch"),
            sourceCommit = state.Commit,
            started = state.Started,
            finished = state.Finished,
            inProgress = !final,
            updated = DateTimeOffset.UtcNow,
            durationSeconds = Math.Max(0, ((state.Finished ?? DateTimeOffset.UtcNow) - state.Started).TotalSeconds),
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
        WriteAtomic(Path.Combine(state.Report, "result.json"), safe.ToJsonString(options));
    }

    private static void WriteAtomic(string path, string text)
    {
        // A killed process leaves the previous complete page available to the user.
        File.WriteAllText(path + ".partial", text);
        File.Move(path + ".partial", path, overwrite: true);
    }
}
