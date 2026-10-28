using System.Diagnostics;
using System.Text.Json;
using Cimt;
using System.Runtime.Versioning;

namespace Cimt.Checks;

/// <summary>Regression cases for configuration, process locking, and the public command.</summary>
[SupportedOSPlatform("macos")]
internal sealed class FoundationChecks(string temp)
{
    private int passed;
    private readonly WorkDirectoryManager folders = new(Path.Combine(temp, "state/owned-work.json"));
    private const string secret = "synthetic-test-credential-never-a-real-key";
    private Node root = null!;
    private string file = "";
    private const string text = """
workspace: {root: ./work}
reports: {root: ./reports}
repository: {url: 'https://example.invalid/app.git', branch: main, solution: App.sln}
execution: {time-limit-minutes: 5}
ai-model: {name: configuration-only-test, api-key: synthetic-test-credential-never-a-real-key}
ai-budget: {amount: 1, currency: USD}
inputs: {instructions: ./instructions.txt}
build:
  targets:
    - {name: first, configuration: Release, project: App.csproj, android: {framework: net10.0-android}}
    - {name: second, configuration: Release, project: App.csproj, ios: {framework: net10.0-ios}}
""";

    public int Run()
    {
        file = Write("default.yaml", text);
        root = Node.Read(file);
        Check("valid schema", ValidSchema);
        Check("nested override retains defaults", NestedOverrideKeepsDefaults);
        Check("lists replace rather than append", ListsReplace);
        Check("inherited path keeps declaring file", PathsKeepTheirOrigin);
        Check("unknown keys rejected", UnknownKeysFail);
        Check("region masking rejected", RegionMaskingFails);
        Check("zero budget rejected", ZeroBudgetFails);
        Check("missing explicit time limit rejected", MissingTimeLimitFails);
        Check("repository traversal rejected", RepositoryTraversalFails);
        Check("credential-bearing HTTPS URL rejected", HttpsCredentialsFail);
        Check("secret snapshots redact values", SecretsAreRedacted);
        Check("secret file permissions enforced", SecretPermissionsAreRequired);
        Check("shared root permits separate work/report run folders", WorkAndReportsCanShareARoot);
        Check("machine lock excludes another process and releases", MachineLockIsExclusive);
        Check("missing runtime cannot report an application pass", MissingRuntimeCannotPass);
        Check("interrupted cleanup removes only owned work", InterruptedWorkIsRemoved);
        Check("cleanup rejects a changed ownership token", ChangedOwnershipIsRejected);
        Check("public run continues after build failure and cleans its clone", PublicRunPreservesBuildFailure);
        Console.WriteLine($"{passed} checks passed.");
        return 0;
    }

    private void Check(string name, Action action)
    {
        action();
        passed++;
        Console.WriteLine("PASS " + name);
    }

    private static void Assert(bool condition, string message)
    {
        if (!condition)
            throw new Exception(message);
    }

    private static void Fails(Action action)
    {
        try
        {
            action();
        }
        catch (ConfigurationException) { return; }
        throw new Exception("Expected configuration failure");
    }

    private string Write(string name, string content)
    {
        var path = Path.Combine(temp, name);
        Directory.CreateDirectory(Path.GetDirectoryName(path)!);
        File.WriteAllText(path, content);
        File.SetUnixFileMode(path, UnixFileMode.UserRead | UnixFileMode.UserWrite);
        return path;
    }
    private Node Read(string value) => Node.Read(Write("case-" + Guid.NewGuid().ToString("N") + ".yaml", value));

    private void ValidSchema()
    {
        new Configuration(root).Validate();
    }

    private void NestedOverrideKeepsDefaults()
    {
        var merged = Node.Merge(root, Read("ai-model: {name: another-model}"));
        Assert(merged.Get("ai-model")!.Value("api-key") == secret, "key lost");
        Assert(merged.Get("ai-model")!.Value("name") == "another-model", "override ignored");
    }

    private void ListsReplace()
    {
        var merged = Node.Merge(root, Read("build: {targets: [{name: only, configuration: Release, project: App.csproj, android: {framework: net10.0-android}}]}"));
        Assert(merged.Get("build")!.Get("targets")!.List!.Count == 1, "lists appended");
        new Configuration(merged).Validate();
    }

    private void PathsKeepTheirOrigin()
    {
        var nested = Node.Read(Write("nested/run.yaml", "execution: {time-limit-minutes: 2}"));
        var merged = Node.Merge(root, nested);
        Assert(merged.Get("inputs")!.Get("instructions")!.PathValue == Path.Combine(temp, "instructions.txt"), "path rebound to override file");
    }

    private void UnknownKeysFail()
    {
        Fails(() => new Configuration(Node.Merge(root, Read("execution: {unlimited: true}"))).Validate());
    }

