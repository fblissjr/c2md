"""Image download, compress, and base64 embed."""

from __future__ import annotations

import base64
import hashlib
import re
from io import BytesIO
from pathlib import Path

import httpx
from PIL import Image


def find_image_urls(markdown: str) -> list[str]:
    """Extract image URLs from markdown text."""
    pattern = r"!\[[^\]]*\]\(([^)]+)\)"
    urls = re.findall(pattern, markdown)
    return [u for u in urls if u.startswith("http")]


def download_and_compress_images(
    image_urls: list[str],
    output_dir: Path,
    quality: int = 80,
    max_width: int = 800,
) -> dict[str, Path]:
    """Download images and compress them locally.

    Returns:
        dict mapping original URLs to local file paths
    """
    if not image_urls:
        return {}

    output_dir.mkdir(parents=True, exist_ok=True)
    url_to_path: dict[str, Path] = {}

    with httpx.Client(timeout=10, follow_redirects=True) as client:
        for src in image_urls:
            try:
                url_hash = hashlib.md5(src.encode()).hexdigest()[:12]
                local_path = output_dir / f"{url_hash}.jpg"

                if local_path.exists():
                    url_to_path[src] = local_path
                    continue

                resp = client.get(src)
                resp.raise_for_status()

                img = Image.open(BytesIO(resp.content))
                if img.mode in ("RGBA", "P"):
                    img = img.convert("RGB")

                if max_width and img.width > max_width:
                    ratio = max_width / img.width
                    new_height = int(img.height * ratio)
                    img = img.resize((max_width, new_height), Image.Resampling.LANCZOS)

                img.save(local_path, "JPEG", quality=quality, optimize=True)
                url_to_path[src] = local_path

            except Exception:
                continue

    return url_to_path


def download_images_as_base64(
    image_urls: list[str],
    quality: int = 80,
    max_width: int = 800,
) -> dict[str, str]:
    """Download images and return as base64 data URIs.

    Returns:
        dict mapping original URLs to base64 data URIs
    """
    if not image_urls:
        return {}

    url_to_base64: dict[str, str] = {}

    with httpx.Client(timeout=10, follow_redirects=True) as client:
        for src in image_urls:
            try:
                resp = client.get(src)
                resp.raise_for_status()

                img = Image.open(BytesIO(resp.content))
                if img.mode in ("RGBA", "P"):
                    img = img.convert("RGB")

                if max_width and img.width > max_width:
                    ratio = max_width / img.width
                    new_height = int(img.height * ratio)
                    img = img.resize((max_width, new_height), Image.Resampling.LANCZOS)

                buffer = BytesIO()
                img.save(buffer, "JPEG", quality=quality, optimize=True)
                b64 = base64.b64encode(buffer.getvalue()).decode("utf-8")
                url_to_base64[src] = f"data:image/jpeg;base64,{b64}"

            except Exception:
                continue

    return url_to_base64


def embed_images_in_markdown(markdown: str, url_to_base64: dict[str, str]) -> str:
    """Replace image URLs in markdown with base64 data URIs."""
    result = markdown
    for url, data_uri in url_to_base64.items():
        result = result.replace(url, data_uri)
    return result
