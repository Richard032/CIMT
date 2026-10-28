using YamlDotNet.RepresentationModel;

namespace Cimt;

public interface IConfigurationNodeReader
{
    Node Read(string file);
}

/// <summary>Reads YAML and attaches the source file to each value.</summary>
public sealed class YamlConfigurationReader : IConfigurationNodeReader
{
    public Node Read(string file)
    {
        file = Path.GetFullPath(file);
        try
        {
            var yaml = Load(file);
            var root = Convert(yaml.Documents[0].RootNode, file);
            if (root.Map is null)
                throw new ConfigurationException("Configuration root must be a mapping.");
            return root;
        }
        catch (ConfigurationException) { throw; }
        catch (Exception error) when (error is IOException or UnauthorizedAccessException or
            YamlDotNet.Core.YamlException or ArgumentException or InvalidCastException)
        {
            throw new ConfigurationException("Cannot read valid YAML configuration: " + Path.GetFileName(file));
        }
    }

    private static YamlStream Load(string file)
    {
        var yaml = new YamlStream();
        using var reader = File.OpenText(file);
        yaml.Load(reader);
        if (yaml.Documents.Count != 1)
            throw new ConfigurationException("Configuration must contain exactly one YAML document.");
        return yaml;
    }

    private static Node Convert(YamlNode node, string origin) => node switch
    {
        YamlScalarNode scalar => new(scalar.Value ?? "", null, null, origin),
        YamlSequenceNode sequence => new(null, null, sequence.Children.Select(child => Convert(child, origin)).ToList(), origin),
        YamlMappingNode mapping => new(null, mapping.Children.ToDictionary(
            item => ((YamlScalarNode)item.Key).Value ?? "", item => Convert(item.Value, origin), StringComparer.Ordinal), null, origin),
        _ => throw new ConfigurationException("Unsupported YAML structure.")
    };
}
