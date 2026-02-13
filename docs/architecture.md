# c2md architecture

last updated: 2026-02-13

## Motivation

c4md wrapped crawl4ai, using ~20% of a 43,000-line codebase and installing 30+ dependencies (~1GB+). Most of what c4md actually used boiled down to playwright browser management and PruningContentFilter. Everything else (markdown conversion, HTTP fetching, caching, link extraction) was overcomplicated and in some cases buggy (html2text word-per-line heading bug, citation duplication).

c2md replaces crawl4ai entirely with a simpler, leaner stack:
- playwright: browser rendering, screenshots, PDFs
- markdownify: HTML-to-markdown (via markdownify, handles nested divs correctly)
- markitdown: file format conversion (PDF, DOCX, XLSX)
- httpx: fast async HTTP for static sites
- readability-lxml: Mozilla Readability for boilerplate removal

~10 deps, ~380MB install vs 30+ deps, ~1GB+.

## Module Map

```
c2md/
  __init__.py       -- version only
  __main__.py       -- python -m c2md entry point
  cli.py            -- Click CLI, orchestration
  fetch.py          -- httpx + BrowserSession (playwright)
  convert.py        -- readability + markdownify -> markdown
  _postprocess.py   -- markdown cleanup pipeline
  citations.py      -- inline links -> numbered references
  crawl.py          -- BFS deep crawler
  media.py          -- image download, compress, base64
  extract.py        -- metadata, dates, links from HTML
  output.py         -- file writers
  utils.py          -- url_to_slug
```

## Data Flow

```
URL or file
  |
  v
fetch.py
  httpx (default, fast, no JS)
  OR BrowserSession (playwright, JS rendering)
  |
  v
FetchResult { html, url, status, screenshot?, pdf? }
  |
  v
convert.py
  readability-lxml: extract main content (strip boilerplate)
  markdownify: HTML -> markdown
  |
  v
_postprocess.py: clean_markdown()
  1. fix_heading_linebreaks (Webflow animated headings)
  2. fix_citation_duplication (doubled link text)
  3. strip_empty_image_links (empty alt text)
  4. collapse_blank_lines (formatting)
  |
  v
citations.py: add_citations() (optional)
  [text](url) -> text [N] + ## References
  |
  v
output.py: stdout or save to file(s)
```

## Key Decisions

### Two fetch modes
httpx for static sites (fast, async, lightweight). Playwright only when needed: `--browser` flag, or auto-detected for screenshots, PDF, deep crawls. crawl4ai always spun up a full browser -- wasteful for most pages.

### readability-lxml for boilerplate removal
Mozilla's Readability algorithm (Firefox Reader Mode) extracts main content automatically. Replaces PruningContentFilter. On by default, `--raw` to disable.

### markdownify for HTML conversion
markdownify handles nested HTML structures correctly. No word-per-line heading bug (which html2text/crawl4ai's fork had). We strip nav/footer/header/aside tags via BeautifulSoup before passing to markdownify.

### stdout by default
c4md always wrote to files. c2md defaults to stdout, making it pipe-friendly:
```bash
c2md URL | head -20
c2md URL | pbcopy
c2md URL > article.md
```

### Browser session reuse
For deep crawls, one browser instance handles all pages via BrowserSession context manager. Simple ~80 lines vs crawl4ai's 1800-line browser pool.

## What Was Ported from c4md

| Component | Action |
|-----------|--------|
| Image processing (media.py) | Ported from processors.py, adapted interface |
| Post-processing pipeline (_postprocess.py) | Ported from processors.py |
| Date extraction (extract.py) | Ported from extractors.py |
| Metadata extraction (extract.py) | Ported + reimplemented (works on raw HTML now) |
| URL slug (utils.py) | Ported as-is |
| Citation system (citations.py) | Written fresh (c4md used crawl4ai's built-in) |
| Deep crawling (crawl.py) | Written fresh (~100 lines BFS) |
| Browser management (fetch.py) | Written fresh (~80 lines playwright) |
| HTML conversion (convert.py) | Written fresh (readability + markdownify) |
