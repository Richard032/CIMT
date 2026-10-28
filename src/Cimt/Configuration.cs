using System.Globalization;
using YamlDotNet.RepresentationModel;

namespace Cimt;

public sealed class ConfigurationException(string message) : Exception(message);

public sealed record Node(string? Scalar, Dictionary<string, Node>? Map, List<Node>? List, string Origin)
{
    public string Text => Scalar ?? throw new ConfigurationException("Expected a scalar configuration value.");
    public Node? Get(string key) => Map?.GetValueOrDefault(key);
    public string? Value(string key) => Get(key)?.Scalar;
    public string PathValue => Path.GetFullPath(Text, Path.GetDirectoryName(Origin)!);
    public static Node Read(string file)
    {
        file = Path.GetFullPath(file);
        try
        {
            var yaml = new YamlStream(); using var reader = File.OpenText(file); yaml.Load(reader);
            if (yaml.Documents.Count != 1) throw new ConfigurationException("Configuration must contain exactly one YAML document.");
            Node Convert(YamlNode n) => n switch
            {
                YamlScalarNode s => new(s.Value ?? "", null, null, file),
                YamlSequenceNode s => new(null, null, s.Children.Select(Convert).ToList(), file),
                YamlMappingNode m => new(null, m.Children.ToDictionary(x => ((YamlScalarNode)x.Key).Value ?? "", x => Convert(x.Value), StringComparer.Ordinal), null, file),
                _ => throw new ConfigurationException("Unsupported YAML structure.")
            };
            var root = Convert(yaml.Documents[0].RootNode);
            if (root.Map is null) throw new ConfigurationException("Configuration root must be a mapping.");
            return root;
        }
        catch (ConfigurationException) { throw; }
        catch (Exception e) when (e is IOException or UnauthorizedAccessException or YamlDotNet.Core.YamlException or ArgumentException or InvalidCastException)
        { throw new ConfigurationException("Cannot read valid YAML configuration: " + Path.GetFileName(file)); }
    }
    public static Node Merge(Node a, Node b)
    {
        if (a.Map is null || b.Map is null) return b;
        var map = new Dictionary<string, Node>(a.Map, StringComparer.Ordinal);
        foreach (var (key, value) in b.Map) map[key] = map.TryGetValue(key, out var previous) ? Merge(previous, value) : value;
        return new(null, map, null, b.Origin);
    }
}

