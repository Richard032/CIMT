using System.Net;
using System.Text.Json;
using System.Text.RegularExpressions;

namespace Cimt;

public static class RunEngine
{
    static readonly JsonSerializerOptions JsonOptions = new() { WriteIndented = true };

    public static async Task<int> Execute(Configuration config, string report, DateTimeOffset started)
    {
        var deadline = started.AddMinutes(double.Parse(config.Root.Get("execution")!.Value("time-limit-minutes")!, System.Globalization.CultureInfo.InvariantCulture));
        var stages = new List<object>();
        var builds = new List<Dictionary<string, string>>();
        var errors = new List<string>();
        var work = "";
        var commit = "";
        var uiExit = 2;
        var exit = 0;
        var nativeModule = Path.Combine(Configuration.InstallationRoot, "tools/node-packages/lib/node_modules/@mobilenext/mobile-mcp/lib/mobilecli.js");
        var runtime = Path.Combine(Configuration.InstallationRoot, "lib/cimt-runtime/run_ui.py");
        var python = Path.Combine(Configuration.InstallationRoot, "tools/python/bin/python");
        var env = new Dictionary<string, string> { ["GIT_TERMINAL_PROMPT"] = "0", ["GCM_INTERACTIVE"] = "never" };
        var devices = new List<Dictionary<string, string>>();

        int Remaining(int maximum)
        {
            var seconds = (int)(deadline - DateTimeOffset.UtcNow).TotalSeconds;
            if (seconds <= 0) throw new RunLimitException("Whole-run time limit reached");
            return Math.Min(maximum, seconds);
        }
        async Task<ProcessRunner.Result> Invoke(string tool, IEnumerable<string> arguments, int maximum = 120, string? input = null)
        {
            try { return await ProcessRunner.Run(tool, arguments, Remaining(maximum), env, input: input); }
            catch (ConfigurationException) when (DateTimeOffset.UtcNow >= deadline)
            { throw new RunLimitException("Whole-run time limit reached"); }
        }
        void Progress(string stage)
        {
            Console.WriteLine(stage);
            File.WriteAllText(Path.Combine(report, "progress.json"), JsonSerializer.Serialize(new { stage, sourceCommit = commit, updated = DateTimeOffset.UtcNow }, JsonOptions));
        }

        try
        {
            if (!File.Exists(runtime) || !File.Exists(python)) throw new ConfigurationException("CIMT support runtime is missing. Install it with scripts/install-cimt-runtime.sh from the source installation.");
            CleanupPreviousOwnedWork();
            work = CreateOwnedWork(config.WorkspaceRoot);
            env["MOBILECLI_HOME"] = Path.Combine(work, "mobilecli");
            var context = new Dictionary<string, object?>
            {
                ["config"] = RuntimeConfig(config.Root), ["report"] = report, ["work"] = work,
                ["deadline"] = deadline.ToUnixTimeMilliseconds() / 1000.0,
                ["nativeHome"] = env["MOBILECLI_HOME"], ["builds"] = builds, ["devices"] = devices
            };
            context["resetDirectories"] = config.Root.Get("reset")?.Map?.ToDictionary(p => p.Key,
                p => Path.GetDirectoryName(p.Value.List![0].Origin)) ?? new();
            var inputs = new Dictionary<string, string>();
            using var http = new HttpClient { Timeout = TimeSpan.FromSeconds(20) };
            foreach (var (name, value) in config.Root.Get("inputs")!.Map!)
            {
                using var timeout = new CancellationTokenSource(TimeSpan.FromSeconds(Remaining(20)));
                var web = Uri.TryCreate(value.Text, UriKind.Absolute, out var uri) && uri.Scheme is "https" or "http";
                if (web && !string.IsNullOrEmpty(uri!.UserInfo)) throw new ConfigurationException("Text input links must be unauthenticated.");
                string text;
                try { text = web ? await http.GetStringAsync(uri!, timeout.Token) : await File.ReadAllTextAsync(value.PathValue, timeout.Token); }
                catch (OperationCanceledException) when (DateTimeOffset.UtcNow >= deadline) { throw new RunLimitException("Whole-run time limit reached"); }
                if (text.Length > 1000000) throw new ConfigurationException("A text input exceeds the supported one-million-character limit.");
                inputs[name] = config.Scrub(text);
            }
            context["inputs"] = inputs;
            await File.WriteAllTextAsync(Path.Combine(report, "inputs.json"), JsonSerializer.Serialize(inputs, JsonOptions));
            Progress("Checking model access and the installed execution runtime");
            var preflight = await Invoke(python, [runtime, "--preflight"], 45, JsonSerializer.Serialize(context));
            if (preflight.Exit != 0) throw new ConfigurationException(config.Scrub(preflight.Stderr.Trim()));
            stages.Add(new { stage = "model/runtime preflight", result = "passed; no inference issued" });

            Progress("Taking the physical-device snapshot");
            var discovered = await Invoke("node", ["-e", "const {Mobilecli}=require(process.argv[1]);const c=new Mobilecli();console.log(JSON.stringify({devices:c.getDevices({type:'real'}),binary:c.getPath()}));", nativeModule], 30);
            if (discovered.Exit != 0) throw new ConfigurationException("Physical-device discovery failed.");
            using (var document = JsonDocument.Parse(discovered.Stdout))
            {
                context["nativeBinary"] = document.RootElement.GetProperty("binary").GetString();
                foreach (var device in document.RootElement.GetProperty("devices").GetProperty("data").GetProperty("devices").EnumerateArray())
                {
                    var platform = device.GetProperty("platform").GetString()!;
                    if (device.GetProperty("state").GetString() != "online" || platform is not ("android" or "ios")) continue;
                    devices.Add(new() { ["platform"] = platform, ["id"] = device.GetProperty("id").GetString()!,
                        ["name"] = device.TryGetProperty("name", out var name) ? name.GetString() ?? platform : platform });
                }
            }
            if (devices.Count == 0) throw new ConfigurationException("No supported physical devices are connected.");
            await File.WriteAllTextAsync(Path.Combine(report, "startup-devices.json"), JsonSerializer.Serialize(devices, JsonOptions));

            var repository = config.Root.Get("repository")!;
            var clone = Path.Combine(work, "repository");
            Progress("Cloning the configured branch");
            var cloned = await Invoke("git", ["clone", "--depth", "1", "--branch", repository.Value("branch")!, "--single-branch", repository.Value("url")!, clone], 180);
            if (cloned.Exit != 0) throw new ConfigurationException("Git clone failed: " + config.Scrub(cloned.Stderr));
            commit = (await Invoke("git", ["-C", clone, "rev-parse", "HEAD"], 15)).Stdout.Trim();
            Progress("Initializing the recorded submodule revisions");
            var modules = await Invoke("git", ["-C", clone, "submodule", "update", "--init", "--recursive", "--depth", "1"], 600);
            if (modules.Exit != 0) throw new ConfigurationException("Submodule initialization failed: " + config.Scrub(modules.Stderr));
            if (!File.Exists(Path.Combine(clone, repository.Value("solution")!.Replace('\\', Path.DirectorySeparatorChar)))) throw new ConfigurationException("Configured solution was not found in the clone.");
            stages.Add(new { stage = "repository", branch = repository.Value("branch"), sourceCommit = commit });

            foreach (var target in config.Root.Get("build")!.Get("targets")!.List!)
            foreach (var platform in new[] { "android", "ios" })
            {
                if (target.Get(platform) is not { } settings || !devices.Any(d => d["platform"] == platform)) continue;
                var name = target.Value("name")!;
                var slug = Regex.Replace(name, "[^A-Za-z0-9_.-]", "_") + "-" + platform + "-" + Guid.NewGuid().ToString("N")[..8];
                var job = Path.Combine(work, slug); Directory.CreateDirectory(job);
                var requestFile = Path.Combine(job, "request.json");
                var resultFile = Path.Combine(job, "result.json");
                var request = new Dictionary<string, object?>
                {
                    ["project"] = target.Value("project"), ["configuration"] = target.Value("configuration"),
                    ["framework"] = settings.Value("framework"), ["properties"] = settings.Get("properties")?.Map?.ToDictionary(p => p.Key, p => p.Value.Text) ?? new(),
                    ["artifact"] = settings.Value("artifact"), ["app-id"] = settings.Value("app-id")
                };
                await File.WriteAllTextAsync(requestFile, JsonSerializer.Serialize(request, JsonOptions));
                if (!OperatingSystem.IsWindows()) File.SetUnixFileMode(requestFile, UnixFileMode.UserRead | UnixFileMode.UserWrite);
                env["CIMT_REPOSITORY_ROOT"] = clone; env["CIMT_BUILD_REQUEST"] = requestFile; env["CIMT_BUILD_RESULT"] = resultFile;
                var script = settings.Get("script")?.PathValue ?? Path.Combine(Configuration.InstallationRoot, "scripts/build/" + platform + ".sh");
                Progress("Building " + name + " for " + platform);
                var built = await Invoke("bash", [script], 1800);
                var logName = slug + ".log";
                await File.WriteAllTextAsync(Path.Combine(report, logName), config.Scrub(built.Stdout + "\n" + built.Stderr));
                if (built.Exit != 0 || !File.Exists(resultFile))
                {
                    errors.Add("Build failed: " + name + " / " + platform + " (exit " + built.Exit + "). See " + logName);
                    stages.Add(new { stage = "build", target = name, platform, result = "error", log = logName });
                    exit = 3; continue;
                }
                var result = JsonSerializer.Deserialize<Dictionary<string, string>>(await File.ReadAllTextAsync(resultFile))!;
                if (!result.TryGetValue("artifact", out var artifact) || !File.Exists(artifact) ||
                    !result.TryGetValue("app-id", out var appId) || !Regex.IsMatch(appId, "^[A-Za-z0-9_.-]+$"))
                    throw new ConfigurationException("A successful build returned invalid artifact metadata.");
                var destination = Path.Combine(report, "artifacts", slug); Directory.CreateDirectory(destination);
                var saved = Path.Combine(destination, Path.GetFileName(artifact)); File.Copy(artifact, saved);
                builds.Add(new() { ["target"] = name, ["platform"] = platform, ["artifact"] = saved, ["app-id"] = appId });
                stages.Add(new { stage = "build", target = name, platform, result = "passed", log = logName });
                // Keep the installed artifact; discard publish intermediates between jobs.
                Directory.Delete(job, true);
            }
            if (builds.Count == 0) throw new ConfigurationException("No installable build was produced; no application interactions were executed.");
            Progress("Executing instructions on startup devices (maximum two at once)");
            context["builds"] = builds;
            var tested = await Invoke(python, [runtime], Math.Max(1, (int)(deadline - DateTimeOffset.UtcNow).TotalSeconds), JsonSerializer.Serialize(context));
            uiExit = tested.Exit is >= 0 and <= 3 ? tested.Exit : 3;
            if (uiExit == 3) errors.Add("Device/AI execution failed (exit " + tested.Exit + "): " + config.Scrub(tested.Stderr));
            exit = Combine(exit, uiExit);
        }
        catch (RunLimitException error) { errors.Add(error.Message); exit = Combine(exit, 2); }
        catch (ConfigurationException error) { errors.Add(config.Scrub(error.Message)); exit = 3; }
        catch (Exception error) { errors.Add("Execution infrastructure failed: " + error.GetType().Name); exit = 3; }
        finally
        {
            if (work.Length > 0)
            {
                try
                {
                    var stopped = await ProcessRunner.Run("node", ["-e", "const {Mobilecli}=require(process.argv[1]);console.log(new Mobilecli().executeCommand(['daemon','stop'],15000));", nativeModule], 20, env);
                    if (stopped.Exit != 0) { errors.Add("The owned native daemon could not be stopped cleanly."); exit = 3; }
                    RemoveOwnedWork(work);
                }
                catch (Exception error) { errors.Add("Owned clone cleanup requires attention: " + error.GetType().Name); exit = 3; }
            }
        }
        if (exit == 0 && uiExit == 2) exit = 2;
        exit = WriteReport(config, report, started, commit, stages, builds, errors, exit);
        Console.WriteLine("CIMT run finished with exit " + exit + ". Report: " + Path.Combine(report, "index.html"));
        return exit;
    }

