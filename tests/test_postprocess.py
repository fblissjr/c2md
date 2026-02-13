"""Tests for c2md._postprocess module.

Ported from c4md tests/test_processors.py.
"""

from c2md._postprocess import (
    clean_markdown,
    collapse_blank_lines,
    fix_citation_duplication,
    fix_heading_linebreaks,
    strip_empty_image_links,
)


class TestFixHeadingLinebreaks:
    def test_orphaned_heading_collapses_fragments(self):
        md = "#\nComplete\nGuide\nto\nBuilding\n\nSome paragraph."
        result = fix_heading_linebreaks(md)
        assert "# Complete Guide to Building" in result
        assert "Some paragraph." in result

    def test_orphaned_h2_collapses(self):
        md = "##\nGetting\nStarted\n\nContent here."
        result = fix_heading_linebreaks(md)
        assert "## Getting Started" in result

    def test_orphaned_h3_collapses(self):
        md = "###\nDeep\nDive\n\nMore content."
        result = fix_heading_linebreaks(md)
        assert "### Deep Dive" in result

    def test_normal_heading_not_collapsed(self):
        md = "# FAQ\nYes.\nNo.\nMaybe."
        result = fix_heading_linebreaks(md)
        assert result == md

    def test_heading_with_text_preserved(self):
        md = "# My Great Title\n\nSome content."
        result = fix_heading_linebreaks(md)
        assert result == md

    def test_orphaned_heading_stops_at_empty_line(self):
        md = "#\nWord1\nWord2\n\nParagraph text here."
        result = fix_heading_linebreaks(md)
        assert "# Word1 Word2" in result
        assert "\nParagraph text here." in result

    def test_orphaned_heading_stops_at_markdown_syntax(self):
        md = "#\nTitle\nWords\n- list item"
        result = fix_heading_linebreaks(md)
        assert "# Title Words" in result
        assert "- list item" in result

    def test_orphaned_heading_stops_at_long_line(self):
        md = "#\nShort\nThis is a full sentence with many words."
        result = fix_heading_linebreaks(md)
        assert "# Short" in result

    def test_orphaned_heading_no_fragments(self):
        md = "#\n\nSome paragraph."
        result = fix_heading_linebreaks(md)
        assert result == md

    def test_no_headings(self):
        md = "Just a paragraph.\nAnother line."
        result = fix_heading_linebreaks(md)
        assert result == md

    def test_empty_string(self):
        assert fix_heading_linebreaks("") == ""


class TestFixCitationDuplication:
    def test_basic_duplication(self):
        md = "Contact sales[39]Contact sales"
        result = fix_citation_duplication(md)
        assert result == "Contact sales[39]"

    def test_no_duplication(self):
        md = "Click here[5]Learn more"
        result = fix_citation_duplication(md)
        assert result == md

    def test_with_whitespace(self):
        md = "Get started [12] Get started"
        result = fix_citation_duplication(md)
        assert result == "Get started[12]"

    def test_single_word(self):
        md = "Pricing[3]Pricing"
        result = fix_citation_duplication(md)
        assert result == "Pricing[3]"

    def test_multiple_duplications(self):
        md = "Foo[1]Foo and Bar[2]Bar"
        result = fix_citation_duplication(md)
        assert "Foo[1]" in result
        assert "Bar[2]" in result
        assert "Foo[1]Foo" not in result
        assert "Bar[2]Bar" not in result

    def test_preserves_normal_citations(self):
        md = "As shown in the study[1], results were positive[2]."
        result = fix_citation_duplication(md)
        assert result == md

    def test_no_citations(self):
        md = "Just plain text without any citations."
        result = fix_citation_duplication(md)
        assert result == md


class TestStripEmptyImageLinks:
    def test_empty_image(self):
        md = "Before ![](https://example.com/img.png) After"
        result = strip_empty_image_links(md)
        assert "![](https://example.com/img.png)" not in result
        assert "Before" in result
        assert "After" in result

    def test_empty_link(self):
        md = "Before [](https://example.com) After"
        result = strip_empty_image_links(md)
        assert "[](https://example.com)" not in result

    def test_preserves_image_with_alt(self):
        md = "![alt text](https://example.com/img.png)"
        result = strip_empty_image_links(md)
        assert result == md

    def test_preserves_link_with_text(self):
        md = "[click here](https://example.com)"
        result = strip_empty_image_links(md)
        assert result == md

    def test_preserves_nested_image_link(self):
        md = "[![logo](https://img.com/logo.png)](https://example.com)"
        result = strip_empty_image_links(md)
        assert "logo" in result
        assert "https://img.com/logo.png" in result

    def test_multiple_empty_images(self):
        md = "![](a.png) text ![](b.png) more"
        result = strip_empty_image_links(md)
        assert "![](a.png)" not in result
        assert "![](b.png)" not in result
        assert "text" in result
        assert "more" in result

    def test_no_images(self):
        md = "Just plain text."
        result = strip_empty_image_links(md)
        assert result == md


class TestCollapseBlankLines:
    def test_collapses_many_blank_lines(self):
        md = "A\n\n\n\n\n\nB"
        result = collapse_blank_lines(md)
        assert result == "A\n\n\nB"

    def test_preserves_double_blank(self):
        md = "A\n\n\nB"
        result = collapse_blank_lines(md)
        assert result == md

    def test_preserves_single_blank(self):
        md = "A\n\nB"
        result = collapse_blank_lines(md)
        assert result == md


class TestCleanMarkdown:
    def test_empty_input(self):
        assert clean_markdown("") == ""

    def test_runs_all_fixups(self):
        md = (
            "#\nBroken\nTitle\n\n"
            "Contact us[5]Contact us\n\n"
            "![](empty.png)\n\n\n\n\n"
            "Real content here."
        )
        result = clean_markdown(md)
        assert "# Broken Title" in result
        assert "Contact us[5]" in result
        assert "Contact us[5]Contact us" not in result
        assert "![](empty.png)" not in result
        assert "\n\n\n\n" not in result
        assert "Real content here." in result

    def test_strips_trailing_whitespace(self):
        md = "Content here.\n\n\n"
        result = clean_markdown(md)
        assert result == "Content here."
