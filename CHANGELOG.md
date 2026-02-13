# Changelog

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
