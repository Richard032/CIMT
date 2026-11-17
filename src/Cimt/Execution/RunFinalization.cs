using System.Text.Json;

namespace Cimt;

public sealed record RunReportData(RunOutcome Outcome, JsonElement? Execution,
    RequirementCoverage Coverage, bool Final);

/// <summary>Owns outcome calculation and supplies the same snapshot to the report and exit code.</summary>
public static class RunFinalization
{
    public static int Finish(RunState state, IRunReportWriter reports)
    {
        JsonElement? execution = null;
        try
        {
            execution = RuntimeResults.Read(state.Report);
        }
        catch (ConfigurationException error)
        {
            if (!state.Errors.Contains(error.Message))
            {
                state.Errors.Add(error.Message);
                state.StopReasons.Add(new("Infrastructure failure", "Worker results", error.Message));
            }
            state.Exit = ExitCodes.Combine(state.Exit, 3);
        }

        var data = Evaluate(state, execution, final: true);
        var outcome = data.Outcome;
        state.Exit = outcome.ExitCode;
        state.Finished = DateTimeOffset.UtcNow;
        state.Activity.Record("Run finished", "finished", "Exit " + outcome.ExitCode
            + "; verdict " + outcome.Verdict + "; completion " + outcome.Completion);
        reports.Write(state, data);
        return outcome.ExitCode;
    }

    public static void Snapshot(RunState state, IRunReportWriter reports)
    {
        try
        {
            reports.Write(state, Evaluate(state, RuntimeResults.Read(state.Report), final: false));
        }
        catch (Exception error) when (error is IOException or UnauthorizedAccessException or ConfigurationException)
        {
            Console.Error.WriteLine("Interim report could not be updated: "
                + (error is ConfigurationException ? error.Message : error.GetType().Name));
        }
    }

    private static RunReportData Evaluate(RunState state, JsonElement? execution, bool final)
    {
        var coverage = RequirementReportBuilder.Build(state.Requirements, RequirementScopes.Create(state),
            execution, state.Inputs.GetValueOrDefault("instructions", ""),
            RequirementCatalogue.Hash(state.Inputs.GetValueOrDefault("requirements", "")));
        var outcome = RunOutcomePolicy.Evaluate(state.Exit, execution, coverage);
        if (!final || state.Cancellation.IsCancellationRequested)
            outcome = new(ExitCodes.Combine(outcome.ExitCode, 2), outcome.Verdict, "incomplete");
        return new(outcome, execution, coverage, final);
    }
}
