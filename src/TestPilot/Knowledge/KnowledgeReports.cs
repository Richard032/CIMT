using System.Text.Json;
using static TestPilot.ReportHtml;

namespace TestPilot;

public static class KnowledgeReports
{
    public static async Task<string?> Publish(RunState state, ICommandRunner runner, RuntimePaths paths)
    {
        var folder = Path.GetDirectoryName(paths.Worker)!;
        if (!File.Exists(Path.Combine(folder, "knowledge", "web.py")) || !File.Exists(paths.Python))
            return null;
        try
        {
            var arguments = new List<string> { "-m", "knowledge.web", Configuration.InstallationRoot,
                "--register", state.Identity.Id, state.Report, state.Finished!.Value.UtcDateTime.ToString("O") };
            if (state.Configuration.Learning)
                arguments.AddRange(["--report-url", state.Identity.Id]);
            var result = await runner.Run(new(paths.Python, arguments, 20, WorkingDirectory: folder));
            if (result.Exit == 0)
                return state.Configuration.Learning ? result.Stdout.Trim() : null;
            Console.Error.WriteLine("Could not publish the interactive Knowledge tab. " + state.Configuration.Scrub(result.Stderr.Trim()));
        }
        catch (Exception error) when (error is ConfigurationException or IOException or UnauthorizedAccessException
            or System.ComponentModel.Win32Exception)
        {
            Console.Error.WriteLine("Could not publish the interactive Knowledge tab: " + error.GetType().Name);
        }
        return null;
    }

    public static string Section(RunState state, bool inProgress)
    {
        var body = inProgress ? "Knowledge proposals are reviewed after the run." : "Learning is disabled for this run.";
        var rows = "";
        if (!inProgress && state.Configuration.Learning)
        {
            body = "Knowledge proposals could not be produced. See run activity for details.";
            var path = Path.Combine(state.Report, "knowledge-proposals.json");
            if (File.Exists(path))
            {
                try
                {
                    using var proposal = JsonDocument.Parse(File.ReadAllText(path));
                    body = Field(proposal.RootElement, "message");
                    if (proposal.RootElement.TryGetProperty("requests", out var requests) && requests.ValueKind == JsonValueKind.Array)
                        rows = string.Concat(requests.EnumerateArray().Select(Row));
                }
                catch (Exception error) when (error is IOException or UnauthorizedAccessException or JsonException)
                {
                    body = "The knowledge proposal file could not be read.";
                }
            }
        }
        var table = rows.Length == 0 ? "" : "<table><thead><tr><th>Operation</th><th>What I learned</th>"
            + "<th>Name</th><th>Steps</th></tr></thead><tbody>" + rows + "</tbody></table>";
        var review = inProgress || !state.Configuration.Learning ? "" : "<p>"
            + "<a href=\"http://127.0.0.1:8765/reports/" + Uri.EscapeDataString(state.Identity.Id)
            + "/index.html#knowledge\">Open the interactive report</a> to edit or decide on requests.</p>";
        return "<section id=\"knowledge\"><h2>Knowledge</h2><!--knowledge-review-start--><p>" + Encode(body)
            + "</p>" + table + review + "<!--knowledge-review-end--></section>";
    }

    private static string Row(JsonElement request)
    {
        var steps = request.TryGetProperty("steps", out var values) && values.ValueKind == JsonValueKind.Array
            ? string.Concat(values.EnumerateArray().Select(step => "<li>" + Encode(step.ToString()) + "</li>")) : "";
        return "<tr><td>" + Encode(Field(request, "operation")) + "</td><td>" + Encode(Field(request, "description"))
            + "</td><td>" + Encode(Field(request, "name")) + "</td><td><ol>" + steps + "</ol></td></tr>";
    }
}
