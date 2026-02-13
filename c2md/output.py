"""File writers: markdown, screenshot, PDF, archive."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path

from PIL import Image


def save_markdown(content: str, output_path: Path) -> None:
    """Save markdown content to file."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(content, encoding="utf-8")


def save_screenshot(
    screenshot_bytes: bytes,
    output_path: Path,
    quality: int = 85,
    max_width: int | None = None,
) -> int:
    """Save screenshot bytes to file, optionally compressing.

    Returns file size in bytes.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    img = Image.open(BytesIO(screenshot_bytes))

    if max_width and img.width > max_width:
        ratio = max_width / img.width
        new_height = int(img.height * ratio)
        img = img.resize((max_width, new_height), Image.Resampling.LANCZOS)

    suffix = output_path.suffix.lower()
    if suffix in (".jpg", ".jpeg"):
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")
        img.save(output_path, "JPEG", quality=quality, optimize=True)
    else:
        img.save(output_path, "PNG", optimize=True)

    return output_path.stat().st_size


def save_pdf(pdf_bytes: bytes, output_path: Path) -> None:
    """Save PDF bytes to file."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(pdf_bytes)


def save_archive(
    markdown: str,
    output_dir: Path,
    screenshot_bytes: bytes | None = None,
    pdf_bytes: bytes | None = None,
    metadata_bytes: bytes | None = None,
    references: str | None = None,
    screenshot_quality: int = 85,
) -> list[Path]:
    """Save all formats into a directory. Returns list of saved paths."""
    output_dir.mkdir(parents=True, exist_ok=True)
    saved: list[Path] = []

    # Markdown
    md_path = output_dir / "article.md"
    md_path.write_text(markdown, encoding="utf-8")
    saved.append(md_path)

    # References
    if references:
        refs_path = output_dir / "references.md"
        refs_path.write_text(references, encoding="utf-8")
        saved.append(refs_path)

    # Screenshot
    if screenshot_bytes:
        screenshot_path = output_dir / "screenshot.png"
        save_screenshot(screenshot_bytes, screenshot_path, quality=screenshot_quality)
        saved.append(screenshot_path)

    # PDF
    if pdf_bytes:
        pdf_path = output_dir / "article.pdf"
        pdf_path.write_bytes(pdf_bytes)
        saved.append(pdf_path)

    # Metadata
    if metadata_bytes:
        meta_path = output_dir / "metadata.json"
        meta_path.write_bytes(metadata_bytes)
        saved.append(meta_path)

    return saved
