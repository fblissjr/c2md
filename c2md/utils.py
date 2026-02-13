"""Utility functions for c2md."""

import re
from urllib.parse import urlparse


def url_to_slug(url: str) -> str:
    """Generate a filesystem-safe filename from a URL."""
    parsed = urlparse(url)
    slug = parsed.netloc + parsed.path
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", slug)
    slug = re.sub(r"_+", "_", slug).strip("_")
    return slug[:100] if slug else "page"
