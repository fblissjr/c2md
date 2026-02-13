"""Link-to-reference citation system.

Converts inline markdown links to numbered references:
    [text](url)  ->  text [1]
    ...
    ## References
    [1] url
"""

from __future__ import annotations

import re


def add_citations(markdown: str) -> tuple[str, str]:
    """Convert inline links to numbered citations.

    Returns:
        (markdown_with_citations, references_block)
    """
    if not markdown:
        return "", ""

    urls: dict[str, int] = {}
    counter = 0

    def replace_link(match: re.Match) -> str:
        nonlocal counter
        text = match.group(1)
        url = match.group(2)

        # Skip image links (handled separately) and anchors
        if url.startswith("#"):
            return match.group(0)

        if url not in urls:
            counter += 1
            urls[url] = counter

        ref_num = urls[url]
        # Return text with citation number -- avoid duplicating text
        if text.strip():
            return f"{text} [{ref_num}]"
        return f"[{ref_num}]"

    # Match [text](url) but NOT ![text](url) (images)
    pattern = r"(?<!!)\[([^\]]*)\]\(([^)]+)\)"
    cited = re.sub(pattern, replace_link, markdown)

    if not urls:
        return markdown, ""

    # Build references block
    lines = ["", "## References", ""]
    for url, num in sorted(urls.items(), key=lambda x: x[1]):
        lines.append(f"[{num}] {url}")

    references = "\n".join(lines)
    return cited, references
