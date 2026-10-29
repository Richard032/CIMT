namespace Cimt;

/// <summary>Lets tests replace execution without adding a forwarding service.</summary>
public delegate Task<int> RunApplication(Configuration configuration, RunFolders folders);

/// <summary>Holds command data while errors may still need a report.</summary>
public sealed class CommandSession(DateTimeOffset started)
{
    public DateTimeOffset Started { get; } = started;
    public Configuration? Configuration
    {
        get; set;
    }
    public OutputLayout Outputs { get; set; } = new(Directory.GetCurrentDirectory());
    public RunFolders? Folders
    {
        get; set;
    }
    public string? Report => Folders?.Report;
    public List<string> Messages { get; } = [];
}

/// <summary>Routes one command to a handler and converts failures into reports.</summary>
public sealed class CommandApplication(IConfigurationLoader configurations, IReadinessValidator readiness,
    RunApplication run, ICommandReports reports, RunFolderAllocator folders, Func<IDisposable> acquireLock,
    TextWriter output, TextWriter errors, TimeProvider? clock = null, RunApplication? replay = null)
{
    /// <summary>Route one command and write a safe error report if it fails.</summary>
    public async Task<int> Run(string[] arguments)
    {
        var session = new CommandSession((clock ?? TimeProvider.System).GetUtcNow());
        IDisposable? held = null;
        try
        {
            var options = CommandLine.Parse(arguments);
            if (options.IsHelp)
                return ShowHelp();
            session.Outputs = OutputLayout.ForCommand(options);
            held = acquireLock();
            return await Execute(options, session);
        }
        catch (Exception error)
        {
            return await ReportFailure(session, error);
        }
        finally
        {
            // Keep the lock until error reporting has finished too.
            held?.Dispose();
        }
    }

    private async Task<int> Execute(CommandOptions options, CommandSession session)
    {
        session.Configuration = configurations.Load(options);
        session.Outputs = session.Configuration.Outputs;
        session.Configuration.Validate();
        session.Outputs.Check();
        session.Folders = folders.Create(session.Configuration.WorkspaceRoot, session.Configuration.ReportsRoot, session.Started);
        DescribeOutputLayout(session);
        await reports.SaveConfiguration(session);
        if (options.Command == "run")
            return await run(session.Configuration, session.Folders);
        if (options.Command == "replay" && replay is not null)
        {
            if (options.Values.ContainsKey("--scenario"))
                throw new ConfigurationException("Saved action-history replay is not implemented yet. Omit --scenario to execute current instructions using retained app builds.");
            return await replay(session.Configuration, session.Folders);
        }
        if (options.Command != "validate")
            throw new ConfigurationException("The " + options.Command + " execution engine is not implemented yet. No application was built, installed, reset, or tested.");
        return await Validate(session);
    }

    private void DescribeOutputLayout(CommandSession session)
    {
        output.WriteLine("CIMT output: " + session.Outputs.Root);
        if (session.Configuration!.HasLegacyOutputRoots)
        {
            const string notice = "Legacy workspace.root/reports.root settings are ignored; CIMT creates output inside the input folder.";
            session.Messages.Add(notice);
            output.WriteLine(notice);
        }
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
            session.Folders ??= CreateErrorFolders(session);
            await reports.Write(session, "inconclusive", "incomplete", 3);
            errors.WriteLine(message + " Report: " + Path.Combine(session.Report!, "index.html"));
        }
        catch
        {
            errors.WriteLine("CIMT could not write an error report. Check report-folder permissions.");
        }
        return 3;
    }

    private RunFolders CreateErrorFolders(CommandSession session)
    {
        // Even invalid configuration must keep its error report with the selected inputs.
        session.Outputs.Check();
        return folders.Create(session.Outputs.WorkRoot, session.Outputs.ReportsRoot, session.Started);
    }

    private int ShowHelp()
    {
        output.WriteLine("CIMT — Curtis Intelligent Mobile Test\nCommands: setup, validate, run, replay\nOptions: --config <YAML> [--run-config <YAML>] [--branch <branch>] [--scenario <saved-scenario>]");
        return 0;
    }
}
