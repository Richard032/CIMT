using System.Net;
using System.Text.Json;

namespace Cimt;

public interface ICommandReports
{
    string Create(string root);
    string ErrorRoot(Configuration? configuration);
    Task SaveConfiguration(CommandSession session);
    Task Write(CommandSession session, string verdict, string completion, int exit);
}

/// <summary>Stores configuration/readiness reports; these are not app test results.</summary>
public sealed class CommandReports : ICommandReports
{
    private static readonly JsonSerializerOptions JsonOptions = new() { WriteIndented = true };

    public string Create(string root)
    {
        Directory.CreateDirectory(root);
        var stamp = DateTimeOffset.Now.ToString("yyyy-MM-dd_HH-mm-ss-fff");
        var path = Path.Combine(root, "report_" + stamp);
        for (var index = 1; Directory.Exists(path); index++)
            path = Path.Combine(root, "report_" + stamp + "_" + index);
        Directory.CreateDirectory(path);
        if (!OperatingSystem.IsWindows())
            File.SetUnixFileMode(path, UnixFileMode.UserRead | UnixFileMode.UserWrite | UnixFileMode.UserExecute);
        return path;
    }

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
            commandResult = verdict,
            completion,
            exitCode = exit,
            messages
        };
        await File.WriteAllTextAsync(Path.Combine(session.Report!, "result.json"), JsonSerializer.Serialize(value, JsonOptions));
        await File.WriteAllTextAsync(Path.Combine(session.Report!, "index.html"), Render(verdict, completion, exit, messages));
    }

    private static string Render(string verdict, string completion, int exit, IEnumerable<string> messages)
    {
        var items = string.Join("", messages.Select(message => "<li>" + WebUtility.HtmlEncode(message) + "</li>"));
        return "<!doctype html><html lang=\"en\"><meta charset=\"utf-8\"><title>CIMT report</title>"
            + "<style>body{font:16px system-ui;max-width:1000px;margin:3rem auto;padding:0 1rem;color:#172333}li{margin:.8rem 0}</style>"
            + "<h1>CIMT report</h1><p>Verdict: <strong>" + WebUtility.HtmlEncode(verdict) + "</strong> · Completion: "
            + WebUtility.HtmlEncode(completion) + " · Exit code: " + exit + "</p><h2>Checks and observations</h2><ul>"
            + items + "</ul><p>This is a configuration/readiness report. It contains no application test results.</p></html>";
    }

    private static string DefaultRoot() => Path.Combine(Configuration.InstallationRoot, "reports");
}
