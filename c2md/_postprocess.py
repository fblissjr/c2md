"""Markdown post-processing pipeline.

Ported from c4md.processors -- fixes common HTML-to-markdown conversion artifacts.
"""

from __future__ import annotations

import re


def fix_heading_linebreaks(markdown: str) -> str:
    """Collapse single-word lines that follow an orphaned heading marker.

    Fixes Webflow-style animated headings where each word is wrapped in a
    separate <div>, causing converters to render:
        #
        Complete
        Guide
        to
    Instead of:
        # Complete Guide to
    """
    lines = markdown.split("\n")
    result = []
    i = 0

    while i < len(lines):
        line = lines[i]

        heading_match = re.match(r"^(#{1,6})\s*$", line)
        if heading_match:
            level = heading_match.group(1)

            j = i + 1
            fragments = []
            while j < len(lines):
                next_line = lines[j].strip()
                if (
                    not next_line
                    or next_line.startswith("#")
                    or next_line.startswith("-")
                    or next_line.startswith("*")
                    or next_line.startswith("[")
                    or next_line.startswith("|")
                    or next_line.startswith(">")
                    or next_line.startswith("```")
                    or len(next_line.split()) > 3
                ):
                    break
                fragments.append(next_line)
                j += 1

            if fragments:
                result.append(f"{level} {' '.join(fragments)}")
                i = j
                continue

        result.append(line)
        i += 1

    return "\n".join(result)


def fix_citation_duplication(markdown: str) -> str:
    r"""Fix citation markers that duplicate adjacent link text.

    Pattern: "text[N]text" where both text occurrences match -> "text[N]"
    """
    pattern = r"([\w][^\[\]]{0,60}?)\s*\[(\d+)\]\s*\1"
    return re.sub(pattern, r"\1[\2]", markdown)


def strip_empty_image_links(markdown: str) -> str:
    """Remove empty markdown image links like [](url) and ![](url)."""
    markdown = re.sub(r"!\[\]\([^)]+\)\s*", "", markdown)
    markdown = re.sub(r"(?<!!)\[\]\([^)]+\)\s*", "", markdown)
    return markdown


def collapse_blank_lines(markdown: str) -> str:
    """Collapse 3+ consecutive blank lines down to 2."""
    return re.sub(r"\n{4,}", "\n\n\n", markdown)


def clean_markdown(markdown: str) -> str:
    """Run all markdown post-processing fixups.

    Order matters:
    1. Fix heading linebreaks (structural)
    2. Fix citation duplication (content)
    3. Strip empty image links (cleanup)
    4. Collapse excess blank lines (formatting)
    """
    if not markdown:
        return markdown

    markdown = fix_heading_linebreaks(markdown)
    markdown = fix_citation_duplication(markdown)
    markdown = strip_empty_image_links(markdown)
    markdown = collapse_blank_lines(markdown)
    return markdown.strip()
