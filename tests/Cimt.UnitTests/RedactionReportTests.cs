using Cimt;
using System.Text.Json;
using System.Net;

namespace Cimt.UnitTests;

/// <summary>Use the real report writer to protect the final JSON and HTML contract.</summary>
public sealed class RedactionReportTests
{
    [Fact]
    public void FailedPasswordCannotHideAFailedOutcome()
    {
        using var fixture = new ReportFixture("failed");
        Assert.Equal(1, fixture.Write());
        var result = fixture.Result();
        Assert.Equal("failed", result.GetProperty("verdict").GetString());
        var scenario = result.GetProperty("execution").GetProperty("devices")[0].GetProperty("scenarios")[0];
        Assert.Equal("failed", scenario.GetProperty("checks")[0].GetProperty("status").GetString());
        Assert.Contains("Verdict: failed", fixture.Html());
    }

    [Fact]
    public void OneDigitPasswordLeavesValidJsonAndWorkingEvidenceLinks()
    {
        using var fixture = new ReportFixture("1");
        fixture.State.Stages.Add(new { stage = "fixture", sequence = 1 });
        fixture.Write();
        var result = fixture.Result();
        Assert.Equal(1, result.GetProperty("stages")[0].GetProperty("sequence").GetInt32());
        var scenario = result.GetProperty("execution").GetProperty("devices")[0].GetProperty("scenarios")[0];
        Assert.Equal("Release1", scenario.GetProperty("target").GetString());
        Assert.Contains("devices/1/check-0001.png", fixture.Html());
        Assert.Contains("devices/1/step-0001.png", fixture.Html());
    }

    [Fact]
    public void YearPasswordCannotChangeRunIdentity()
    {
        using var fixture = new ReportFixture("2026");
        fixture.Write();
        Assert.Equal(fixture.State.Identity.Id, fixture.Result().GetProperty("runIdentity").GetProperty("id").GetString());
        Assert.All(fixture.Result().GetProperty("activity").EnumerateArray(), item =>
            Assert.True(DateTimeOffset.TryParse(item.GetProperty("timestamp").GetString(), out _)));
        Assert.Contains(fixture.State.Identity.Id, fixture.Html());
    }

    [Theory]
    [InlineData("a\"b")]
    [InlineData("páss")]
    [InlineData("a\\b")]
    public void EscapedSecretsAreAbsentFromDecodedDiagnostics(string secret)
    {
        using var fixture = new ReportFixture(secret);
        fixture.Write();
        var device = fixture.Result().GetProperty("execution").GetProperty("devices")[0];
        Assert.Equal("<redacted>", device.GetProperty("diagnostics").GetString());
        var decoded = WebUtility.HtmlDecode(fixture.Html());
        Assert.DoesNotContain(secret, decoded);
        Assert.DoesNotContain(JsonSerializer.Serialize(secret)[1..^1], decoded);
    }

    private sealed class ReportFixture(string secret) : IDisposable
    {
        private readonly TestDirectory folder = new();
        private RunState? state;
        public RunState State => state ??= new(RedactionTests.Settings(secret),
            TestRunFolders.At(folder.Path, DateTimeOffset.Parse("2026-10-28T12:00:00Z")),
            new RunDeadline(DateTimeOffset.UtcNow.AddMinutes(1)));

        public int Write()
        {
            Directory.CreateDirectory(Path.Combine(folder.Path, "devices/1"));
            File.WriteAllBytes(Path.Combine(folder.Path, "devices/1/check-0001.png"), [137, 80, 78, 71]);
            File.WriteAllBytes(Path.Combine(folder.Path, "devices/1/step-0001.png"), [137, 80, 78, 71]);
            // Worker-shaped data contains a real failure and invented secret observations.
            var execution = new { devices = new[] { new {
                device = new { id = "1", platform = "android", name = "Phone" }, diagnostics = secret,
                error = (string?)null, stoppingReason = (string?)null,
                scenarios = new[] { new { target = "Release1", verdict = "failed", completion = "complete", crashes = Array.Empty<object>(),
                    checks = new[] { new { source = "instructions", subject = "Save", status = "failed", expected = "Saved",
                        observed = secret, screenshot = "devices/1/check-0001.png" } },
                    steps = new[] { new { action = "tap", observation = secret, screenshot = "devices/1/step-0001.png" } }
                } }
            } } };
            File.WriteAllText(Path.Combine(folder.Path, "ui-results.json"), JsonSerializer.Serialize(execution));
            return new RunReportWriter().Write(State);
        }

        public JsonElement Result() => JsonSerializer.Deserialize<JsonElement>(File.ReadAllText(Path.Combine(folder.Path, "result.json")));
        public string Html() => File.ReadAllText(Path.Combine(folder.Path, "index.html"));
        public void Dispose() => folder.Dispose();
    }
}
