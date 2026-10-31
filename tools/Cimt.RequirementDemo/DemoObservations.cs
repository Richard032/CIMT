namespace Cimt.RequirementDemo;

/// <summary>Supply all five statuses. These are examples, not observations of a real application.</summary>
public static class DemoObservations
{
    public static object Execution(IReadOnlyList<RequirementDefinition> requirements) => new
    {
        devices = new[] { "android", "ios" }.Select(platform => new {
            device = new { id = "synthetic-" + platform, platform, name = "Simulated " + platform + " phone" },
            scenarios = new[] { new {
                target = "Demo", verdict = "failed", completion = "incomplete", crashes = Array.Empty<object>(),
                steps = new[] {
                    new { step = 0, action = "synthetic preparation", observation = "Synthetic checkerboard fixture; no device capture.", screenshot = "devices/" + platform + "/step-0.png" },
                    new { step = 1, action = "synthetic observation", observation = "Second synthetic evidence record; no application action.", screenshot = "devices/" + platform + "/step-1.png" }
                }, requirements = Results(requirements)
            } }
        }).ToArray()
    };

    private static object[] Results(IReadOnlyList<RequirementDefinition> definitions)
    {
        var statuses = new[] { "passed", "failed", "not tested", "inconclusive", "overridden" };
        var observations = new[] { "Synthetic: saved value is visible after reopening.",
            "Synthetic: returning from the menu loses the selected value.", "", "", "" };
        var reasons = new[] { "", "", "Required external equipment was unavailable in this example.",
            "The displayed value could not establish whether persistence succeeded.",
            "The instruction excludes export, while this requirement asks for export." };
        return definitions.Select((definition, index) => new
        {
            id = definition.Id,
            status = statuses[index],
            expected = definition.Text,
            observed = observations[index],
            reason = reasons[index],
            instructionQuote = index == 4 ? "Do not test export." : "",
            step = (int?)null,
            screenshot = "",
            evidenceError = "Synthetic demo: no device screenshot was collected."
        }).ToArray();
    }
}
