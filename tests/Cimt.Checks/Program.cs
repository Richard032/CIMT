using Cimt;
using Cimt.Checks;
using System.Runtime.Versioning;

[assembly: SupportedOSPlatform("macos")]

if (args.Contains("--lock-probe"))
{
    try
    {
        using var held = new MachineLock();
        return 1;
    }
    catch (ConfigurationException) { return 0; }
}

var temporary = Path.Combine(Path.GetTempPath(), "cimt-checks-" + Guid.NewGuid().ToString("N"));
Directory.CreateDirectory(temporary);
Environment.SetEnvironmentVariable("CIMT_INSTALL_ROOT", temporary);
try
{
    return new FoundationChecks(temporary).Run();
}
finally
{
    Directory.Delete(temporary, recursive: true);
}
