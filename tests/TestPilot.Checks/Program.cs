using TestPilot;
using TestPilot.Checks;
using System.Runtime.Versioning;

[assembly: SupportedOSPlatform("macos")]

if (args.FirstOrDefault() == "--public-command-probe")
    return await Entry.Run(args.Skip(1).ToArray());

if (args.Contains("--lock-probe"))
{
    try
    {
        using var held = new MachineLock();
        return 1;
    }
    catch (ConfigurationException) { return 0; }
}

var temporary = Path.Combine(Path.GetTempPath(), "testpilot-checks-" + Guid.NewGuid().ToString("N"));
Directory.CreateDirectory(temporary);
Environment.SetEnvironmentVariable("TESTPILOT_INSTALL_ROOT", temporary);
try
{
    return await new FoundationChecks(temporary).Run();
}
finally
{
    Directory.Delete(temporary, recursive: true);
}
