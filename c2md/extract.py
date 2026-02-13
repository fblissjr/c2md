"""Metadata, dates, link analysis."""

from __future__ import annotations

import re
from collections import Counter
from datetime import datetime
from urllib.parse import urlparse

from bs4 import BeautifulSoup


def extract_metadata(html: str, url: str) -> dict:
    """Extract article metadata from HTML.

    Extracts:
    - Basic info: title, description, author, published_date
    - Content stats: word_count, reading_time_minutes
    - Link analysis: internal/external link counts, top external domains
    - Media: image_count, video_count
    - SEO: canonical_url, og tags
    """
    soup = BeautifulSoup(html, "lxml")
    parsed_url = urlparse(url)
    base_domain = parsed_url.netloc

    # Basic info from meta tags
    title = _get_meta(soup, "og:title") or _get_title(soup)
    description = _get_meta(soup, "og:description") or _get_meta(soup, "description")
    author = _get_meta(soup, "author") or _get_meta(soup, "article:author")
    published_date = extract_date_from_html(soup)

    # Content stats (from visible text)
    text = soup.get_text(separator=" ", strip=True)
    words = text.split()
    word_count = len(words)
    reading_time_minutes = max(1, round(word_count / 238))

    # Link analysis
    all_links = soup.find_all("a", href=True)
    internal_links = []
    external_links = []
    for a in all_links:
        href = a["href"]
        if href.startswith(("#", "javascript:", "mailto:", "tel:")):
            continue
        link_parsed = urlparse(href)
        if link_parsed.netloc and link_parsed.netloc != base_domain:
            external_links.append(href)
        else:
            internal_links.append(href)

    # Top external domains
    ext_domains = []
    for href in external_links:
        try:
            domain = urlparse(href).netloc
            if domain:
                ext_domains.append(domain)
        except Exception:
            pass
    top_domains = [d for d, _ in Counter(ext_domains).most_common(10)]

    # Media
    images = soup.find_all("img")
    videos = soup.find_all(["video", "iframe"])

    # SEO / OG
    canonical_url = ""
    canonical_tag = soup.find("link", rel="canonical")
    if canonical_tag:
        canonical_url = canonical_tag.get("href", "")
    og_image = _get_meta(soup, "og:image") or ""
    og_type = _get_meta(soup, "og:type") or ""
    og_site_name = _get_meta(soup, "og:site_name") or ""

    return {
        "url": url,
        "title": title or "",
        "description": description or "",
        "author": author or "",
        "published_date": published_date,
        "word_count": word_count,
        "reading_time_minutes": reading_time_minutes,
        "internal_link_count": len(internal_links),
        "external_link_count": len(external_links),
        "top_external_domains": top_domains,
        "image_count": len(images),
        "video_count": len(videos),
        "canonical_url": canonical_url,
        "og_image": og_image,
        "og_type": og_type,
        "og_site_name": og_site_name,
    }


def extract_date_from_html(soup: BeautifulSoup) -> str | None:
    """Extract publication date from HTML meta tags and content.

    Tries in order:
    1. Standard metadata fields
    2. Date patterns in visible text (first 1000 chars)

    Returns ISO date (YYYY-MM-DD) or None.
    """
    # Strategy 1: meta tags
    date_meta_names = [
        "date", "published", "datePublished", "article:published_time",
        "og:article:published_time", "pubdate", "publish_date",
        "DC.date.issued", "sailthru.date",
    ]
    for name in date_meta_names:
        content = _get_meta(soup, name)
        if content:
            parsed = _parse_date_string(content)
            if parsed:
                return parsed

    # Also check <time> elements
    time_el = soup.find("time", datetime=True)
    if time_el:
        parsed = _parse_date_string(time_el["datetime"])
        if parsed:
            return parsed

    # Strategy 2: date patterns in visible text
    text = soup.get_text(separator=" ", strip=True)[:1000]
    return _find_date_in_text(text)


def extract_date_from_markdown(markdown: str) -> str | None:
    """Extract a date from markdown text content."""
    if not markdown:
        return None
    return _find_date_in_text(markdown[:1000])


def sort_results_by_date(
    results: list[dict],
    descending: bool = True,
) -> list[dict]:
    """Sort results by extracted date. Results without dates go to end."""
    def get_sort_key(item: dict) -> tuple[str, str]:
        date = item.get("published_date")
        if date is None:
            return ("9999-99-99" if descending else "0000-00-00", item.get("url", ""))
        return (date, item.get("url", ""))

    return sorted(results, key=get_sort_key, reverse=descending)


# --- Private helpers ---


def _get_meta(soup: BeautifulSoup, name: str) -> str | None:
    """Get content from a meta tag by name or property."""
    tag = soup.find("meta", attrs={"name": name})
    if tag and tag.get("content"):
        return tag["content"]
    tag = soup.find("meta", attrs={"property": name})
    if tag and tag.get("content"):
        return tag["content"]
    return None


def _get_title(soup: BeautifulSoup) -> str:
    """Get page title."""
    title_tag = soup.find("title")
    return title_tag.get_text(strip=True) if title_tag else ""


def _parse_date_string(date_str: str) -> str | None:
    """Try to parse a date string into YYYY-MM-DD."""
    if not date_str:
        return None
    try:
        if "T" in date_str:
            dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
            return dt.strftime("%Y-%m-%d")
        # Try YYYY-MM-DD directly
        if re.match(r"^\d{4}-\d{2}-\d{2}", date_str):
            return date_str[:10]
    except (ValueError, TypeError):
        pass
    return None


def _find_date_in_text(text: str) -> str | None:
    """Find a date pattern in text content."""
    patterns = [
        (r"(\d{4}-\d{2}-\d{2})", "%Y-%m-%d"),
        (
            r"((?:January|February|March|April|May|June|July|August|September|"
            r"October|November|December|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|"
            r"Oct|Nov|Dec)[a-z]*\.?\s+\d{1,2},?\s+\d{4})",
            None,
        ),
        (
            r"(\d{1,2}\s+(?:January|February|March|April|May|June|July|August|"
            r"September|October|November|December)\s+\d{4})",
            None,
        ),
    ]

    for pattern, fmt in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            date_str = match.group(1)
            if fmt:
                try:
                    dt = datetime.strptime(date_str, fmt)
                    return dt.strftime("%Y-%m-%d")
                except ValueError:
                    pass
            else:
                # Try multiple date formats
                cleaned = date_str.replace(",", "").replace(".", "")
                for date_fmt in ("%B %d %Y", "%b %d %Y", "%d %B %Y"):
                    try:
                        dt = datetime.strptime(cleaned, date_fmt)
                        return dt.strftime("%Y-%m-%d")
                    except ValueError:
                        continue

    return None