    private void RegionMaskingFails()
    {
        Fails(() => new Configuration(Node.Merge(root, Read("masking: {rules: [{region: {x: 1}}]}"))).Validate());
    }

    private void ZeroBudgetFails()
    {
        Fails(() => new Configuration(Node.Merge(root, Read("ai-budget: {amount: 0}"))).Validate());
    }

    private void MissingTimeLimitFails()
    {
        Fails(() => new Configuration(Read(text.Replace("execution: {time-limit-minutes: 5}", ""))).Validate());
    }

    private void RepositoryTraversalFails()
    {
        Fails(() => new Configuration(Node.Merge(root, Read("repository: {solution: ../outside.sln}"))).Validate());
    }

    private void HttpsCredentialsFail()
    {
        Fails(() => new Configuration(Node.Merge(root, Read("repository: {url: 'https://user:password@example.invalid/app.git'}"))).Validate());
    }

    private void SecretsAreRedacted()
    {
        var withSigning = Node.Merge(root, Read("build: {targets: [{name: signed, configuration: Release, project: App.csproj, android: {framework: net10.0-android, properties: {AndroidSigningStorePass: synthetic-store-secret, CodesignKey: synthetic-signing-key}}}]}"));
        var c = new Configuration(withSigning);
        c.Validate();
        var snapshot = JsonSerializer.Serialize(c.Sanitized(withSigning));
        Assert(!snapshot.Contains(secret) && !snapshot.Contains("synthetic-store-secret") && !snapshot.Contains("synthetic-signing-key"), "secret leaked");
        Assert(!c.Scrub("error " + secret).Contains(secret), "diagnostic secret leaked");
    }

    private void SecretPermissionsAreRequired()
    {
        File.SetUnixFileMode(file, UnixFileMode.UserRead | UnixFileMode.UserWrite | UnixFileMode.OtherRead);
        try
        {
            Fails(() => new Configuration(Node.Read(file)).Validate());
        }
        finally { File.SetUnixFileMode(file, UnixFileMode.UserRead | UnixFileMode.UserWrite); }
    }

    private void WorkAndReportsCanShareARoot()
    {
        new Configuration(Node.Merge(root, Read("reports: {root: ./work}"))).Validate();
    }

    private void MachineLockIsExclusive()
    {
        int Probe()
        {
            var info = new ProcessStartInfo("dotnet") { UseShellExecute = false };
            info.ArgumentList.Add(System.Reflection.Assembly.GetExecutingAssembly().Location);
            info.ArgumentList.Add("--lock-probe");
            using var child = Process.Start(info)!;
            child.WaitForExit();
            return child.ExitCode;
        }
        using (var held = new MachineLock())
        {
            Assert(Probe() == 0, "second process entered lock");
        }
        Assert(Probe() == 1, "lock not released");
    }

    private void MissingRuntimeCannotPass()
    {
        var code = Entry.Run(["run", "--config", file]).GetAwaiter().GetResult();
        Assert(code == 3, "missing runtime passed");
        var reports = Directory.GetFiles(Path.Combine(temp, "reports"), "index.html", SearchOption.AllDirectories);
        Assert(reports.Length > 0, "missing HTML report");
        Assert(reports.All(p => !File.ReadAllText(p).Contains(secret)), "report leaked secret");
    }

    private void InterruptedWorkIsRemoved()
    {
        var unrelated = Path.Combine(temp, "keep");
        Directory.CreateDirectory(unrelated);
        File.WriteAllText(Path.Combine(unrelated, "keep.txt"), "keep");
        var owned = folders.Create(Path.Combine(temp, "work"));
        Directory.CreateDirectory(Path.Combine(owned, "repository"));
        File.WriteAllText(Path.Combine(owned, "repository", "App.csproj"), "fixture");
        folders.CleanupPrevious();
        Assert(!Directory.Exists(owned), "owned clone remained");
        Assert(File.Exists(Path.Combine(unrelated, "keep.txt")), "unrelated work removed");
    }

    private void ChangedOwnershipIsRejected()
    {
        var owned = folders.Create(Path.Combine(temp, "work"));
        var marker = Path.Combine(owned, ".cimt-owned");
        var token = File.ReadAllText(marker);
        File.WriteAllText(marker, "changed");
        try
        {
            folders.Remove(owned);
            throw new Exception("foreign work removed");
        }
        catch (IOException) { }
        Assert(Directory.Exists(owned), "unsafe cleanup");
        File.WriteAllText(marker, token);
        folders.Remove(owned);
    }

    private void PublicRunPreservesBuildFailure()
    {
        var existing = Directory.Exists(Path.Combine(temp, "reports")) ? Directory.GetDirectories(Path.Combine(temp, "reports")).ToHashSet() : [];
        var build = InstallFakeTools();
        var fixture = CreatePublicConfiguration(build);
        RunWithFakeTools(fixture);
        VerifyPublicRun(existing);
    }

