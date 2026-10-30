using System.Net;
using System.Text.Json;

namespace Cimt;

public interface ICommandReports
{
    Task SaveConfiguration(CommandSession session);
    Task Write(CommandSession session, string verdict, string completion, int exit);
}

/// <summary>Stores configuration/readiness reports; these are not app test results.</summary>
public sealed class CommandReports : ICommandReports
{
    private static readonly JsonSerializerOptions JsonOptions = new() { WriteIndented = true, PropertyNamingPolicy = JsonNamingPolicy.CamelCase };

    public async Task SaveConfiguration(CommandSession session)
    {
        var configuration = session.Configuration!;
        var json = JsonSerializer.Serialize(configuration.Sanitized(configuration.Root), JsonOptions);
        await File.WriteAllTextAsync(Path.Combine(session.Report!, "effective-config.json"), json);
        // Record the new policy without changing the user's private configuration file.
        var layout = new
        {
            outputFolder = "CIMT output",
            workFolder = "work",
            reportsFolder = "reports",
            legacyRootSettingsIgnored = configuration.HasLegacyOutputRoots
        };
        await File.WriteAllTextAsync(Path.Combine(session.Report!, "output-layout.json"),
            JsonSerializer.Serialize(layout, JsonOptions));
    }

    public async Task Write(CommandSession session, string verdict, string completion, int exit)
    {
        var messages = session.Messages.Select(message => session.Configuration?.Scrub(message) ?? message).ToArray();
        var value = new
        {
            command = session.Command,
            runIdentity = session.Folders!.Identity,
            commandResult = verdict,
            completion,
            exitCode = exit,
            messages
        };
        await File.WriteAllTextAsync(Path.Combine(session.Report!, "result.json"), JsonSerializer.Serialize(value, JsonOptions));
        var html = Render(session.Folders!.Identity, verdict, completion, exit, messages, session.Command);
        await File.WriteAllTextAsync(Path.Combine(session.Report!, "index.html"), html);
    }

    private static string Render(RunIdentity identity, string verdict, string completion, int exit, IEnumerable<string> messages, string? command)
    {
        var items = string.Join("", messages.Select(message => "<li>" + WebUtility.HtmlEncode(message) + "</li>"));
        return ReportPage.Start(command ?? "unknown", identity.Id)
            + "<header class=\"report-header\"><h1>CIMT command report</h1><p>Run: " + WebUtility.HtmlEncode(identity.Id)
            + " (UTC)</p><p>Command: " + WebUtility.HtmlEncode(command ?? "unknown") + "</p></header>" + ReportPage.Navigation
            + "<main id=\"report-content\"><section id=\"overview\"><h2>Command overview</h2><p>Verdict: " + ReportHtml.Badge(verdict)
            + " · Completion: " + ReportHtml.Badge(completion) + " · Exit code: " + exit + "</p>"
            + "<p>This is a configuration/readiness report. It contains no application test results.</p></section>"
            + "<section id=\"findings\"><h2>Checks and observations</h2><ul>" + items + "</ul></section>"
            + "<section id=\"devices\"><h2>Devices</h2><p>No application interactions were executed by this command.</p></section>"
            + "<section id=\"requirements\"><h2>Requirements</h2><p>Application requirements were not evaluated by this command.</p></section>"
            + "<section id=\"activity\"><h2>Activity</h2><p><a href=\"result.json\">Machine-readable command result</a></p></section></main>" + ReportPage.End;
    }

}
