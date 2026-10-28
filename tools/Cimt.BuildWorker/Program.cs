using System.Diagnostics;
using System.Text.Json;
using System.Text.RegularExpressions;

var secrets=new List<string>();
string Scrub(string value){foreach(var s in secrets.Where(x=>x.Length>0).OrderByDescending(x=>x.Length))value=value.Replace(s,"<redacted>",StringComparison.Ordinal);return value;}
try
{
    if(args.Length!=1 || args[0] is not ("android" or "ios"))throw new Exception("Build platform must be android or ios.");
    string Env(string name)=>Environment.GetEnvironmentVariable(name) is {Length:>0} value?value:throw new Exception(name+" is required.");
    var root=Path.GetFullPath(Env("CIMT_REPOSITORY_ROOT"));var resultFile=Path.GetFullPath(Env("CIMT_BUILD_RESULT"));
    if(File.Exists(resultFile))File.Delete(resultFile);
    using var document=JsonDocument.Parse(File.ReadAllText(Env("CIMT_BUILD_REQUEST")));var request=document.RootElement;
    string Value(string name)=>request.TryGetProperty(name,out var n)?n.GetString()??"":"";
    var projectValue=Value("project");
    if(Path.IsPathRooted(projectValue)||projectValue.Replace('\\','/').Split('/').Contains(".."))throw new Exception("Build project must be relative to the repository root.");
    var project=Path.GetFullPath(projectValue.Replace('\\',Path.DirectorySeparatorChar),root);
    if(!File.Exists(project)||!project.EndsWith(".csproj",StringComparison.OrdinalIgnoreCase))throw new Exception("Configured application project does not exist.");
    var configuration=Value("configuration");var framework=Value("framework");
    if(string.IsNullOrWhiteSpace(configuration)||!framework.Contains("-"+args[0],StringComparison.Ordinal))throw new Exception("Build configuration and matching target framework are required.");
    var properties=new Dictionary<string,string>();
    if(request.TryGetProperty("properties",out var props))foreach(var p in props.EnumerateObject())
    {
        if(!Regex.IsMatch(p.Name,"^[A-Za-z_][A-Za-z0-9_]*$"))throw new Exception("Invalid MSBuild property name.");
        properties[p.Name]=p.Value.ValueKind==JsonValueKind.String?p.Value.GetString()!:p.Value.GetRawText();
        if(Regex.IsMatch(p.Name,"pass|secret|token|key",RegexOptions.IgnoreCase))secrets.Add(properties[p.Name]);
    }
    Directory.CreateDirectory(Path.GetDirectoryName(resultFile)!);
    var output=Path.Combine(Path.GetDirectoryName(resultFile)!,"build_"+args[0]+"_"+Guid.NewGuid().ToString("N"));Directory.CreateDirectory(output);
    var common=new List<string>{project,"-c",configuration,"-f",framework};
    if(args[0]=="android")properties["AndroidPackageFormats"]="apk";
    else {properties["RuntimeIdentifier"]="ios-arm64";properties["BuildIpa"]="true";properties["ArchiveOnBuild"]="true";}
    var buildArgs=new List<string>{"publish"};buildArgs.AddRange(common);buildArgs.Add("--output");buildArgs.Add(output);
    buildArgs.AddRange(properties.Select(p=>"-p:"+p.Key+"="+p.Value));
    async Task<(int Exit,string Output)> Run(IEnumerable<string> arguments,bool log)
    {
        var executable=Environment.GetEnvironmentVariable("CIMT_DOTNET_EXECUTABLE")??"dotnet";
        var info=new ProcessStartInfo(executable){UseShellExecute=false,RedirectStandardOutput=true,RedirectStandardError=true,WorkingDirectory=root};
        foreach(var arg in arguments)info.ArgumentList.Add(arg);
        using var process=Process.Start(info)??throw new Exception("Unable to start dotnet.");
        var stdout=process.StandardOutput.ReadToEndAsync();var stderr=process.StandardError.ReadToEndAsync();await process.WaitForExitAsync();
        var a=await stdout;var b=await stderr;if(log){Console.Write(Scrub(a));Console.Error.Write(Scrub(b));}return(process.ExitCode,a);
    }
    Console.WriteLine("Publishing configured "+args[0]+" application target.");
    var built=await Run(buildArgs,true);if(built.Exit!=0)return built.Exit;
    var candidates=Directory.GetFiles(output,args[0]=="android"?"*.apk":"*.ipa",SearchOption.AllDirectories);
    if(args[0]=="android")
    {var signed=candidates.Where(p=>p.EndsWith("-Signed.apk",StringComparison.OrdinalIgnoreCase)).ToArray();if(signed.Length>0)candidates=signed;}
    string? artifact=candidates.Length==1?candidates[0]:null;
    if(artifact is null && Value("artifact") is {Length:>0} fallback){var resolved=Path.GetFullPath(fallback,root);if(File.Exists(resolved))artifact=resolved;}
    if(artifact is null)throw new Exception("Publish did not produce one unambiguous installable artifact; configure artifact fallback or a replacement script.");
    var metadata=new List<string>{"msbuild",project,"-p:Configuration="+configuration,"-p:TargetFramework="+framework,"-getProperty:ApplicationId"};
    metadata.AddRange(properties.Select(p=>"-p:"+p.Key+"="+p.Value));
    var query=await Run(metadata,false);var appId=query.Exit==0?query.Output.Trim():"";
    if(!Regex.IsMatch(appId,"^[A-Za-z0-9_.-]+$"))appId=Value("app-id");
    if(!Regex.IsMatch(appId,"^[A-Za-z0-9_.-]+$"))throw new Exception("Could not resolve app-id from MSBuild or configured fallback.");
    var result=new Dictionary<string,string>{{"artifact",Path.GetFullPath(artifact)},{"app-id",appId}};
    await File.WriteAllTextAsync(resultFile+".partial",JsonSerializer.Serialize(result,new JsonSerializerOptions{WriteIndented=true}));
    File.Move(resultFile+".partial",resultFile,true);Console.WriteLine("Build result written: "+resultFile);return 0;
}
catch(Exception e){Console.Error.WriteLine(Scrub(e.Message));return 3;}
