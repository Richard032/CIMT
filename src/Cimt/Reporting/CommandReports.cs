using System.Net;
using System.Text.Json;

namespace Cimt;

public interface ICommandReports
{
    string ErrorRoot(Configuration? configuration);
    Task SaveConfiguration(CommandSession session);
    Task Write(CommandSession session, string verdict, string completion, int exit);
}

/// <summary>Stores configuration/readiness reports; these are not app test results.</summary>
public sealed class CommandReports : ICommandReports
{
    private static readonly JsonSerializerOptions JsonOptions = new() { WriteIndented = true, PropertyNamingPolicy = JsonNamingPolicy.CamelCase };

    public string ErrorRoot(Configuration? configuration)
    {
        try
        {
            return configuration?.ReportsRoot ?? DefaultRoot();
        }
        catch (ConfigurationException) { return DefaultRoot(); }
        catch (ArgumentException) { return DefaultRoot(); }
    }

    public Task SaveConfiguration(CommandSession session)
    {
        var configuration = session.Configuration!;
        var json = JsonSerializer.Serialize(configuration.Sanitized(configuration.Root), JsonOptions);
        return File.WriteAllTextAsync(Path.Combine(session.Report!, "effective-config.json"), json);
    }

    public async Task Write(CommandSession session, string verdict, string completion, int exit)
    {
        var messages = session.Messages.Select(message => session.Configuration?.Scrub(message) ?? message).ToArray();
        var value = new
        {
            runIdentity = session.Folders!.Identity,
            commandResult = verdict,
            completion,
            exitCode = exit,
            messages
        };
        await File.WriteAllTextAsync(Path.Combine(session.Report!, "result.json"), JsonSerializer.Serialize(value, JsonOptions));
        await File.WriteAllTextAsync(Path.Combine(session.Report!, "index.html"), Render(session.Folders!.Identity, verdict, completion, exit, messages));
    }

    private static string Render(RunIdentity identity, string verdict, string completion, int exit, IEnumerable<string> messages)
    {
        var items = string.Join("", messages.Select(message => "<li>" + WebUtility.HtmlEncode(message) + "</li>"));
        return "<!doctype html><html lang=\"en\"><meta charset=\"utf-8\"><title>CIMT report</title>"
            + "<style>body{font:16px system-ui;max-width:1000px;margin:3rem auto;padding:0 1rem;color:#172333}li{margin:.8rem 0}</style>"
            + "<h1>CIMT report</h1><p>Run: " + WebUtility.HtmlEncode(identity.Id) + " (UTC)</p><p>Verdict: <strong>" + WebUtility.HtmlEncode(verdict) + "</strong> · Completion: "
            + WebUtility.HtmlEncode(completion) + " · Exit code: " + exit + "</p><h2>Checks and observations</h2><ul>"
            + items + "</ul><p>This is a configuration/readiness report. It contains no application test results.</p></html>";
    }

    private static string DefaultRoot() => Path.Combine(Configuration.InstallationRoot, "reports");
}
