using System.Diagnostics;
using System.Text.Json;
using Cimt;
using System.Runtime.Versioning;
[assembly: SupportedOSPlatform("macos")]

if(args.Contains("--lock-probe"))
{
    try{using var held=new MachineLock();return 1;}catch(ConfigurationException){return 0;}
}
var temp=Path.Combine(Path.GetTempPath(),"cimt-checks-"+Guid.NewGuid().ToString("N"));Directory.CreateDirectory(temp);
Environment.SetEnvironmentVariable("CIMT_INSTALL_ROOT",temp);
var passed=0;
void Check(string name,Action action){action();passed++;Console.WriteLine("PASS "+name);}
void Assert(bool condition,string message){if(!condition)throw new Exception(message);}
void Fails(Action action){try{action();}catch(ConfigurationException){return;}throw new Exception("Expected configuration failure");}
var secret="synthetic-test-credential-never-a-real-key";
var text="""
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
string Write(string name,string content){var path=Path.Combine(temp,name);Directory.CreateDirectory(Path.GetDirectoryName(path)!);File.WriteAllText(path,content);File.SetUnixFileMode(path,UnixFileMode.UserRead|UnixFileMode.UserWrite);return path;}
Node Read(string value)=>Node.Read(Write("case-"+Guid.NewGuid().ToString("N")+".yaml",value));
try
{
    var file=Write("default.yaml",text);var root=Node.Read(file);
    Check("valid schema",()=>new Configuration(root).Validate());
    Check("nested override retains defaults",()=>{var merged=Node.Merge(root,Read("ai-model: {name: another-model}"));Assert(merged.Get("ai-model")!.Value("api-key")==secret,"key lost");Assert(merged.Get("ai-model")!.Value("name")=="another-model","override ignored");});
    Check("lists replace rather than append",()=>{var merged=Node.Merge(root,Read("build: {targets: [{name: only, configuration: Release, project: App.csproj, android: {framework: net10.0-android}}]}"));Assert(merged.Get("build")!.Get("targets")!.List!.Count==1,"lists appended");new Configuration(merged).Validate();});
    Check("inherited path keeps declaring file",()=>{var nested=Node.Read(Write("nested/run.yaml","execution: {time-limit-minutes: 2}"));var merged=Node.Merge(root,nested);Assert(merged.Get("inputs")!.Get("instructions")!.PathValue==Path.Combine(temp,"instructions.txt"),"path rebound to override file");});
    Check("unknown keys rejected",()=>Fails(()=>new Configuration(Node.Merge(root,Read("execution: {unlimited: true}"))).Validate()));
    Check("region masking rejected",()=>Fails(()=>new Configuration(Node.Merge(root,Read("masking: {rules: [{region: {x: 1}}]}"))).Validate()));
    Check("zero budget rejected",()=>Fails(()=>new Configuration(Node.Merge(root,Read("ai-budget: {amount: 0}"))).Validate()));
    Check("missing explicit time limit rejected",()=>Fails(()=>new Configuration(Read(text.Replace("execution: {time-limit-minutes: 5}",""))).Validate()));
    Check("repository traversal rejected",()=>Fails(()=>new Configuration(Node.Merge(root,Read("repository: {solution: ../outside.sln}"))).Validate()));
    Check("credential-bearing HTTPS URL rejected",()=>Fails(()=>new Configuration(Node.Merge(root,Read("repository: {url: 'https://user:password@example.invalid/app.git'}"))).Validate()));
    Check("secret snapshots redact values",()=>{var withSigning=Node.Merge(root,Read("build: {targets: [{name: signed, configuration: Release, project: App.csproj, android: {framework: net10.0-android, properties: {AndroidSigningStorePass: synthetic-store-secret, CodesignKey: synthetic-signing-key}}}]}"));var c=new Configuration(withSigning);c.Validate();var snapshot=JsonSerializer.Serialize(c.Sanitized(withSigning));Assert(!snapshot.Contains(secret)&&!snapshot.Contains("synthetic-store-secret")&&!snapshot.Contains("synthetic-signing-key"),"secret leaked");Assert(!c.Scrub("error "+secret).Contains(secret),"diagnostic secret leaked");});
    Check("secret file permissions enforced",()=>{File.SetUnixFileMode(file,UnixFileMode.UserRead|UnixFileMode.UserWrite|UnixFileMode.OtherRead);try{Fails(()=>new Configuration(Node.Read(file)).Validate());}finally{File.SetUnixFileMode(file,UnixFileMode.UserRead|UnixFileMode.UserWrite);}});
    Check("shared root permits separate work/report run folders",()=>new Configuration(Node.Merge(root,Read("reports: {root: ./work}"))).Validate());
    Check("machine lock excludes another process and releases",()=>
    {
        int Probe(){var info=new ProcessStartInfo("dotnet"){UseShellExecute=false};
            info.ArgumentList.Add(System.Reflection.Assembly.GetExecutingAssembly().Location);info.ArgumentList.Add("--lock-probe");using var child=Process.Start(info)!;child.WaitForExit();return child.ExitCode;}
        using(var held=new MachineLock()){Assert(Probe()==0,"second process entered lock");}
        Assert(Probe()==1,"lock not released");
    });
    Check("unimplemented run cannot report a pass",()=>{var code=Entry.Run(["run","--config",file]).GetAwaiter().GetResult();Assert(code==3,"unimplemented run passed");var reports=Directory.GetFiles(Path.Combine(temp,"reports"),"index.html",SearchOption.AllDirectories);Assert(reports.Length>0,"missing HTML report");Assert(reports.All(p=>!File.ReadAllText(p).Contains(secret)),"report leaked secret");});
    Console.WriteLine($"{passed} checks passed.");return 0;
}
finally{Directory.Delete(temp,true);}