    static int Combine(int first, int next) => first == 3 || next == 3 ? 3 : first == 1 || next == 1 ? 1 : first == 2 || next == 2 ? 2 : 0;

    static object? RuntimeConfig(Node node, string key = "")
    {
        if (node.Map is not null) return node.Map.ToDictionary(p => p.Key, p => RuntimeConfig(p.Value, p.Key));
        if (node.List is not null)
        {
            if (key is "command" or "verify-command") return node.List.Select((n, i) => i == 0 && n.Text.Contains('/') ? n.PathValue : n.Text).ToArray();
            return node.List.Select(n => RuntimeConfig(n)).ToArray();
        }
        return node.Scalar;
    }

    static string Registry => Path.Combine(Configuration.InstallationRoot, "state/owned-work.json");
    public static string CreateOwnedWork(string root)
    {
        Directory.CreateDirectory(root);
        var path = Path.Combine(root, "work_" + DateTimeOffset.Now.ToString("yyyy-MM-dd_HH-mm-ss-fff") + "_" + Guid.NewGuid().ToString("N")[..8]);
        Directory.CreateDirectory(path);
        if (!OperatingSystem.IsWindows()) File.SetUnixFileMode(path, UnixFileMode.UserRead | UnixFileMode.UserWrite | UnixFileMode.UserExecute);
        var token = Guid.NewGuid().ToString("N");
        File.WriteAllText(Path.Combine(path, ".cimt-owned"), token);
        Directory.CreateDirectory(Path.GetDirectoryName(Registry)!);
        File.WriteAllText(Registry, JsonSerializer.Serialize(new { path, token }));
        return path;
    }

