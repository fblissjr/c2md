# Changelog

## 0.3.0

### Added
- `--insecure` flag for explicit SSL verification bypass (replaces silent auto-fallback)
- Response size limits: 50MB for HTML, 20MB per image
- Content-Type validation for image downloads
- Redirect cap (max 5) on all HTTP clients

### Changed
- Chromium launches with hardened flags: disabled DNS prefetch, WebRTC, safe browsing, network prediction, mDNS, pings
- Browser `wait_until` uses `domcontentloaded` for HTML-only fetches (faster), `networkidle` only for screenshot/PDF
- Image download exception handling narrowed to network/IO errors only

### Removed
- Automatic SSL verification fallback (was silently retrying without cert verification)

## 0.2.0

### Added
- Configurable `--depth` for deep crawl (1-10, default 1)
- Multi-level BFS: crawl can now follow links beyond 1 level deep

## 0.1.0

### Added
- Initial release: convert URLs and files to clean markdown
- Two fetch modes: httpx (fast, default) and playwright (browser, `--browser`)
- Readability-based boilerplate removal (on by default, `--raw` to disable)
- CSS selector targeting (`--selector`)
- Numbered citation references (`--refs`)
- Output modes: markdown (default), screenshot, pdf, metadata, archive
- Deep crawl with BFS link following (`--deep --max-pages N`)
- Image embedding (`--embed-images`) and download (`--download-images`)
- Local file conversion via markitdown (PDF, DOCX, XLSX, HTML)
- Pipe-friendly: stdout by default, `-o` for file output
- Markdown post-processing pipeline (heading fix, citation dedup, empty image strip)
- Content deduplication for deep crawls (`--dedupe`)
- Date extraction and sorting (`--sort-by-date`)
- SSL verification fallback for systems with cert issues
