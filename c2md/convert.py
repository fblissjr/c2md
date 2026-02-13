"""HTML -> markdown conversion via readability-lxml + markdownify."""

from __future__ import annotations

from bs4 import BeautifulSoup
from markdownify import markdownify as md
from readability import Document


def html_to_markdown(
    html: str,
    url: str = "",
    strip_boilerplate: bool = True,
    selector: str | None = None,
) -> str:
    """Convert HTML to clean markdown.

    Pipeline:
    1. readability-lxml extracts main content (if strip_boilerplate)
    2. OR BeautifulSoup extracts by CSS selector (if selector)
    3. markdownify converts HTML -> markdown
    """
    if not html or not html.strip():
        return ""

    content_html = html

    if selector:
        # CSS selector takes priority over readability
        soup = BeautifulSoup(html, "lxml")
        selected = soup.select(selector)
        if selected:
            content_html = "\n".join(str(el) for el in selected)
        # If selector finds nothing, fall through to readability
        elif strip_boilerplate:
            content_html = _readability_extract(html, url)
    elif strip_boilerplate:
        content_html = _readability_extract(html, url)

    # Strip unwanted tags via BeautifulSoup before conversion
    # (markdownify doesn't allow both strip and convert simultaneously)
    soup = BeautifulSoup(content_html, "lxml")
    for tag_name in ("script", "style", "nav", "footer", "header", "aside"):
        for tag in soup.find_all(tag_name):
            tag.decompose()
    content_html = str(soup)

    markdown = md(
        content_html,
        heading_style="ATX",
        bullets="-",
    )

    return _clean_output(markdown)


def convert_file(path: str) -> str:
    """Convert file (PDF, DOCX, XLSX, etc.) to markdown via markitdown."""
    from markitdown import MarkItDown

    converter = MarkItDown()
    result = converter.convert(path)
    return result.text_content


def _readability_extract(html: str, url: str = "") -> str:
    """Extract main content using Mozilla's Readability algorithm."""
    doc = Document(html, url=url)
    return doc.summary()


def _clean_output(markdown: str) -> str:
    """Clean up markdownify output artifacts."""
    import re

    # Collapse runs of 3+ blank lines to 2
    markdown = re.sub(r"\n{4,}", "\n\n\n", markdown)

    # Remove trailing whitespace per line
    lines = [line.rstrip() for line in markdown.split("\n")]
    markdown = "\n".join(lines)

    return markdown.strip()
