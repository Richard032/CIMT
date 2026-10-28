using System.Text.Json;

namespace Cimt;

public interface ITextInputReader
{
    Task<string> Read(Node source, CancellationToken cancellation);
}

/// <summary>Reads an unauthenticated web page or a local text file.</summary>
public sealed class TextInputReader(HttpClient http) : ITextInputReader
{
    public async Task<string> Read(Node source, CancellationToken cancellation)
    {
        if (!Uri.TryCreate(source.Text, UriKind.Absolute, out var uri) || uri.Scheme is not ("https" or "http"))
            return await File.ReadAllTextAsync(source.PathValue, cancellation);
        if (!string.IsNullOrEmpty(uri.UserInfo))
            throw new ConfigurationException("Text input links must be unauthenticated.");
        return await http.GetStringAsync(uri, cancellation);
    }
}

/// <summary>Loads and redacts the text supplied to this run.</summary>
public sealed class TextInputLoader(ITextInputReader reader) : IRunStep
{
    public async Task Execute(RunState state)
    {
        foreach (var (name, source) in state.Configuration.Root.Get("inputs")!.Map!)
            state.Inputs[name] = await ReadInput(state, source);
        state.Requirements = RequirementCatalogue.Read(state.Inputs.GetValueOrDefault("requirements", ""));
        await File.WriteAllTextAsync(Path.Combine(state.Report, "requirements.json"),
            JsonSerializer.Serialize(new
            {
                sourceSha256 = RequirementCatalogue.Hash(state.Inputs.GetValueOrDefault("requirements", "")),
                items = state.Requirements
            }, new JsonSerializerOptions { WriteIndented = true }));
        await File.WriteAllTextAsync(Path.Combine(state.Report, "inputs.json"),
            JsonSerializer.Serialize(state.Inputs, new JsonSerializerOptions { WriteIndented = true }));
    }

    private async Task<string> ReadInput(RunState state, Node source)
    {
        using var timeout = new CancellationTokenSource(TimeSpan.FromSeconds(state.Deadline.RemainingSeconds(20)));
        try
        {
            var text = await reader.Read(source, timeout.Token);
            if (text.Length > 1000000)
                throw new ConfigurationException("A text input exceeds the supported one-million-character limit.");
            return state.Configuration.Scrub(text);
        }
        catch (OperationCanceledException) when (state.Deadline.HasExpired)
        {
            throw new RunLimitException("Whole-run time limit reached");
        }
    }
}
