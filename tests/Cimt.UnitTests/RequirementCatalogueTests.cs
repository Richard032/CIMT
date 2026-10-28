using Cimt;

namespace Cimt.UnitTests;

/// <summary>Small examples show how free text is grouped without losing its content.</summary>
public sealed class RequirementCatalogueTests
{
    [Fact]
    public void EmptyInputHasNoRequirements() => Assert.Empty(RequirementCatalogue.Read(" \n\t"));

    [Fact]
    public void WrappedLinesStayTogether()
    {
        var row = Assert.Single(RequirementCatalogue.Read("The app shall remain running\nwhen a button is pressed."));
        Assert.Equal("REQ-0001", row.Id);
        Assert.Equal(1, row.StartLine);
        Assert.Equal(2, row.EndLine);
        Assert.Contains("\nwhen", row.Text);
    }

    [Fact]
    public void CompletedLinesStartSeparateItems()
    {
        var rows = RequirementCatalogue.Read("Save shall work.\nBack shall work.");
        Assert.Equal(2, rows.Count);
        Assert.Equal("REQ-0002", rows[1].Id);
    }

    [Fact]
    public void BulletsHaveSeparateResults()
    {
        var rows = RequirementCatalogue.Read("- Save value\n  and keep it\n- Open menu");
        Assert.Equal(2, rows.Count);
        Assert.Contains("and keep it", rows[0].Text);
        Assert.Equal(3, rows[1].StartLine);
    }

    [Fact]
    public void OriginalLabelsAndDuplicateTextArePreserved()
    {
        var rows = RequirementCatalogue.Read("FR-01 Save\nFR-01 Save");
        Assert.Equal(2, rows.Count);
        Assert.Equal(rows[0].Text, rows[1].Text);
        Assert.NotEqual(rows[0].Id, rows[1].Id);
    }

    [Fact]
    public void ParagraphsHaveTheirOriginalLineRanges()
    {
        var rows = RequirementCatalogue.Read("\nFirst paragraph\n\nSecond paragraph\n");
        Assert.Equal(2, rows[0].StartLine);
        Assert.Equal(2, rows[0].EndLine);
        Assert.Equal(4, rows[1].StartLine);
        Assert.Equal(4, rows[1].EndLine);
    }

    [Fact]
    public void NumberedItemsNeedNoSpecialFormatConfiguration()
    {
        Assert.Equal(2, RequirementCatalogue.Read("1. Save\n2) Back").Count);
    }

    [Fact]
    public void HeadingsAreContextAndTableRowsRemainRequirements()
    {
        var document = RequirementCatalogue.Parse("# Requirements\n| ID | Expectation |\n| R1 | Save works |");
        Assert.Equal(2, document.Items.Count);
        Assert.Equal("# Requirements", Assert.Single(document.Headings).Text);
        Assert.Equal("# Requirements", document.Items[0].HeadingContext);
    }

    [Fact]
    public void HeadingDoesNotReceiveARequirementId()
    {
        var row = Assert.Single(RequirementCatalogue.Read("# Requirements\n- Saving must work."));
        Assert.Equal("REQ-0001", row.Id);
        Assert.Equal("- Saving must work.", row.Text);
        Assert.Equal(2, row.StartLine);
        Assert.Equal(2, row.EndLine);
        Assert.Equal("# Requirements", row.HeadingContext);
    }

    [Fact]
    public void HeadingOnlyDocumentRetainsItsContextWithoutRequirements()
    {
        var document = RequirementCatalogue.Parse("# Requirements\n\n## Android");
        Assert.Empty(document.Items);
        Assert.Equal(2, document.Headings.Count);
    }

    [Fact]
    public void NewHeadingEndsThePreviousRequirement()
    {
        var document = RequirementCatalogue.Parse("Save the value\n## Navigation\nBack works.");
        Assert.Equal(2, document.Items.Count);
        Assert.Equal(1, document.Items[0].EndLine);
        Assert.Empty(document.Items[0].HeadingContext);
        Assert.Equal("## Navigation", document.Items[1].HeadingContext);
    }

    [Fact]
    public void SiblingHeadingReplacesThePreviousSectionContext()
    {
        var rows = RequirementCatalogue.Read("# Requirements\n## Android\n- Save\n## iOS\n- Back");
        Assert.Equal("# Requirements\n## Android", rows[0].HeadingContext);
        Assert.Equal("# Requirements\n## iOS", rows[1].HeadingContext);
    }

    [Fact]
    public void UnderlinedHeadingKeepsRequirementSourceLines()
    {
        var row = Assert.Single(RequirementCatalogue.Read("Requirements\n===\nSave works."));
        Assert.Equal(3, row.StartLine);
        Assert.Equal(3, row.EndLine);
        Assert.Equal("Requirements\n===", row.HeadingContext);
    }

    [Fact]
    public void SourceFingerprintChangesWhenTextChanges()
    {
        Assert.Equal(RequirementCatalogue.Hash("Save"), RequirementCatalogue.Hash("Save"));
        Assert.NotEqual(RequirementCatalogue.Hash("Save"), RequirementCatalogue.Hash("Back"));
    }

    [Fact]
    public void WindowsLineEndingsKeepTheSameIds()
    {
        Assert.Equal(RequirementCatalogue.Read("Save.\nBack."), RequirementCatalogue.Read("Save.\r\nBack."));
    }
}