    private string InstallFakeTools()
    {
        Write("instructions.txt", "Explore buttons; fixture only.");
        Write("lib/cimt-runtime/run_ui.py", "fixture worker selected by test executable");
        InstallFakePython();
        InstallFakeNode();
        InstallFakeGit();
        return InstallFakeBuilder();
    }

    private string CreatePublicConfiguration(string build)
    {
        var extra = Read("build: {targets: [{name: fail, configuration: Failed, project: App.csproj, android: {framework: net10.0-android, script: '" + build + "'}}, {name: ok, configuration: Release, project: App.csproj, android: {framework: net10.0-android, script: '" + build + "'}}]}");
        var merged = Node.Merge(root, extra);
        // Write the merged fixture as JSON, which is a YAML subset.
        object? Value(Node n) => n.Map is not null ? n.Map.ToDictionary(p => p.Key, p => Value(p.Value)) : n.List is not null ? n.List.Select(Value).ToArray() : n.Scalar;
        return Write("fixture-run.yaml", JsonSerializer.Serialize(Value(merged)));
    }

    private void RunWithFakeTools(string fixture)
    {
        var prior = Environment.GetEnvironmentVariable("PATH");
        try
        {
            Environment.SetEnvironmentVariable("PATH", Path.Combine(temp, "fakebin") + Path.PathSeparator + prior);
            Assert(Entry.Run(["run", "--config", fixture]).GetAwaiter().GetResult() == 3, "build failure did not dominate outcome");
        }
        finally { Environment.SetEnvironmentVariable("PATH", prior); }
    }

    private void VerifyPublicRun(HashSet<string> existing)
    {
        var created = Directory.GetDirectories(Path.Combine(temp, "reports")).Single(p => !existing.Contains(p));
        using var result = JsonDocument.Parse(File.ReadAllText(Path.Combine(created, "result.json")));
        var stages = result.RootElement.GetProperty("stages").EnumerateArray().Where(e => e.GetProperty("stage").GetString() == "build").ToArray();
        Assert(stages.Length == 2 && stages[0].GetProperty("result").GetString() == "error" && stages[1].GetProperty("result").GetString() == "passed", "other target did not continue");
        Assert(!Directory.EnumerateDirectories(Path.Combine(temp, "work"), "work_*").Any(), "run clone remained");
        Assert(!File.ReadAllText(Path.Combine(created, "index.html")).Contains(secret), "secret appeared in application report");
    }

    private string WriteExecutable(string name, string content)
    {
        var path = Write(name, content);
        File.SetUnixFileMode(path, UnixFileMode.UserRead | UnixFileMode.UserWrite | UnixFileMode.UserExecute);
        return path;
    }

    private string InstallFakePython() => WriteExecutable("tools/python/bin/python", """
#!/usr/bin/env python3
import sys,json,pathlib
c=json.load(sys.stdin)
if '--preflight' not in sys.argv:
 d={'devices':[{'index':1,'device':{'platform':'android'},'error':None,'stoppingReason':None,'scenarios':[{'target':'ok','completion':'complete','crashes':[],'steps':[]}]}]}
 pathlib.Path(c['report'],'ui-results.json').write_text(json.dumps(d))
print('Simulated runtime interface; no API or device actions.')
""");

    private string InstallFakeNode() => WriteExecutable("fakebin/node", """
#!/usr/bin/env python3
import sys,json
if any('daemon' in a for a in sys.argv): print('{}')
else: print(json.dumps({'devices':{'data':{'devices':[{'id':'fixture-device','platform':'android','state':'online'}]}},'binary':'fixture-native'}))
""");

    private string InstallFakeGit() => WriteExecutable("fakebin/git", """
#!/usr/bin/env python3
import sys,pathlib
a=sys.argv[1:]
if a[0]=='clone':
 p=pathlib.Path(a[-1]);p.mkdir();(p/'App.sln').write_text('fixture');(p/'App.csproj').write_text('<Project />')
elif 'rev-parse' in a: print('a'*40)
elif 'submodule' not in a: sys.exit(4)
""");

    private string InstallFakeBuilder() => WriteExecutable("fixture-build", """
#!/bin/bash
python3 - <<'PY'
import json,os,pathlib,sys
r=json.loads(pathlib.Path(os.environ['CIMT_BUILD_REQUEST']).read_text())
if r['configuration']=='Failed':sys.exit(42)
p=pathlib.Path(os.environ['CIMT_BUILD_RESULT']);a=p.parent/'fixture.apk';a.write_bytes(b'fixture only')
p.write_text(json.dumps({'artifact':str(a),'app-id':'com.example.fixture'}))
PY
""");
}
