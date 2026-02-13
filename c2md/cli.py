"""c2md CLI - Click command definitions and main entry point."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import click
import orjson
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

from c2md.citations import add_citations
from c2md.convert import convert_file, html_to_markdown
from c2md.extract import extract_date_from_html, extract_metadata, sort_results_by_date
from c2md.media import (
    download_and_compress_images,
    download_images_as_base64,
    embed_images_in_markdown,
    find_image_urls,
)
from c2md.output import save_archive, save_markdown, save_pdf, save_screenshot
from c2md.utils import url_to_slug

console = Console(stderr=True)

# Markdown post-processing (ported from c4md.processors)
from c2md._postprocess import clean_markdown  # noqa: E402


@click.command()
@click.argument("source")
@click.option(
    "-m", "--mode",
    type=click.Choice(["markdown", "screenshot", "pdf", "metadata", "archive"]),
    default="markdown",
    help="Output mode (default: markdown)",
)
@click.option("-o", "--output", "output_path", type=click.Path(), default=None,
              help="Output file or directory. Omit for stdout.")
@click.option("-f", "--filename", default=None, help="Custom filename (no extension)")
@click.option("--raw", is_flag=True, help="Disable boilerplate removal (readability)")
@click.option("--selector", default=None, help="CSS selector for content targeting")
@click.option("--browser", is_flag=True,
              help="Force playwright browser (for JS-rendered sites)")
@click.option("--no-headless", is_flag=True, help="Show browser window")
@click.option("-v", "--verbose", is_flag=True, help="Verbose progress output")
@click.option("--timeout", default=30, help="Page timeout in seconds")
@click.option("--refs", is_flag=True, help="Add numbered citation references")
@click.option("--deep", is_flag=True, help="Deep crawl: follow links 1 level deep")
@click.option("--max-pages", default=10, help="Max pages in deep mode")
@click.option("--sort-by-date", is_flag=True, help="Sort results by date (newest first)")
@click.option("--limit", default=None, type=int, help="Limit to N results")
@click.option("--url-pattern", default=None,
              help="Filter deep crawl URLs (glob pattern)")
@click.option("--no-images", is_flag=True, help="Strip images from markdown")
@click.option("--embed-images", is_flag=True,
              help="Embed images as base64 in markdown")
@click.option("--download-images", is_flag=True,
              help="Download and compress images locally")
@click.option("--image-width", default=800, type=int,
              help="Max width for downloaded/embedded images")
@click.option("--screenshot-quality", default=85, type=click.IntRange(1, 100),
              help="JPEG quality for screenshots")
@click.option("--screenshot-width", default=None, type=int,
              help="Max screenshot width (resize if larger)")
@click.option("--dedupe", is_flag=True,
              help="Deduplicate deep crawl results by content fingerprint")
def main(
    source: str,
    mode: str,
    output_path: str | None,
    filename: str | None,
    raw: bool,
    selector: str | None,
    browser: bool,
    no_headless: bool,
    verbose: bool,
    timeout: int,
    refs: bool,
    deep: bool,
    max_pages: int,
    sort_by_date: bool,
    limit: int | None,
    url_pattern: str | None,
    no_images: bool,
    embed_images: bool,
    download_images: bool,
    image_width: int,
    screenshot_quality: int,
    screenshot_width: int | None,
    dedupe: bool,
):
    """Convert URLs and files to clean markdown.

    SOURCE can be a URL or a local file path (PDF, DOCX, XLSX, HTML, etc.).

    \b
    Examples:
        c2md https://example.com/article          # markdown to stdout
        c2md https://example.com -o out/           # save to file
        c2md https://example.com --mode screenshot  # screenshot
        c2md https://example.com --browser         # force JS rendering
        c2md https://example.com --raw             # no boilerplate removal
        c2md https://example.com --refs            # add citation references
        c2md https://example.com --deep            # follow links
        c2md report.pdf                            # convert local file
    """
    # Detect if source is a local file
    source_path = Path(source)
    is_file = source_path.exists() and source_path.is_file()
    is_url = source.startswith(("http://", "https://"))

    if not is_file and not is_url:
        raise click.ClickException(
            f"Source must be a URL (http/https) or existing file: {source}"
        )

    # File conversion is a special fast path
    if is_file:
        _handle_file(source_path, output_path, verbose)
        return

    # URL processing
    needs_browser = (
        browser
        or mode in ("screenshot", "pdf", "archive")
        or deep
    )

    slug = filename or url_to_slug(source)

    if verbose:
        mode_label = mode + (" (deep)" if deep else "")
        if not raw:
            mode_label += " [readability]"
        console.print(Panel(
            f"[bold]c2md - Content to Markdown[/bold]\n{source}\nMode: {mode_label}",
            expand=False,
        ))

    if deep:
        results = _run_deep_crawl(
            source, needs_browser, no_headless, timeout, mode, slug,
            max_pages, url_pattern, raw, selector, verbose,
            screenshot_quality, screenshot_width, dedupe,
            sort_by_date, limit, refs, no_images, embed_images,
            download_images, image_width, output_path,
        )
        return

    # Single page
    with Progress(
        SpinnerColumn(), TextColumn("[progress.description]{task.description}"),
        console=console, transient=True,
    ) as progress:
        if verbose:
            progress.add_task(description="Fetching...", total=None)

        fetch_result = asyncio.run(
            _fetch_single(source, needs_browser, no_headless, timeout, mode)
        )

    _process_result(
        fetch_result, source, slug, mode, raw, selector, refs,
        no_images, embed_images, download_images, image_width,
        screenshot_quality, screenshot_width, output_path, verbose,
    )


def _handle_file(source_path: Path, output_path: str | None, verbose: bool) -> None:
    """Handle local file conversion via markitdown."""
    if verbose:
        console.print(f"[dim]Converting file: {source_path}[/dim]")

    markdown = convert_file(str(source_path))

    if output_path:
        out = Path(output_path)
        if out.is_dir() or output_path.endswith("/"):
            out.mkdir(parents=True, exist_ok=True)
            out = out / f"{source_path.stem}.md"
        save_markdown(markdown, out)
        console.print(f"[green]Saved:[/green] {out}")
    else:
        click.echo(markdown)


async def _fetch_single(
    url: str, needs_browser: bool, no_headless: bool,
    timeout: int, mode: str,
):
    """Fetch a single URL."""
    if needs_browser:
        from c2md.fetch import BrowserSession
        async with BrowserSession(
            headless=not no_headless, timeout=timeout,
        ) as session:
            return await session.fetch(
                url,
                screenshot=(mode in ("screenshot", "archive")),
                pdf=(mode in ("pdf", "archive")),
            )
    else:
        import httpx
        from c2md.fetch import fetch_static
        try:
            return await fetch_static(url, timeout=timeout)
        except httpx.ConnectError as e:
            if "CERTIFICATE_VERIFY_FAILED" in str(e):
                console.print(
                    "[yellow]SSL verification failed, retrying without verification[/yellow]",
                )
                return await fetch_static(url, timeout=timeout, verify_ssl=False)
            raise


def _process_result(
    result, url: str, slug: str, mode: str, raw: bool,
    selector: str | None, refs: bool, no_images: bool,
    embed_images: bool, download_images_flag: bool, image_width: int,
    screenshot_quality: int, screenshot_width: int | None,
    output_path: str | None, verbose: bool,
) -> None:
    """Process a single FetchResult into the desired output."""
    from bs4 import BeautifulSoup

    if mode == "markdown":
        markdown = html_to_markdown(
            result.html, url=url,
            strip_boilerplate=not raw,
            selector=selector,
        )
        markdown = clean_markdown(markdown)

        if no_images:
            import re
            markdown = re.sub(r"!\[[^\]]*\]\([^)]+\)\s*", "", markdown)

        references = ""
        if refs:
            markdown, references = add_citations(markdown)

        if embed_images:
            image_urls = find_image_urls(markdown)
            if image_urls:
                if verbose:
                    console.print(f"[dim]Embedding {len(image_urls)} images...[/dim]")
                url_to_b64 = download_images_as_base64(image_urls, max_width=image_width)
                markdown = embed_images_in_markdown(markdown, url_to_b64)
                if references:
                    references = embed_images_in_markdown(references, url_to_b64)

        elif download_images_flag and output_path:
            image_urls = find_image_urls(markdown)
            if image_urls:
                out_dir = Path(output_path) if Path(output_path).is_dir() else Path(output_path).parent
                images_dir = out_dir / f"{slug}_images"
                url_to_path = download_and_compress_images(
                    image_urls, images_dir, max_width=image_width,
                )
                if url_to_path and verbose:
                    total_size = sum(p.stat().st_size for p in url_to_path.values())
                    console.print(
                        f"[green]Downloaded:[/green] {len(url_to_path)} images "
                        f"({total_size // 1024}KB) to {images_dir}/",
                    )

        # Output
        if output_path:
            out = Path(output_path)
            if out.is_dir() or output_path.endswith("/"):
                out.mkdir(parents=True, exist_ok=True)
                out = out / f"{slug}.md"
            save_markdown(markdown, out)
            console.print(f"[green]Saved:[/green] {out}")
            if references:
                refs_path = out.with_name(f"{out.stem}_refs.md")
                save_markdown(references, refs_path)
                console.print(f"[green]Saved:[/green] {refs_path}")
        else:
            output = markdown
            if references:
                output = f"{markdown}\n{references}"
            click.echo(output)

    elif mode == "screenshot":
        if not result.screenshot:
            raise click.ClickException("No screenshot data (use --browser for JS sites)")
        if output_path:
            out = Path(output_path)
            if out.is_dir() or output_path.endswith("/"):
                out.mkdir(parents=True, exist_ok=True)
                ext = ".jpg" if screenshot_width else ".png"
                out = out / f"{slug}{ext}"
            size = save_screenshot(
                result.screenshot, out,
                quality=screenshot_quality, max_width=screenshot_width,
            )
            size_str = f" ({size // 1024}KB)" if verbose else ""
            console.print(f"[green]Saved:[/green] {out}{size_str}")
        else:
            raise click.ClickException("Screenshot mode requires -o/--output")

    elif mode == "pdf":
        if not result.pdf:
            raise click.ClickException("No PDF data (use --browser for JS sites)")
        if output_path:
            out = Path(output_path)
            if out.is_dir() or output_path.endswith("/"):
                out.mkdir(parents=True, exist_ok=True)
                out = out / f"{slug}.pdf"
            save_pdf(result.pdf, out)
            console.print(f"[green]Saved:[/green] {out}")
        else:
            raise click.ClickException("PDF mode requires -o/--output")

    elif mode == "metadata":
        metadata = extract_metadata(result.html, url)
        meta_json = orjson.dumps(metadata, option=orjson.OPT_INDENT_2)
        if output_path:
            out = Path(output_path)
            if out.is_dir() or output_path.endswith("/"):
                out.mkdir(parents=True, exist_ok=True)
                out = out / f"{slug}_meta.json"
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_bytes(meta_json)
            console.print(f"[green]Saved:[/green] {out}")
        else:
            click.echo(meta_json.decode())

    elif mode == "archive":
        if not output_path:
            raise click.ClickException("Archive mode requires -o/--output")

        out_dir = Path(output_path)
        if not output_path.endswith("/"):
            out_dir = out_dir / slug

        markdown = html_to_markdown(
            result.html, url=url,
            strip_boilerplate=not raw, selector=selector,
        )
        markdown = clean_markdown(markdown)

        references = ""
        if refs:
            markdown, references = add_citations(markdown)

        metadata = extract_metadata(result.html, url)
        meta_bytes = orjson.dumps(metadata, option=orjson.OPT_INDENT_2)

        saved = save_archive(
            markdown, out_dir,
            screenshot_bytes=result.screenshot,
            pdf_bytes=result.pdf,
            metadata_bytes=meta_bytes,
            references=references or None,
            screenshot_quality=screenshot_quality,
        )
        console.print(f"[green]Archive created:[/green] {out_dir}/")
        for f in saved:
            console.print(f"  [dim]{f.name}[/dim]")


def _run_deep_crawl(
    url: str, needs_browser: bool, no_headless: bool, timeout: int,
    mode: str, slug: str, max_pages: int, url_pattern: str | None,
    raw: bool, selector: str | None, verbose: bool,
    screenshot_quality: int, screenshot_width: int | None,
    dedupe: bool, sort_by_date: bool, limit: int | None,
    refs: bool, no_images: bool, embed_images: bool,
    download_images_flag: bool, image_width: int,
    output_path: str | None,
) -> None:
    """Run a deep crawl and process all results."""
    import xxhash
    from c2md.crawl import deep_crawl
    from c2md.fetch import BrowserSession

    async def _crawl():
        async with BrowserSession(
            headless=not no_headless, timeout=timeout,
        ) as session:
            return await deep_crawl(
                url, session,
                max_pages=max_pages,
                url_pattern=url_pattern,
                screenshot=(mode in ("screenshot", "archive")),
                pdf=(mode in ("pdf", "archive")),
            )

    with Progress(
        SpinnerColumn(), TextColumn("[progress.description]{task.description}"),
        console=console, transient=True,
    ) as progress:
        if verbose:
            progress.add_task(
                description=f"Deep crawling (max {max_pages} pages)...", total=None,
            )
        results = asyncio.run(_crawl())

    if verbose:
        console.print(f"[dim]Crawled {len(results)} pages[/dim]")

    # Deduplicate
    if dedupe and len(results) > 1:
        before = len(results)
        seen = set()
        unique = []
        for r in results:
            markdown = html_to_markdown(r.html, r.url, strip_boilerplate=not raw)
            fp = xxhash.xxh64(markdown.encode()).hexdigest()
            if fp not in seen:
                seen.add(fp)
                unique.append(r)
        results = unique
        if verbose and len(results) < before:
            console.print(f"[dim]Deduplication: {before} -> {len(results)} unique[/dim]")

    # Sort by date
    if sort_by_date and len(results) > 1:
        from bs4 import BeautifulSoup
        from c2md.extract import extract_date_from_html

        tagged = []
        for r in results:
            soup = BeautifulSoup(r.html, "lxml")
            date = extract_date_from_html(soup)
            tagged.append({"result": r, "published_date": date, "url": r.url})

        tagged = sort_results_by_date(tagged, descending=True)
        results = [t["result"] for t in tagged]

        if verbose:
            for t in tagged[:5]:
                d = t["published_date"] or "no date"
                console.print(f"  [dim]{d}: {t['url']}[/dim]")
            if len(tagged) > 5:
                console.print(f"  [dim]... and {len(tagged) - 5} more[/dim]")

    # Apply limit
    if limit and len(results) > limit:
        if verbose:
            console.print(f"[dim]Limiting to {limit} results[/dim]")
        results = results[:limit]

    # Process each result
    if not output_path:
        output_path = "./output"

    for i, result in enumerate(results):
        page_slug = url_to_slug(result.url)
        if verbose:
            console.print(f"\n[bold]Page {i+1}/{len(results)}:[/bold] {result.url}")

        _process_result(
            result, result.url, page_slug, mode, raw, selector, refs,
            no_images, embed_images, download_images_flag, image_width,
            screenshot_quality, screenshot_width, output_path, verbose,
        )

    if verbose:
        console.print(
            f"\n[bold green]Done![/bold green] Processed {len(results)} pages",
        )


if __name__ == "__main__":
    main()
