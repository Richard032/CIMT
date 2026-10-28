namespace Cimt;

/// <summary>Lets tests replace execution without adding a forwarding service.</summary>
public delegate Task<int> RunApplication(Configuration configuration, string report, DateTimeOffset started);

/// <summary>Holds command data while errors may still need a report.</summary>
public sealed class CommandSession(DateTimeOffset started)
{
    public DateTimeOffset Started { get; } = started;
    public Configuration? Configuration
    {
        get; set;
    }
    public string? Report
    {
        get; set;
    }
    public List<string> Messages { get; } = [];
}

/// <summary>Routes one command to a handler and converts failures into reports.</summary>
public sealed class CommandApplication(IConfigurationLoader configurations, IReadinessValidator readiness,
    RunApplication run, ICommandReports reports, Func<IDisposable> acquireLock,
    TextWriter output, TextWriter errors, TimeProvider? clock = null)
{
    /// <summary>Route one command and write a safe error report if it fails.</summary>
    public async Task<int> Run(string[] arguments)
    {
        var session = new CommandSession((clock ?? TimeProvider.System).GetUtcNow());
        try
        {
            var options = CommandLine.Parse(arguments);
            if (options.IsHelp)
                return ShowHelp();
            return await Execute(options, session);
        }
        catch (Exception error)
        {
            return await ReportFailure(session, error);
        }
    }

    private async Task<int> Execute(CommandOptions options, CommandSession session)
    {
        session.Configuration = configurations.Load(options);
        session.Configuration.Validate();
        session.Report = reports.Create(session.Configuration.ReportsRoot);
        using var held = acquireLock();
        await reports.SaveConfiguration(session);
        if (options.Command == "run")
            return await run(session.Configuration, session.Report, session.Started);
        if (options.Command != "validate")
            throw new ConfigurationException("The " + options.Command + " execution engine is not implemented yet. No application was built, installed, reset, or tested.");
        return await Validate(session);
    }

    private async Task<int> Validate(CommandSession session)
    {
        await readiness.Validate(session.Configuration!, session.Messages);
        session.Messages.Add("Configuration/readiness checks passed. Model access, signing, login, application behaviour and strict billing enforcement require execution-time validation.");
        await reports.Write(session, "passed", "complete", 0);
        output.WriteLine("Validation passed. Report: " + Path.Combine(session.Report!, "index.html"));
        return 0;
    }

    private async Task<int> ReportFailure(CommandSession session, Exception error)
    {
        var message = error is ConfigurationException ? error.Message
            : "Configuration or readiness operation failed (" + error.GetType().Name + ").";
        message = session.Configuration?.Scrub(message) ?? message;
        session.Messages.Add(message);
        try
        {
            session.Report ??= reports.Create(reports.ErrorRoot(session.Configuration));
            await reports.Write(session, "inconclusive", "incomplete", 3);
            errors.WriteLine(message + " Report: " + Path.Combine(session.Report, "index.html"));
        }
        catch
        {
            errors.WriteLine("CIMT could not write an error report. Check report-folder permissions.");
        }
        return 3;
    }

    private int ShowHelp()
    {
        output.WriteLine("CIMT — Curtis Intelligent Mobile Test\nCommands: setup, validate, run, replay\nOptions: --config <YAML> [--run-config <YAML>] [--branch <branch>] [--scenario <saved-scenario>]");
        return 0;
    }
}
