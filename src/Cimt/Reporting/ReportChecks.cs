using System.Text.Json;
using static Cimt.ReportHtml;

namespace Cimt;

/// <summary>Uses the saved override decision when selecting effective failures.</summary>
public static class ReportChecks
{
    public static bool Overridden(JsonElement scenario, JsonElement check) => Rows(scenario, "requirements")
        .Any(row => Field(row, "id") == Field(check, "requirementId") && Field(row, "status") == "overridden");

    public static bool Failed(JsonElement scenario, JsonElement check) =>
        Field(check, "status") == "failed" && !Overridden(scenario, check);
}
