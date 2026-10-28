namespace Cimt;

/// <summary>Allows only one CIMT command to hold the Mac run lock.</summary>
public sealed class MachineLock : IDisposable
{
    private readonly FileStream stream;

    public MachineLock()
    {
        var root = Path.Combine(Configuration.InstallationRoot, "state");
        Directory.CreateDirectory(root);
        var path = Path.Combine(root, "run.lock");
        if (new FileInfo(path).LinkTarget is not null)
            throw new ConfigurationException("CIMT lock path must not be a symbolic link.");
        stream = Acquire(path);
    }

    private static FileStream Acquire(string path)
    {
        try
        {
            return new FileStream(path, FileMode.OpenOrCreate, FileAccess.ReadWrite, FileShare.None);
        }
        catch (IOException)
        {
            throw new ConfigurationException("Another CIMT run is active on this Mac.");
        }
    }

    public void Dispose() => stream.Dispose();
}
