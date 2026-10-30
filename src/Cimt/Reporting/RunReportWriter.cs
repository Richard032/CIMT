using System.Text.Json;
using System.Text.Json.Nodes;

namespace Cimt;

/// <summary>Writes partial and final machine results and their HTML view.</summary>
public sealed class RunReportWriter : IRunReportWriter
{
    public int Write(RunState state)
    {
        return WriteReport(state, final: true);
    }

    public void Snapshot(RunState state)
    {
        try { WriteReport(state, final: false); }
        catch (IOException error) { Console.Error.WriteLine("Interim report could not be updated: " + error.GetType().Name); }
        catch (UnauthorizedAccessException error) { Console.Error.WriteLine("Interim report could not be updated: " + error.GetType().Name); }
    }

    private static int WriteReport(RunState state, bool final)
    {
        var execution = ReadExecution(state.Report);
        var coverage = RequirementReportBuilder.Build(state.Requirements, RequirementScopes.Create(state),
            execution, state.Inputs.GetValueOrDefault("instructions", ""),
            RequirementCatalogue.Hash(state.Inputs.GetValueOrDefault("requirements", "")));
        var outcome = RunOutcomePolicy.Evaluate(state.Exit, execution, coverage);
        if (!final || state.Cancellation.IsCancellationRequested)
            outcome = new(ExitCodes.Combine(outcome.ExitCode, 2), outcome.Verdict, "incomplete");
        if (final)
        {
            state.Activity.Record("Run finished", "finished", "Exit " + outcome.ExitCode
                + "; verdict " + outcome.Verdict + "; completion " + outcome.Completion);
            state.Finished = DateTimeOffset.UtcNow;
        }
        var activity = RunActivityLog.Read(state.Report, state.Configuration.Scrub);
        WriteMachineResult(state, outcome, execution, coverage, activity, final);
        var renderer = new RunHtmlRenderer(state.Configuration);
        WriteAtomic(Path.Combine(state.Report, "index.html"), renderer.Render(state, outcome, execution, coverage, activity, !final));
        if (final)
            Console.WriteLine("CIMT " + state.Command + " finished with exit " + outcome.ExitCode + ". Report: " + Path.Combine(state.Report, "index.html"));
        return outcome.ExitCode;
    }

    private static JsonElement? ReadExecution(string report)
    {
        var path = Path.Combine(report, "ui-results.json");
        if (!File.Exists(path))
            return null;
        var data = JsonNode.Parse(File.ReadAllText(path))!;
        var budget = Path.Combine(report, "ai-budget.json");
        if (File.Exists(budget))
            data["budget"] = JsonNode.Parse(File.ReadAllText(budget));
        return JsonSerializer.SerializeToElement(data);
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
