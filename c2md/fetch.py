"""Content fetching: httpx (fast) or playwright (browser)."""

from __future__ import annotations

from dataclasses import dataclass, field

import httpx


@dataclass
class FetchResult:
    """Result from fetching a URL."""

    html: str
    url: str
    status: int
    screenshot: bytes | None = None
    pdf: bytes | None = None
    headers: dict[str, str] = field(default_factory=dict)


class BrowserSession:
    """Playwright browser context manager for single or multi-page crawling.

    Usage:
        async with BrowserSession(headless=True) as session:
            result = await session.fetch("https://example.com")
    """

    def __init__(
        self,
        headless: bool = True,
        timeout: int = 30,
        viewport_width: int = 1280,
        viewport_height: int = 720,
    ):
        self.headless = headless
        self.timeout = timeout * 1000  # playwright uses ms
        self.viewport = {"width": viewport_width, "height": viewport_height}
        self._playwright = None
        self._browser = None
        self._context = None

    async def __aenter__(self) -> BrowserSession:
        from playwright.async_api import async_playwright

        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(headless=self.headless)
        self._context = await self._browser.new_context(viewport=self.viewport)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        if self._context:
            await self._context.close()
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()

    async def fetch(
        self,
        url: str,
        screenshot: bool = False,
        pdf: bool = False,
        wait_for: str | None = None,
    ) -> FetchResult:
        """Fetch a URL with the browser, optionally capturing screenshot/PDF."""
        page = await self._context.new_page()
        try:
            response = await page.goto(url, timeout=self.timeout, wait_until="networkidle")
            status = response.status if response else 0

            if wait_for:
                await page.wait_for_selector(wait_for, timeout=self.timeout)

            html = await page.content()

            screenshot_bytes = None
            if screenshot:
                screenshot_bytes = await page.screenshot(full_page=True, type="png")

            pdf_bytes = None
            if pdf:
                # PDF generation only works in headless mode
                if self.headless:
                    pdf_bytes = await page.pdf(format="A4", print_background=True)

            return FetchResult(
                html=html,
                url=page.url,  # may differ from input if redirected
                status=status,
                screenshot=screenshot_bytes,
                pdf=pdf_bytes,
            )
        finally:
            await page.close()


async def fetch_static(
    url: str,
    timeout: int = 30,
    follow_redirects: bool = True,
    headers: dict[str, str] | None = None,
    verify_ssl: bool = True,
) -> FetchResult:
    """Fast fetch with httpx (no JS rendering)."""
    default_headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/131.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }
    if headers:
        default_headers.update(headers)

    async with httpx.AsyncClient(
        timeout=timeout,
        follow_redirects=follow_redirects,
        headers=default_headers,
        verify=verify_ssl,
    ) as client:
        response = await client.get(url)
        return FetchResult(
            html=response.text,
            url=str(response.url),
            status=response.status_code,
            headers=dict(response.headers),
        )
