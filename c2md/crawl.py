"""Deep link BFS crawler."""

from __future__ import annotations

import fnmatch
import re
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from c2md.fetch import BrowserSession, FetchResult


async def deep_crawl(
    start_url: str,
    session: BrowserSession,
    max_pages: int = 10,
    url_pattern: str | None = None,
    screenshot: bool = False,
    pdf: bool = False,
) -> list[FetchResult]:
    """Follow links 1 level deep from start_url. Same-domain only.

    Args:
        start_url: The seed URL to crawl
        session: An active BrowserSession
        max_pages: Maximum number of pages to fetch (including start)
        url_pattern: Glob pattern to filter discovered URLs
        screenshot: Capture screenshots for each page
        pdf: Capture PDFs for each page
    """
    parsed_start = urlparse(start_url)
    base_domain = parsed_start.netloc

    # Fetch the start page
    start_result = await session.fetch(start_url, screenshot=screenshot, pdf=pdf)
    results = [start_result]
    visited = {_normalize_url(start_url)}

    # Extract links from start page
    discovered = _extract_links(start_result.html, start_url, base_domain)

    # Filter by pattern if specified
    if url_pattern:
        discovered = [u for u in discovered if fnmatch.fnmatch(u, url_pattern)]

    # BFS one level deep
    for url in discovered:
        if len(results) >= max_pages:
            break

        normalized = _normalize_url(url)
        if normalized in visited:
            continue
        visited.add(normalized)

        try:
            result = await session.fetch(url, screenshot=screenshot, pdf=pdf)
            if result.status < 400:
                results.append(result)
        except Exception:
            continue

    return results


def _extract_links(html: str, base_url: str, base_domain: str) -> list[str]:
    """Extract same-domain links from HTML."""
    soup = BeautifulSoup(html, "lxml")
    links = []

    for a in soup.find_all("a", href=True):
        href = a["href"]

        # Skip fragments, javascript, mailto
        if href.startswith(("#", "javascript:", "mailto:", "tel:")):
            continue

        # Resolve relative URLs
        absolute = urljoin(base_url, href)
        parsed = urlparse(absolute)

        # Same domain only
        if parsed.netloc != base_domain:
            continue

        # Skip non-HTTP schemes
        if parsed.scheme not in ("http", "https"):
            continue

        # Skip common non-page extensions
        if re.search(r"\.(jpg|jpeg|png|gif|svg|pdf|zip|tar|gz|css|js|xml)$", parsed.path, re.I):
            continue

        links.append(absolute)

    # Deduplicate while preserving order
    seen = set()
    unique = []
    for link in links:
        normalized = _normalize_url(link)
        if normalized not in seen:
            seen.add(normalized)
            unique.append(link)

    return unique


def _normalize_url(url: str) -> str:
    """Normalize URL for dedup (strip fragment, trailing slash)."""
    parsed = urlparse(url)
    path = parsed.path.rstrip("/") or "/"
    return f"{parsed.scheme}://{parsed.netloc}{path}"
