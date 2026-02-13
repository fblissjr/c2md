# c2md

Convert URLs and files to clean markdown.

## Install

```bash
uv pip install .
uv run playwright install chromium
```

## Usage

```bash
c2md https://example.com              # markdown to stdout
c2md https://example.com -o out/      # save to file
c2md https://example.com --browser    # JS-rendered sites
c2md https://example.com --raw        # skip boilerplate removal
c2md https://example.com --refs       # numbered citations
c2md https://example.com --deep       # follow links (1 level)
c2md https://example.com --mode pdf -o out/
c2md report.pdf                       # local files too
```

## Key Flags

| Flag | What it does |
|---|---|
| `--browser` | Force Playwright (JS-heavy sites) |
| `--raw` | Disable readability extraction |
| `--refs` | Inline links become numbered references |
| `--selector CSS` | Target specific element |
| `--embed-images` | Base64 images inline |
| `--deep` | Crawl linked pages (same-domain) |
| `--max-pages N` | Limit crawled pages |
| `--mode` | `markdown` / `screenshot` / `pdf` / `metadata` / `archive` |
| `-o PATH` | Output directory or file |

## Stack

httpx (fast fetch) / playwright (browser) / readability-lxml (boilerplate removal) / markdownify (HTML to markdown)
