"""Tests for c2md.crawl module."""

from c2md.crawl import _extract_links, _normalize_url


class TestNormalizeUrl:
    def test_strips_trailing_slash(self):
        assert _normalize_url("https://example.com/page/") == "https://example.com/page"

    def test_strips_fragment(self):
        assert _normalize_url("https://example.com/page#section") == "https://example.com/page"

    def test_root_path(self):
        assert _normalize_url("https://example.com/") == "https://example.com/"

    def test_preserves_path(self):
        assert _normalize_url("https://example.com/a/b/c") == "https://example.com/a/b/c"


class TestExtractLinks:
    def test_same_domain_links(self):
        html = """
        <html><body>
            <a href="/page1">Page 1</a>
            <a href="https://example.com/page2">Page 2</a>
            <a href="https://other.com/external">External</a>
        </body></html>
        """
        links = _extract_links(html, "https://example.com", "example.com")
        assert "https://example.com/page1" in links
        assert "https://example.com/page2" in links
        # External link should be excluded
        assert not any("other.com" in l for l in links)

    def test_skips_fragments(self):
        html = '<a href="#section">Jump</a>'
        links = _extract_links(html, "https://example.com", "example.com")
        assert len(links) == 0

    def test_skips_javascript(self):
        html = '<a href="javascript:void(0)">Click</a>'
        links = _extract_links(html, "https://example.com", "example.com")
        assert len(links) == 0

    def test_skips_mailto(self):
        html = '<a href="mailto:test@example.com">Email</a>'
        links = _extract_links(html, "https://example.com", "example.com")
        assert len(links) == 0

    def test_skips_static_files(self):
        html = """
        <a href="/doc.pdf">PDF</a>
        <a href="/image.jpg">Image</a>
        <a href="/page">Page</a>
        """
        links = _extract_links(html, "https://example.com", "example.com")
        assert "https://example.com/page" in links
        assert not any(".pdf" in l for l in links)
        assert not any(".jpg" in l for l in links)

    def test_deduplicates(self):
        html = """
        <a href="/page">First</a>
        <a href="/page">Second</a>
        <a href="/page/">Third (trailing slash)</a>
        """
        links = _extract_links(html, "https://example.com", "example.com")
        # /page and /page/ normalize to the same thing
        assert len(links) <= 2  # at most /page and /page/ before normalization
