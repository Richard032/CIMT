using System.IO.Compression;

namespace Cimt.Build;

/// <summary>Packs a simulator bundle in the ZIP format accepted by the device adapter.</summary>
public static class SimulatorArtifact
{
    public static string Create(string output)
    {
        var bundles = Directory.GetDirectories(output, "*.app", SearchOption.TopDirectoryOnly);
        if (bundles.Length != 1)
            throw new InvalidOperationException("Simulator build must produce one .app bundle in its output folder.");
        // Keep the bundle name at the archive root. A simulator ZIP is not a phone IPA.
        var archive = Path.Combine(output, "simulator-app.zip");
        ZipFile.CreateFromDirectory(bundles[0], archive, CompressionLevel.Fastest, includeBaseDirectory: true);
        return archive;
    }
}
