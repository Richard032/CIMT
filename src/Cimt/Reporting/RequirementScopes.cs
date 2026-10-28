namespace Cimt;

/// <summary>Uses configured targets and startup devices, not only successful builds.</summary>
public static class RequirementScopes
{
    public static IReadOnlyList<RequirementScope> Create(RunState state)
    {
        var scopes = new List<RequirementScope>();
        foreach (var target in state.Configuration.Root.Get("build")!.Get("targets")!.List!)
            foreach (var device in state.Devices)
                if (target.Get(device["platform"]) is not null)
                    scopes.Add(Create(state, target.Value("name")!, device));
        if (scopes.Count == 0)
            scopes.Add(new("", "", "", "", "No compatible target/device execution was available."));
        return scopes;
    }

    private static RequirementScope Create(RunState state, string target, Dictionary<string, string> device)
    {
        var built = state.Builds.Any(build => build["target"] == target && build["platform"] == device["platform"]);
        var reason = built ? "The device objective did not evaluate this requirement."
            : "No installable build was available for this target/platform.";
        return new(target, device["platform"], device["id"], device.GetValueOrDefault("name", device["platform"]), reason);
    }
}
