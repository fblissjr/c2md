"""Tests for c2md.citations module."""

from c2md.citations import add_citations


class TestAddCitations:
    def test_basic_link(self):
        md = "Visit [Example](https://example.com) for more."
        cited, refs = add_citations(md)
        assert "Example [1]" in cited
        assert "[1] https://example.com" in refs
        # Original link syntax should be gone
        assert "[Example](https://example.com)" not in cited

    def test_multiple_links(self):
        md = "See [A](https://a.com) and [B](https://b.com)."
        cited, refs = add_citations(md)
        assert "[1]" in cited
        assert "[2]" in cited
        assert "[1] https://a.com" in refs
        assert "[2] https://b.com" in refs

    def test_duplicate_urls_share_number(self):
        md = "[First](https://same.com) and [Second](https://same.com)."
        cited, refs = add_citations(md)
        # Both should reference [1]
        assert "First [1]" in cited
        assert "Second [1]" in cited
        # Only one reference entry
        assert refs.count("https://same.com") == 1

    def test_image_links_not_cited(self):
        md = "![Alt text](https://img.com/photo.jpg)\n[Link](https://example.com)"
        cited, refs = add_citations(md)
        # Image should be untouched
        assert "![Alt text](https://img.com/photo.jpg)" in cited
        # Regular link should be cited
        assert "Link [1]" in cited

    def test_anchor_links_preserved(self):
        md = "Jump to [section](#heading) for details."
        cited, refs = add_citations(md)
        # Anchor links should be unchanged
        assert "[section](#heading)" in cited
        assert refs == ""

    def test_empty_input(self):
        cited, refs = add_citations("")
        assert cited == ""
        assert refs == ""

    def test_no_links(self):
        md = "Plain text with no links at all."
        cited, refs = add_citations(md)
        assert cited == md
        assert refs == ""

    def test_empty_link_text(self):
        md = "Click [](https://example.com) here."
        cited, refs = add_citations(md)
        assert "[1]" in cited
        assert "[1] https://example.com" in refs

    def test_references_header(self):
        md = "[Link](https://example.com)"
        _, refs = add_citations(md)
        assert "## References" in refs

    def test_no_duplication_bug(self):
        """The old crawl4ai citation system duplicated link text.
        Verify our implementation doesn't have this bug."""
        md = "[Contact sales](https://example.com/sales)"
        cited, refs = add_citations(md)
        # Should NOT produce "Contact salesContact sales"
        assert "Contact sales [1]" in cited
        assert cited.count("Contact sales") == 1