    public static void CleanupPreviousOwnedWork()
    {
        if (!File.Exists(Registry)) return;
        using var registry = JsonDocument.Parse(File.ReadAllText(Registry));
        RemoveOwnedWork(registry.RootElement.GetProperty("path").GetString()!);
    }

    public static void RemoveOwnedWork(string path)
    {
        if (!File.Exists(Registry)) throw new IOException("Missing ownership registry");
        using var registry = JsonDocument.Parse(File.ReadAllText(Registry));
        if (registry.RootElement.GetProperty("path").GetString() != path || !Path.GetFileName(path).StartsWith("work_", StringComparison.Ordinal) ||
            new DirectoryInfo(path).LinkTarget is not null) throw new IOException("Unverified work ownership");
        if (Directory.Exists(path))
        {
            var token = File.ReadAllText(Path.Combine(path, ".cimt-owned"));
            if (token != registry.RootElement.GetProperty("token").GetString()) throw new IOException("Work ownership token mismatch");
            Directory.Delete(path, true);
        }
        File.Delete(Registry);
    }

    static int WriteReport(Configuration config, string report, DateTimeOffset started, string commit, List<object> stages,
        List<Dictionary<string, string>> builds, List<string> errors, int exit)
    {
        JsonElement? ui = null;
        var uiFile = Path.Combine(report, "ui-results.json");
        if (File.Exists(uiFile)) ui = JsonSerializer.Deserialize<JsonElement>(File.ReadAllText(uiFile));
        var hasCrash = false;
        var allComplete = ui.HasValue;
        if (ui is { } results && results.TryGetProperty("devices", out var deviceResults))
            foreach (var device in deviceResults.EnumerateArray())
            {
                if (device.TryGetProperty("stoppingReason", out var stopping) && stopping.ValueKind != JsonValueKind.Null) allComplete = false;
                if (device.TryGetProperty("error", out var error) && error.ValueKind != JsonValueKind.Null) allComplete = false;
                foreach (var scenario in device.GetProperty("scenarios").EnumerateArray())
                {
                    if (scenario.GetProperty("crashes").GetArrayLength() > 0) hasCrash = true;
                    if (scenario.GetProperty("completion").GetString() != "complete") allComplete = false;
                }
            }
        if (hasCrash) exit = Combine(exit, 1);
        if (!ui.HasValue) exit = Combine(exit, 2);
        var value = new { command = "run", sourceBranch = config.Root.Get("repository")!.Value("branch"), sourceCommit = commit,
            started, finished = DateTimeOffset.UtcNow, exitCode = exit, verdict = hasCrash || exit == 1 ? "failed" : exit == 0 ? "passed" : "inconclusive",
            completion = (exit is 0 or 1) && allComplete ? "complete" : "incomplete", stages, builds, errors, execution = ui };
        File.WriteAllText(Path.Combine(report, "result.json"), config.Scrub(JsonSerializer.Serialize(value, JsonOptions)));
        string Safe(string s) => WebUtility.HtmlEncode(config.Scrub(s));
        var body = "<!doctype html><html lang=\"en\"><meta charset=\"utf-8\"><title>CIMT application test</title><style>body{font:16px system-ui;max-width:1150px;margin:2rem auto;padding:1rem;color:#172333}img{max-width:280px;max-height:520px}pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#f1f4f8;padding:1rem}li{margin:.7rem 0}</style>";
        body += "<h1>CIMT application test</h1><p>Exit: " + exit + " · Verdict: " + Safe(value.verdict) + " · Completion: " + Safe(value.completion) + "</p>";
        body += "<p>Branch: " + Safe(value.sourceBranch!) + " · Commit: " + Safe(commit) + "</p><h2>Stopping reasons and coverage limits</h2><ul>";
        body += string.Join("", errors.Select(e => "<li>" + Safe(e) + "</li>")) + "</ul><p>Only recorded target/device/control paths were exercised. This report does not prove coverage of every possible application state.</p>";
        bool Detail(string section) => config.Root.Get("reports")?.Get("sections")?.List is not { } sections || sections.Any(s => s.Text == section);
        string Field(JsonElement item, string key, string fallback = "") => item.ValueKind == JsonValueKind.Object && item.TryGetProperty(key, out var field) ? field.ToString() : fallback;
        body += "<h2>Build stages</h2><ul>";
        foreach (var stage in stages)
        {
            var item = JsonSerializer.SerializeToElement(stage);
            body += "<li>" + Safe(Field(item, "stage") + " " + Field(item, "target") + " " + Field(item, "platform") + ": " + Field(item, "result"));
            if (Detail("diagnostics") && item.TryGetProperty("log", out var log)) body += " — <a href=\"" + Safe(log.GetString()!) + "\">build log</a>";
            body += "</li>";
        }
        body += "</ul>";
        if (Detail("requirements") && File.Exists(Path.Combine(report, "inputs.json")))
            body += "<details><summary>Testing instructions and requirements</summary><pre>" + Safe(File.ReadAllText(Path.Combine(report, "inputs.json"))) + "</pre></details>";
        if (ui is { } execution)
        {
            body += "<h2>Device scenarios and coverage</h2>";
            foreach (var device in execution.GetProperty("devices").EnumerateArray())
            {
                var identity = device.GetProperty("device");
                body += "<h3>" + Safe(Field(identity, "name", Field(identity, "platform"))) + "</h3>";
                foreach (var reason in new[] { "error", "stoppingReason" })
                    if (device.TryGetProperty(reason, out var stopping) && stopping.ValueKind != JsonValueKind.Null)
                        body += "<p>" + Safe(stopping.ToString()) + "</p>";
                foreach (var scenario in device.GetProperty("scenarios").EnumerateArray())
                {
                    body += "<h4>" + Safe(Field(scenario, "target")) + " — " + Safe(Field(scenario, "verdict", "inconclusive")) + " / " + Safe(Field(scenario, "completion")) + "</h4>";
                    if (scenario.TryGetProperty("coverage", out var coverage))
                        body += "<p>Observed control/state combinations: " + Safe(Field(coverage, "observedControls", "0")) + "; activated: " + Safe(Field(coverage, "attemptedControls", "0")) + "; outstanding: " + Safe(Field(coverage, "outstandingObservedControls", "0")) + ".</p>";
                    if (scenario.TryGetProperty("remaining", out var remaining) && remaining.GetArrayLength() > 0)
                        body += "<p>Remaining/blocked work:</p><pre>" + Safe(remaining.ToString()) + "</pre>";
                    if (scenario.TryGetProperty("crashes", out var crashes) && crashes.GetArrayLength() > 0)
                    {
                        body += "<p>Crash/termination findings: " + crashes.GetArrayLength() + ".</p>";
                        if (Detail("findings")) body += "<details><summary>Findings and reproduction</summary><pre>" + Safe(crashes.ToString()) + "</pre></details>";
                    }
                    if (Detail("interpretations") && scenario.TryGetProperty("interpretation", out var interpretation)) body += "<p>Interpretation: " + Safe(interpretation.ToString()) + "</p>";
                    if (Detail("scenarios"))
                    {
                        body += "<details open><summary>Steps and observed behaviour</summary><ol>";
                        foreach (var step in scenario.GetProperty("steps").EnumerateArray())
                        {
                            var action = step.TryGetProperty("action", out var actionValue) ? actionValue.ValueKind == JsonValueKind.Object ? Field(actionValue, "action") : actionValue.ToString() : "check";
                            body += "<li><p>" + Safe(action + ": " + Field(step, "observation")) + "</p>";
                            foreach (var key in new[] { "actionError", "crash", "recovery", "navigation" }) if (step.TryGetProperty(key, out var note)) body += "<p>" + Safe(note.ToString()) + "</p>";
                            if (step.TryGetProperty("screenshot", out var screenshot)) body += "<a href=\"" + Safe(screenshot.ToString()) + "\"><img loading=\"lazy\" src=\"" + Safe(screenshot.ToString()) + "\" alt=\"Step evidence\"></a>";
                            body += "</li>";
                        }
                        body += "</ol></details>";
                    }
                }
            }
            if (execution.TryGetProperty("budget", out var budget)) body += "<h2>AI budget accounting</h2><pre>" + Safe(budget.ToString()) + "</pre>";
            if (Detail("diagnostics")) body += "<details><summary>Execution data</summary><pre>" + Safe(JsonSerializer.Serialize(execution, JsonOptions)) + "</pre></details>";
        }
        else body += "<p>No application UI interaction result was produced.</p>";
        body += "<p><a href=\"result.json\">Machine-readable run result</a></p>";
        File.WriteAllText(Path.Combine(report, "index.html"), config.Scrub(body + "</html>"));
        return exit;
    }
}

public sealed class RunLimitException(string message) : Exception(message);