public sealed class Configuration
{
    public Node Root { get; }
    public HashSet<string> Secrets { get; } = new(StringComparer.Ordinal);
    public string ReportsRoot => Root.Get("reports")?.Get("root")?.PathValue ?? Path.Combine(InstallationRoot, "reports");
    public string WorkspaceRoot => Root.Get("workspace")?.Get("root")?.PathValue ?? Path.Combine(InstallationRoot, "work");
    public static string InstallationRoot => Environment.GetEnvironmentVariable("CIMT_INSTALL_ROOT") ?? "/Users/Shared/CIMT";
    public string Scrub(string s) { foreach (var secret in Secrets.OrderByDescending(x => x.Length)) s = s.Replace(secret, "<redacted>", StringComparison.Ordinal); return s; }
    public Configuration(Node root) { Root = root; Collect(root, false); }
    void Collect(Node n, bool secret)
    {
        if (n.Scalar is { Length: > 0 } s && secret) Secrets.Add(s);
        if (n.Map is not null) foreach (var (k,v) in n.Map) Collect(v, secret || k == "credentials" || System.Text.RegularExpressions.Regex.IsMatch(k,"pass|secret|token|key",System.Text.RegularExpressions.RegexOptions.IgnoreCase));
        if (n.List is not null) foreach (var item in n.List) Collect(item, secret);
    }
    public object? Sanitized(Node n) => n.Map is not null ? n.Map.ToDictionary(x => x.Key, x => Sanitized(x.Value)) : n.List is not null ? n.List.Select(Sanitized).ToArray() : Secrets.Contains(n.Scalar ?? "") ? "<redacted>" : n.Scalar;
    static void Keys(Node? n, params string[] allowed)
    {
        if (n is null) return;
        if (n.Map is null) throw new ConfigurationException("Expected a configuration mapping.");
        if (n.Map.Keys.Any(k => !allowed.Contains(k, StringComparer.Ordinal))) throw new ConfigurationException("Unknown configuration key in a mapping.");
    }
    static Node Required(Node n, string key) => n.Get(key) ?? throw new ConfigurationException("Missing required configuration field: " + key);
    static string Text(Node n, string key)
    {
        var s = Required(n,key).Text;
        if (string.IsNullOrWhiteSpace(s) || s.Contains('<') || s.Contains('>')) throw new ConfigurationException("A non-placeholder value is required for: " + key);
        return s;
    }
    static void Positive(Node n, string key)
    {
        if (!decimal.TryParse(Text(n,key), NumberStyles.Number, CultureInfo.InvariantCulture, out var value) || value <= 0)
            throw new ConfigurationException(key + " must be a positive number.");
    }
    static void Command(Node? n)
    {
        if (n is null) return;
        if (n.List is not { Count: > 0 } || n.List.Any(x => string.IsNullOrWhiteSpace(x.Scalar))) throw new ConfigurationException("Commands must be nonempty argument lists.");
    }
    public void Validate()
    {
        var n=Root;
        Keys(n,"workspace","reports","repository","build","inputs","credentials","reset","masking","execution","ai-model","ai-budget");
        Keys(n.Get("workspace"),"root"); Keys(n.Get("reports"),"root","sections");
        Keys(n.Get("repository"),"url","branch","solution");
        var repo=Required(n,"repository");var url=Text(repo,"url");Text(repo,"branch");RepoPath(Text(repo,"solution"));
        if (Uri.TryCreate(url,UriKind.Absolute,out var uri) && (uri.Scheme=="https" || uri.Scheme=="ssh"))
        { if (!string.IsNullOrEmpty(uri.UserInfo) && uri.Scheme=="https") throw new ConfigurationException("Repository URL must not contain credentials."); }
        else if (!System.Text.RegularExpressions.Regex.IsMatch(url,@"^[\w.-]+@[\w.-]+:[^\s]+$")) throw new ConfigurationException("Repository URL must use HTTPS or SSH.");
        Keys(n.Get("execution"),"time-limit-minutes");Positive(Required(n,"execution"),"time-limit-minutes");
        Keys(n.Get("ai-model"),"name","api-key");var model=Required(n,"ai-model");Text(model,"name");Text(model,"api-key");
        Keys(n.Get("ai-budget"),"amount","currency");var budget=Required(n,"ai-budget");Positive(budget,"amount");
        if (!System.Text.RegularExpressions.Regex.IsMatch(Text(budget,"currency"),"^[A-Z]{3}$")) throw new ConfigurationException("currency must be an uppercase three-letter code.");
        Keys(n.Get("inputs"),"instructions","requirements","setup");Text(Required(n,"inputs"),"instructions");
        Keys(n.Get("build"),"targets");
        var targets=Required(Required(n,"build"),"targets").List;
        if (targets is not {Count:>0}) throw new ConfigurationException("At least one build target is required.");
        var names=new HashSet<string>(StringComparer.Ordinal);
        foreach(var target in targets)
        {
            Keys(target,"name","configuration","project","android","ios");
            if(!names.Add(Text(target,"name"))) throw new ConfigurationException("Build target names must be unique.");
            Text(target,"configuration");RepoPath(Text(target,"project"));
            if(target.Get("android") is null && target.Get("ios") is null) throw new ConfigurationException("Each target requires Android or iOS settings.");
            foreach(var platform in new[]{"android","ios"}) if(target.Get(platform) is {} settings)
            {
                Keys(settings,"framework","properties","script","artifact","app-id");var framework=Text(settings,"framework");
                if(!framework.Contains("-"+platform,StringComparison.Ordinal)) throw new ConfigurationException("Target framework does not match its platform.");
                if(settings.Get("properties") is {} props && (props.Map is null || props.Map.Values.Any(x=>x.Scalar is null))) throw new ConfigurationException("Build properties must be scalar mappings.");
            }
        }
        if(n.Get("credentials") is {} credentials)
        {
            if(credentials.Map is null) throw new ConfigurationException("credentials must be a named mapping.");
            foreach(var value in credentials.Map.Values){Keys(value,"username","password");Text(value,"username");Text(value,"password");}
        }
        Keys(n.Get("reset"),"command","verify-command");Command(n.Get("reset")?.Get("command"));Command(n.Get("reset")?.Get("verify-command"));
        Keys(n.Get("masking"),"rules");
        if(n.Get("masking")?.Get("rules") is {} rules)
        { if(rules.List is null) throw new ConfigurationException("masking.rules must be a list.");foreach(var rule in rules.List){Keys(rule,"element-id");Text(rule,"element-id");} }
        if(n.Get("reports")?.Get("sections") is {} sections && (sections.List is null || sections.List.Any(x=>!new[]{"requirements","scenarios","findings","interpretations","diagnostics"}.Contains(x.Scalar)))) throw new ConfigurationException("Invalid report detail section.");
        foreach(var file in SecretFiles())
        {
            if(!OperatingSystem.IsWindows() && (File.GetUnixFileMode(file)&(UnixFileMode.GroupRead|UnixFileMode.GroupWrite|UnixFileMode.GroupExecute|UnixFileMode.OtherRead|UnixFileMode.OtherWrite|UnixFileMode.OtherExecute))!=0)
                throw new ConfigurationException("Secret configuration requires owner-only file permissions: "+Path.GetFileName(file));
        }
        // Work/report roots may coincide: their run directories have distinct
        // work_<timestamp> and report_<timestamp> names. Cleanup owns clones only.
    }
    IEnumerable<string> SecretFiles()
    {
        var result=new HashSet<string>();
        void Visit(Node n){if(n.Scalar is {} s && Secrets.Contains(s))result.Add(n.Origin);if(n.Map is not null)foreach(var v in n.Map.Values)Visit(v);if(n.List is not null)foreach(var v in n.List)Visit(v);}
        Visit(Root);return result;
    }
    public static void RepoPath(string path)
    { if(Path.IsPathRooted(path)||path.Replace('\\','/').Split('/').Contains(".."))throw new ConfigurationException("Repository paths must remain relative to the clone root."); }
}
