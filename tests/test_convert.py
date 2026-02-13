"""Tests for c2md.convert module."""

from c2md.convert import html_to_markdown, _readability_extract, _clean_output


class TestHtmlToMarkdown:
    def test_basic_html(self):
        html = "<html><body><h1>Title</h1><p>Hello world.</p></body></html>"
        result = html_to_markdown(html, strip_boilerplate=False)
        assert "Title" in result
        assert "Hello world." in result

    def test_empty_html(self):
        assert html_to_markdown("") == ""
        assert html_to_markdown("   ") == ""

    def test_heading_levels(self):
        html = "<h1>H1</h1><h2>H2</h2><h3>H3</h3>"
        result = html_to_markdown(html, strip_boilerplate=False)
        assert "# H1" in result
        assert "## H2" in result
        assert "### H3" in result

    def test_strips_nav_footer(self):
        html = """
        <html><body>
            <nav><a href="/">Home</a></nav>
            <article><p>Main content</p></article>
            <footer><p>Copyright 2026</p></footer>
        </body></html>
        """
        result = html_to_markdown(html, strip_boilerplate=False)
        assert "Main content" in result
        # nav/footer should be stripped by markdownify strip param
        assert "Copyright 2026" not in result

    def test_css_selector(self):
        html = """
        <html><body>
            <div class="sidebar">Sidebar stuff</div>
            <article class="post">Important content here</article>
        </body></html>
        """
        result = html_to_markdown(html, selector="article.post", strip_boilerplate=False)
        assert "Important content" in result

    def test_links_preserved(self):
        html = '<p>Visit <a href="https://example.com">Example</a></p>'
        result = html_to_markdown(html, strip_boilerplate=False)
        assert "Example" in result
        assert "https://example.com" in result

    def test_code_blocks(self):
        html = "<pre><code>def hello():\n    print('hi')</code></pre>"
        result = html_to_markdown(html, strip_boilerplate=False)
        assert "def hello():" in result

    def test_raw_mode_no_readability(self):
        """With strip_boilerplate=False, all content should pass through."""
        html = "<html><body><p>All content.</p></body></html>"
        result = html_to_markdown(html, strip_boilerplate=False)
        assert "All content." in result


class TestReadabilityExtract:
    def test_extracts_main_content(self):
        html = """
        <html><body>
            <nav><ul><li>Menu 1</li><li>Menu 2</li></ul></nav>
            <article>
                <h1>Article Title</h1>
                <p>This is the main article content with enough text
                to be recognized as the primary content by readability.
                It needs to be reasonably long to be identified.</p>
                <p>Another paragraph of real content that helps readability
                determine this is the main content area of the page.</p>
            </article>
            <aside>Related links sidebar</aside>
        </body></html>
        """
        result = _readability_extract(html)
        assert "Article Title" in result or "article content" in result


class TestCleanOutput:
    def test_collapses_blank_lines(self):
        md = "A\n\n\n\n\nB"
        result = _clean_output(md)
        assert "\n\n\n\n" not in result

    def test_strips_trailing_whitespace(self):
        md = "Line with trailing spaces   \nAnother line  "
        result = _clean_output(md)
        for line in result.split("\n"):
            assert line == line.rstrip()
