using System.Security.Cryptography;
using System.Text;

namespace Cimt;

/// <summary>Gives the native helper a short socket address while its files stay in the run folder.</summary>
public sealed class NativeHomeLink
{
    public string LinkPath { get; }

    public NativeHomeLink(string registry)
    {
        // One installation has one active run. Its registry gives the link a stable name for this user.
        var identity = Path.GetFullPath(registry) + "\n" + Environment.UserName;
        var hash = Convert.ToHexString(SHA256.HashData(Encoding.UTF8.GetBytes(identity)))[..20];
        LinkPath = Path.Combine("/tmp", "cimt-native-" + hash);
    }

    public string Create(string target)
    {
        var link = new DirectoryInfo(LinkPath);
        if (link.LinkTarget is not null || link.Exists || File.Exists(LinkPath))
            throw new ConfigurationException("The native helper link is already occupied; it will not be reused.");
        Directory.CreateSymbolicLink(LinkPath, Path.GetFullPath(target));
        return LinkPath;
    }

    public void Remove(string expectedTarget)
    {
        var link = new DirectoryInfo(LinkPath);
        if (link.LinkTarget is null)
        {
            if (link.Exists || File.Exists(LinkPath))
                throw new IOException("The native helper link is not owned by this run.");
            return;
        }
        var target = Path.GetFullPath(link.LinkTarget, "/tmp");
        if (target != Path.GetFullPath(expectedTarget))
            throw new IOException("The native helper link target does not match this run.");
        // Delete the link only. The work-folder manager deletes the owned target later.
        File.Delete(LinkPath);
    }
}
