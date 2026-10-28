using Cimt;
using System.Text.Json;

namespace Cimt.UnitTests;

/// <summary>Only invented values are used. No private configuration is read.</summary>
public sealed class RedactionTests
{
    [Theory]
    [InlineData("páss")]
    [InlineData("a\"b")]
    [InlineData("a\\b")]
    [InlineData("a\nb")]
    public void JsonStringsAreRedactedBeforeEscaping(string secret)
    {
        var source = JsonSerializer.SerializeToElement(new { observation = "value " + secret });
        var safe = new JsonTextRedactor(Settings(secret).Scrub).Text(source)!;
        using var parsed = JsonDocument.Parse(safe.ToJsonString());
        Assert.Equal("value <redacted>", parsed.RootElement.GetProperty("observation").GetString());
    }

    [Fact]
    public void OneDigitSecretCannotChangeJsonNumbersOrPropertyNames()
    {
        var source = JsonSerializer.SerializeToElement(new { step1 = 1, text = "value 1" });
        var safe = new JsonTextRedactor(Settings("1").Scrub).Text(source)!;
        using var parsed = JsonDocument.Parse(safe.ToJsonString());
        Assert.Equal(1, parsed.RootElement.GetProperty("step1").GetInt32());
        Assert.Equal("value <redacted>", parsed.RootElement.GetProperty("text").GetString());
    }

    [Fact]
    public void ExistingMarkersSurviveRepeatedRedaction()
    {
        var configuration = Settings("e");
        Assert.Equal("s<redacted>cr<redacted>t", configuration.Scrub(configuration.Scrub("secret")));
    }

    [Fact]
    public void SecretStartingWithTheMarkerIsStillRemovedCompletely()
    {
        Assert.Equal("<redacted>", Settings("<redacted>private").Scrub("<redacted>private"));
    }

    [Theory]
    [InlineData("páss")]
    [InlineData("a\"b")]
    [InlineData("a\\b")]
    public void JsonEscapedSecretsAreRemovedFromTextLogs(string secret)
    {
        var escaped = JsonSerializer.Serialize(secret)[1..^1];
        Assert.Equal("log <redacted>", Settings(secret).Scrub("log " + escaped));
    }

    [Fact]
    public void ConfigurationSnapshotRemovesSecretsInsideOtherValues()
    {
        var configuration = Settings("private");
        var value = new Node("prefix private suffix", null, null, "/fixture/config.yaml");
        Assert.Equal("prefix <redacted> suffix", configuration.Sanitized(value));
    }

    [Fact]
    public void UnknownFieldsAreTextEvenWhenNamedStatus()
    {
        var source = JsonSerializer.SerializeToElement(new { diagnostics = new { status = "failed" } });
        var safe = new RunReportRedactor(new JsonTextRedactor(Settings("failed").Scrub)).Run(source);
        Assert.Equal("<redacted>", safe["diagnostics"]!["status"]!.GetValue<string>());
    }

    [Fact]
    public void MetadataExemptionCannotKeepAnArbitraryObject()
    {
        var source = JsonSerializer.SerializeToElement(new { status = new { text = "private" } });
        Assert.Throws<ConfigurationException>(() => new JsonTextRedactor(Settings("private").Scrub)
            .Record(source, ["status"]));
    }

    [Fact]
    public void RequirementIdsAndStatusesSurviveWhileSourceTextIsRedacted()
    {
        var source = JsonSerializer.Deserialize<JsonElement>("""
            {"requirementCoverage":{"sourceSha256":"hash1","requirements":[{
            "status":"failed","definition":{"id":"REQ-0001","text":"value REQ-0001","startLine":1,"endLine":1},
            "results":[{"status":"failed","expected":"REQ-0001","observed":"REQ-0001",
            "screenshot":"devices/1/check-0001.png","scope":{"target":"Release1","platform":"android","deviceId":"1"}}]}]}}
            """);
        var safe = new RunReportRedactor(new JsonTextRedactor(Settings("REQ-0001").Scrub)).Run(source);
        var row = safe["requirementCoverage"]!["requirements"]![0]!;
        Assert.Equal("REQ-0001", row["definition"]!["id"]!.GetValue<string>());
        Assert.Equal("failed", row["status"]!.GetValue<string>());
        Assert.Equal("value <redacted>", row["definition"]!["text"]!.GetValue<string>());
        Assert.Equal("<redacted>", row["results"]![0]!["observed"]!.GetValue<string>());
    }

    internal static Configuration Settings(string secret)
    {
        const string origin = "/fixture/config.yaml";
        return new(new Node(null, new()
        {
            ["repository"] = new(null, new() { ["branch"] = new("main", null, null, origin) }, null, origin),
            ["build"] = new(null, new() { ["targets"] = new(null, null, [], origin) }, null, origin),
            ["credentials"] = new(null, new() { ["test"] = new(null, new()
            {
                ["password"] = new(secret, null, null, origin)
            }, null, origin) }, null, origin)
        }, null, origin));
    }
}
