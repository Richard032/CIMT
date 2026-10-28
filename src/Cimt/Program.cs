using System.Diagnostics;
using System.Net;
using System.Text.Json;
using Cimt;

return await Entry.Run(args);

public static class Entry
{
    public static async Task<int> Run(string[] args)
    {
        if(args.Length==0 || args[0] is "--help" or "help")
        { Console.WriteLine("CIMT — Curtis Intelligent Mobile Test\nCommands: setup, validate, run, replay\nOptions: --config <YAML> [--run-config <YAML>] [--branch <branch>] [--scenario <saved-scenario>]"); return 0; }
        Configuration? config=null;string? report=null;var messages=new List<string>();
        try
        {
            var command=args[0];
            if(!new[]{"setup","validate","run","replay"}.Contains(command))throw new ConfigurationException("Unknown CIMT command.");
            var options=new Dictionary<string,string>();
            for(int i=1;i<args.Length;i+=2)
            { if(!new[]{"--config","--run-config","--branch","--scenario"}.Contains(args[i])||i+1>=args.Length||args[i+1].StartsWith("--")||!options.TryAdd(args[i],args[i+1]))throw new ConfigurationException("Invalid, duplicate, or missing command option."); }
            if(!options.TryGetValue("--config",out var file))throw new ConfigurationException("--config is required.");
            var root=Node.Read(file);
            if(command=="setup")throw new ConfigurationException("YAML-driven setup is not implemented yet; the documented prerequisite bootstrap helper is available.");
            if(options.TryGetValue("--run-config",out var extra))root=Node.Merge(root,Node.Read(extra));
            if(options.TryGetValue("--branch",out var branch))
            {
                var origin=Path.GetFullPath(file);var overrideRoot=new Node(null,new(){["repository"]=new(null,new(){["branch"]=new(branch,null,null,origin)},null,origin)},null,origin);
                root=Node.Merge(root,overrideRoot);
            }
            config=new(root);config.Validate();
            report=NewReport(config.ReportsRoot);
            using var machineLock=new MachineLock();
            await File.WriteAllTextAsync(Path.Combine(report,"effective-config.json"),JsonSerializer.Serialize(config.Sanitized(root),new JsonSerializerOptions{WriteIndented=true}));
            if(command!="validate")throw new ConfigurationException("The "+command+" execution engine is not implemented yet. No application was built, installed, reset, or tested.");
            await ValidateReadiness(config,messages);
            messages.Add("Configuration/readiness checks passed. Model access, signing, login, application behaviour and strict billing enforcement require execution-time validation.");
            await WriteReport(report,"passed","complete",0,messages,config);
            Console.WriteLine("Validation passed. Report: "+Path.Combine(report,"index.html"));return 0;
        }
        catch(Exception e)
        {
            var message=e is ConfigurationException?e.Message:"Configuration or readiness operation failed ("+e.GetType().Name+").";
            messages.Add(config?.Scrub(message)??message);
            try
            {
                report??=NewReport(Path.Combine(Configuration.InstallationRoot,"reports"));
                await WriteReport(report,"inconclusive","incomplete",3,messages,config);
                Console.Error.WriteLine((config?.Scrub(message)??message)+" Report: "+Path.Combine(report,"index.html"));
            }
            catch { Console.Error.WriteLine("CIMT could not write an error report. Check report-folder permissions."); }
            return 3;
        }
    }
    static string NewReport(string root)
    {
        Directory.CreateDirectory(root);
        var stamp=DateTimeOffset.Now.ToString("yyyy-MM-dd_HH-mm-ss-fff");var path=Path.Combine(root,"report_"+stamp);
        for(var i=1;Directory.Exists(path);i++)path=Path.Combine(root,"report_"+stamp+"_"+i);
        Directory.CreateDirectory(path);if(!OperatingSystem.IsWindows())File.SetUnixFileMode(path,UnixFileMode.UserRead|UnixFileMode.UserWrite|UnixFileMode.UserExecute);return path;
    }
    static async Task WriteReport(string folder,string verdict,string completion,int exit,IEnumerable<string> messages,Configuration? config)
    {
        string Safe(string s)=>WebUtility.HtmlEncode(config?.Scrub(s)??s);
        var data=new{commandResult=verdict,completion,exitCode=exit,messages=messages.Select(s=>config?.Scrub(s)??s).ToArray()};
        await File.WriteAllTextAsync(Path.Combine(folder,"result.json"),JsonSerializer.Serialize(data,new JsonSerializerOptions{WriteIndented=true}));
        var html="<!doctype html><html lang=\"en\"><meta charset=\"utf-8\"><title>CIMT report</title><style>body{font:16px system-ui;max-width:1000px;margin:3rem auto;padding:0 1rem;color:#172333}li{margin:.8rem 0}code{background:#eef1f5;padding:.2rem}</style><h1>CIMT report</h1><p>Verdict: <strong>"+Safe(verdict)+"</strong> · Completion: "+Safe(completion)+" · Exit code: "+exit+"</p><h2>Checks and observations</h2><ul>"+string.Join("",messages.Select(s=>"<li>"+Safe(s)+"</li>"))+"</ul><p>This is a configuration/readiness report. It contains no application test results.</p></html>";
        await File.WriteAllTextAsync(Path.Combine(folder,"index.html"),html);
    }
    static async Task ValidateReadiness(Configuration c,List<string> messages)
    {
        var root=c.Root;
        using var http=new HttpClient{Timeout=TimeSpan.FromSeconds(20)};
        foreach(var (key,value) in root.Get("inputs")!.Map!)
        {
            if(Uri.TryCreate(value.Text,UriKind.Absolute,out var uri) && uri.Scheme is "https" or "http")
            {
                if(!string.IsNullOrEmpty(uri.UserInfo))throw new ConfigurationException("Text inputs must not contain authentication credentials.");
                using var response=await http.GetAsync(uri);response.EnsureSuccessStatusCode();
                _=await response.Content.ReadAsStringAsync();
            }
            else { using var stream=File.OpenRead(value.PathValue); }
            messages.Add(key+" text input is readable.");
        }
        foreach(var target in root.Get("build")!.Get("targets")!.List!)
            foreach(var platform in new[]{"android","ios"})
                if(target.Get(platform)?.Get("script") is {} script && !File.Exists(script.PathValue))throw new ConfigurationException("A replacement build script does not exist.");
        foreach(var key in new[]{"command","verify-command"})if(root.Get("reset")?.Get(key)?.List is {Count:>0} cmd)
        {
            var command=cmd[0];if(command.Text.Contains('/')&&!File.Exists(command.PathValue))throw new ConfigurationException("A reset script does not exist.");
        }
        var repo=root.Get("repository")!;
        var git=await ProcessRunner.Run("git",["ls-remote","--exit-code",repo.Value("url")!,"refs/heads/"+repo.Value("branch")!],20,new(){["GIT_TERMINAL_PROMPT"]="0",["GCM_INTERACTIVE"]="never"});
        if(git.Exit!=0)throw new ConfigurationException("Noninteractive Git access or branch validation failed.");
        messages.Add("Configured Git branch is accessible without prompting.");
        foreach(var tool in new[]{"dotnet","java","adb","xcodebuild"})
        {
            var flag=tool=="java"?"-version":tool=="adb"?"version":tool=="xcodebuild"?"-version":"--version";
            var result=await ProcessRunner.Run(tool,[flag],15);
            if(result.Exit!=0)throw new ConfigurationException("Required tool check failed: "+tool);
            messages.Add(tool+" is available.");
        }
        var adb=await ProcessRunner.Run("adb",["devices"],15);
        var android=adb.Stdout.Split('\n').Count(l=>l.TrimEnd().EndsWith("\tdevice",StringComparison.Ordinal));
        var apple=await ProcessRunner.Run("xcrun",["devicectl","list","devices","--timeout","15"],20);
        var ios=apple.Stdout.Split('\n').Count(l=>System.Text.RegularExpressions.Regex.IsMatch(l,@"\sconnected\s"));
        if(android+ios==0)throw new ConfigurationException("No supported physical devices are available.");
        messages.Add($"Startup device snapshot: {android} Android and {ios} Apple device(s). Device signing/control still requires a real test.");
    }
}

