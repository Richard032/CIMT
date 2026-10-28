using Cimt;

namespace Cimt.UnitTests;

/// <summary>Each case checks one explicit heading form, without guessing from prose.</summary>
public sealed class RequirementHeadingTests
{
    [Theory]
    [InlineData("# Requirements", 1)]
    [InlineData("###### Requirements", 6)]
    [InlineData("   ## Requirements ##", 2)]
    [InlineData("#", 1)]
    public void HashHeadingKeepsItsOriginalText(string text, int level)
    {
        var heading = Assert.Single(RequirementHeadingReader.ReadAll([text]));
        Assert.Equal(text, heading.Text);
        Assert.Equal(level, heading.Level);
        Assert.Equal(1, heading.StartLine);
        Assert.Equal(1, heading.EndLine);
    }

    [Theory]
    [InlineData("===", 1)]
    [InlineData("---", 2)]
    public void UnderlinedHeadingKeepsBothLines(string underline, int level)
    {
        var heading = Assert.Single(RequirementHeadingReader.ReadAll(["Requirements", underline]));
        Assert.Equal("Requirements\n" + underline, heading.Text);
        Assert.Equal(level, heading.Level);
        Assert.Equal(2, heading.EndLine);
    }

    [Theory]
    [InlineData("Requirements")]
    [InlineData("#Save must work")]
    [InlineData("####### Save must work")]
    [InlineData("    # Code example")]
    public void OtherTextIsNotGuessedToBeAHeading(string text)
    {
        Assert.Empty(RequirementHeadingReader.ReadAll([text]));
    }

    [Fact]
    public void ListItemBeforeARuleIsNotAHeading()
    {
        Assert.Empty(RequirementHeadingReader.ReadAll(["- Save must work", "---"]));
    }

    [Theory]
    [InlineData("```")]
    [InlineData("~~~")]
    public void CodeExampleHeadingsStayInTheSource(string fence)
    {
        var heading = Assert.Single(RequirementHeadingReader.ReadAll(
            [fence, "# Example", fence, "# Actual section"]));
        Assert.Equal("# Actual section", heading.Text);
        Assert.Equal(4, heading.StartLine);
    }
}
