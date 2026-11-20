namespace Cimt;

/// <summary>Opens a finalized report in the Mac's default browser.</summary>
public static class RunReportBrowser
{
    public static async Task Open(string report, ICommandRunner runner)
    {
        try
        {
            var result = await runner.Run(new("/usr/bin/open", [report], TimeoutSeconds: 10));
            if (result.Exit == 0)
                return;
        }
        catch (Exception error) when (error is ConfigurationException or IOException or UnauthorizedAccessException
            or System.ComponentModel.Win32Exception)
        {
            // The terminal already shows the report location.
        }
        Console.Error.WriteLine("CIMT could not open the browser. Open the report location printed above.");
    }
}
