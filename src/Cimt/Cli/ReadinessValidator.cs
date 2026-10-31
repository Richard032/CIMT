using System.Text.Json;

namespace Cimt;

public interface IReadinessValidator
{
    Task Validate(Configuration configuration, List<string> messages);
}

/// <summary>Checks prerequisites without building or operating the app.</summary>
public sealed class ReadinessValidator(ICommandRunner processes, ITextInputReader inputs) : IReadinessValidator
{
    /// <summary>Check inputs, scripts, tools, Git access, and device presence without testing the app.</summary>
    public async Task Validate(Configuration configuration, List<string> messages)
    {
        await CheckInputs(configuration.Root, messages);
        CheckScripts(configuration.Root);
        await CheckGit(configuration.Root, messages);
        await CheckTools(messages);
        await CheckDevices(configuration, messages);
    }

    private async Task CheckInputs(Node root, List<string> messages)
    {
        foreach (var (name, source) in root.Get("inputs")!.Map!)
        {
            using var timeout = new CancellationTokenSource(TimeSpan.FromSeconds(20));
            _ = await inputs.Read(source, timeout.Token);
            messages.Add(name + " text input is readable.");
        }
    }

    private static void CheckScripts(Node root)
    {
        foreach (var target in root.Get("build")!.Get("targets")!.List!)
            foreach (var platform in new[] { "android", "ios" })
                if (target.Get(platform)?.Get("script") is { } script && !File.Exists(script.PathValue))
                    throw new ConfigurationException("A replacement build script does not exist.");
        foreach (var key in new[] { "command", "verify-command" })
            CheckResetScript(root.Get("reset")?.Get(key));
    }

    private static void CheckResetScript(Node? node)
    {
        if (node?.List is not { Count: > 0 } command)
            return;
        if (command[0].Text.Contains('/') && !File.Exists(command[0].PathValue))
            throw new ConfigurationException("A reset script does not exist.");
    }

    private async Task CheckGit(Node root, List<string> messages)
    {
        var repository = root.Get("repository")!;
        var result = await processes.Run(new("git", ["ls-remote", "--exit-code", repository.Value("url")!,
            "refs/heads/" + repository.Value("branch")!], 20,
            new()
            {
                ["GIT_TERMINAL_PROMPT"] = "0",
                ["GCM_INTERACTIVE"] = "never"
            }));
        if (result.Exit != 0)
            throw new ConfigurationException("Noninteractive Git access or branch validation failed.");
        messages.Add("Configured Git branch is accessible without prompting.");
    }

    private async Task CheckTools(List<string> messages)
    {
        foreach (var tool in new[] { "dotnet", "java", "adb", "xcodebuild" })
        {
            var flag = tool switch
            {
                "java" => "-version",
                "adb" => "version",
                "xcodebuild" => "-version",
                _ => "--version"
            };
            var result = await processes.Run(new(tool, [flag], 15));
            if (result.Exit != 0)
                throw new ConfigurationException("Required tool check failed: " + tool);
            messages.Add(tool + " is available.");
        }
    }

    private async Task CheckDevices(Configuration configuration, List<string> messages)
    {
        var selection = new DeviceSelection(configuration.Root.Get("execution"));
        var module = new RuntimePaths(Configuration.InstallationRoot).NativeModule;
        var snapshot = await processes.Run(new("node", DeviceInventory.Arguments(module, selection), 60));
        if (snapshot.Exit != 0)
            throw new ConfigurationException("Device discovery failed: " + configuration.Scrub(snapshot.Stderr.Trim()));
        using var document = JsonDocument.Parse(snapshot.Stdout);
        var devices = DeviceInventory.Read(document.RootElement, selection);
        selection.Verify(devices);
        foreach (var target in configuration.Root.Get("build")!.Get("targets")!.List!)
            foreach (var platform in new[] { "android", "ios" })
                if (target.Get(platform) is { } settings)
                    selection.ValidateBuild(platform, settings);
        messages.Add($"Startup {selection.Kind} device snapshot: {devices.Count} selected device(s). App build and control still require a real test.");
    }
}