public sealed class MachineLock : IDisposable
{
    readonly FileStream stream;
    public MachineLock()
    {
        var root=Path.Combine(Configuration.InstallationRoot,"state");Directory.CreateDirectory(root);
        var path=Path.Combine(root,"run.lock");
        if(new FileInfo(path).LinkTarget is not null)throw new ConfigurationException("CIMT lock path must not be a symbolic link.");
        try{stream=new FileStream(path,FileMode.OpenOrCreate,FileAccess.ReadWrite,FileShare.None);}
        catch(IOException){throw new ConfigurationException("Another CIMT run is active on this Mac.");}
    }
    public void Dispose()=>stream.Dispose();
}

public static class ProcessRunner
{
    public sealed record Result(int Exit,string Stdout,string Stderr);
    public static async Task<Result> Run(string executable,IEnumerable<string> args,int timeout,Dictionary<string,string>? environment=null)
    {
        var info=new ProcessStartInfo(executable){UseShellExecute=false,RedirectStandardOutput=true,RedirectStandardError=true};
        foreach(var arg in args)info.ArgumentList.Add(arg);
        if(environment is not null)foreach(var (k,v) in environment)info.Environment[k]=v;
        using var process=Process.Start(info)??throw new ConfigurationException("Unable to start a required tool.");
        var stdout=process.StandardOutput.ReadToEndAsync();var stderr=process.StandardError.ReadToEndAsync();
        using var cancellation=new CancellationTokenSource(TimeSpan.FromSeconds(timeout));
        try{await process.WaitForExitAsync(cancellation.Token);}catch(OperationCanceledException){process.Kill(true);await process.WaitForExitAsync();throw new ConfigurationException("A readiness check timed out.");}
        return new(process.ExitCode,await stdout,await stderr);
    }
}
