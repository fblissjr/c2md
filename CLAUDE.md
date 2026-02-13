# c2md - Content to Markdown

last updated: 2026-02-13

## Overview

c2md converts URLs and files to clean markdown. Simple, lean stack: playwright for browser rendering, readability-lxml for boilerplate removal, and markdownify for HTML-to-markdown conversion.

## Architecture

```
c2md/
  __init__.py       -- version, public API
  __main__.py       -- python -m c2md
  cli.py            -- Click CLI (~300 lines, orchestration)
  fetch.py          -- httpx (fast) or playwright (browser)
  convert.py        -- readability + markdownify -> markdown
  _postprocess.py   -- markdown cleanup pipeline (heading fix, citation dedup, etc.)
  citations.py      -- inline links -> numbered references
  crawl.py          -- BFS deep crawler (1 level, same-domain)
  media.py          -- image download, compress, base64 embed
  extract.py        -- metadata, dates, link analysis from HTML
  output.py         -- file writers (md, screenshot, pdf, archive)
  utils.py          -- url_to_slug, helpers
```

### Data Flow

```
URL or file path
  -> fetch.py: httpx (static) or BrowserSession (playwright)
  -> FetchResult(html, url, screenshot?, pdf?)
  -> convert.py: readability extract -> markdownify -> clean markdown
  -> _postprocess.py: clean_markdown() pipeline
  -> citations.py: add_citations() (optional --refs)
  -> output.py: save to file(s) or stdout
```

### Key Design Decisions

1. **Two fetch modes**: httpx by default (fast, async). Playwright when `--browser` is set, or auto-detected for screenshots/PDF/deep crawls.
2. **readability-lxml for boilerplate removal**: Mozilla's Readability algorithm (Firefox Reader Mode). On by default, `--raw` to disable.
3. **markdownify for conversion**: Handles nested HTML correctly (no word-per-line heading bug from html2text).
4. **stdout by default**: Pipe-friendly. Use `-o` for file output.
5. **Citations are optional**: `--refs` flag to enable. Not on by default.
6. **SSL fallback**: Automatically retries without SSL verification if cert verification fails.

## Dependencies

~10 core deps, ~380MB install (mostly playwright):
- playwright (browser rendering)
- markitdown + markdownify (file + HTML conversion)
- httpx (async HTTP)
- readability-lxml (boilerplate removal)
- beautifulsoup4 + lxml (HTML parsing)
- click, rich, pillow, xxhash, orjson

## CLI Quick Reference

```bash
c2md URL                          # markdown to stdout
c2md URL -o out/                  # save to file
c2md URL --browser                # force playwright (JS sites)
c2md URL --raw                    # no boilerplate removal
c2md URL --selector article       # CSS selector targeting
c2md URL --refs                   # numbered citation references
c2md URL --mode screenshot -o out/  # screenshot
c2md URL --mode pdf -o out/       # PDF
c2md URL --mode metadata          # JSON metadata to stdout
c2md URL --mode archive -o out/   # all formats
c2md URL --deep --max-pages 10    # follow links
c2md URL --embed-images           # base64 images in markdown
c2md report.pdf                   # convert local file
c2md spreadsheet.xlsx             # convert local file
```

## How to Extend

### Adding a new output mode
1. Add to `cli.py`'s `--mode` Choice list
2. Add processing logic in `_process_result()`

### Adding new post-processing
1. Write a function in `_postprocess.py`
2. Add it to `clean_markdown()` pipeline

### Adding new metadata fields
1. Edit `extract.py:extract_metadata()`
