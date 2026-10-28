using Cimt;

namespace Cimt.UnitTests;

public sealed class CommandTests
{
    [Theory]
    [InlineData("unknown", "--config", "file.yaml")]
    [InlineData("run", "--other", "file.yaml")]
    [InlineData("run", "--config")]
    [InlineData("run", "--config", "--branch")]
    [InlineData("run", "--config", "one.yaml", "--config", "two.yaml")]
    public void InvalidArgumentsAreRejected(params string[] arguments)
    {
        Assert.Throws<ConfigurationException>(() => CommandLine.Parse(arguments));
    }

    [Fact]
    public void BranchOverrideRemainsLiteral()
    {
        var options = CommandLine.Parse(["run", "--config", "local.yaml", "--branch", "feature/fix"]);
        Assert.Equal("feature/fix", options.Values["--branch"]);
    }

    [Fact]
    public void ResetExecutableKeepsItsFileOriginButArgumentsStayLiteral()
    {
        var origin = "/fixture/nested/config.yaml";
        var command = new Node(null, null,
            [new("./reset.sh", null, null, origin), new("./literal-argument", null, null, origin)], origin);
        var result = Assert.IsType<string[]>(RuntimeRequest.ConvertNode(command, "command"));
        Assert.Equal(["/fixture/nested/reset.sh", "./literal-argument"], result);
    }

    [Fact]
    public void HtmlRendererEscapesInputAndRemovesSecrets()
    {
        var origin = "/fixture/config.yaml";
        var root = new Node(null, new()
        {
            ["repository"] = new(null, new()
            {
                ["branch"] = new("<branch>", null, null, origin)
            }, null, origin),
            ["ai-model"] = new(null, new()
            {
                ["api-key"] = new("synthetic-secret", null, null, origin)
            }, null, origin)
        }, null, origin);
        var state = new RunState(new Configuration(root), "/unused", DateTimeOffset.UnixEpoch,
            new RunDeadline(DateTimeOffset.UtcNow.AddMinutes(1)));
        state.Errors.Add("<script>synthetic-secret</script>");
        var html = new RunHtmlRenderer(state.Configuration).Render(state, new(3, "inconclusive", "incomplete"), null);
        Assert.DoesNotContain("synthetic-secret", html);
        Assert.DoesNotContain("<script>", html);
        Assert.Contains("&lt;script&gt;", html);
        Assert.Contains("&lt;branch&gt;", html);
    }
}
