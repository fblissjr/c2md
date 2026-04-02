"""Tests for c2md.fetch security hardening."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from c2md.fetch import MAX_REDIRECTS


async def _launch_browser_and_get_args() -> list[str]:
    """Launch a mocked BrowserSession and return the Chromium launch args."""
    mock_browser = AsyncMock()
    mock_browser.new_context.return_value = AsyncMock()
    mock_instance = AsyncMock()
    mock_instance.chromium.launch.return_value = mock_browser
    mock_pw = AsyncMock()
    mock_pw.start.return_value = mock_instance

    with patch("playwright.async_api.async_playwright", return_value=mock_pw):
        from c2md.fetch import BrowserSession
        session = BrowserSession()
        await session.__aenter__()
        args = mock_instance.chromium.launch.call_args.kwargs.get("args", [])
        await session.__aexit__(None, None, None)

    return args


async def _fetch_and_get_goto_call(screenshot=False, pdf=False):
    """Run BrowserSession.fetch with full mock stack, return the page.goto call."""
    mock_page = AsyncMock()
    mock_page.goto.return_value = AsyncMock(status=200)
    mock_page.content.return_value = "<html></html>"
    mock_page.url = "https://example.com"
    mock_page.screenshot.return_value = b"fake-png"
    mock_page.pdf.return_value = b"fake-pdf"

    mock_context = AsyncMock()
    mock_context.new_page.return_value = mock_page
    mock_browser = AsyncMock()
    mock_browser.new_context.return_value = mock_context
    mock_instance = AsyncMock()
    mock_instance.chromium.launch.return_value = mock_browser
    mock_pw = AsyncMock()
    mock_pw.start.return_value = mock_instance

    with patch("playwright.async_api.async_playwright", return_value=mock_pw):
        from c2md.fetch import BrowserSession
        session = BrowserSession()
        await session.__aenter__()
        await session.fetch("https://example.com", screenshot=screenshot, pdf=pdf)
        await session.__aexit__(None, None, None)

    return mock_page.goto.call_args


class TestBrowserSessionFlags:
    """Verify Chromium is launched with security-hardening flags."""

    @pytest.mark.asyncio
    async def test_disables_dns_prefetch(self):
        args = await _launch_browser_and_get_args()
        assert "--dns-prefetch-disable" in args

    @pytest.mark.asyncio
    async def test_disables_pings(self):
        args = await _launch_browser_and_get_args()
        assert "--no-pings" in args

    @pytest.mark.asyncio
    async def test_disables_safe_browsing(self):
        args = await _launch_browser_and_get_args()
        assert "--disable-client-side-phishing-detection" in args
        assert "--safebrowsing-disable-auto-update" in args

    @pytest.mark.asyncio
    async def test_disables_network_prediction_features(self):
        args = await _launch_browser_and_get_args()
        features_flag = [a for a in args if a.startswith("--disable-features=")]
        assert len(features_flag) >= 1
        all_features = ",".join(f.split("=", 1)[1] for f in features_flag)
        assert "NetworkPrediction" in all_features
        assert "MediaRouter" in all_features
        assert "DialMediaRouteProvider" in all_features


class TestBrowserSessionWaitUntil:
    """Verify wait_until strategy varies by fetch mode."""

    @pytest.mark.asyncio
    async def test_default_wait_until_is_domcontentloaded(self):
        goto_call = await _fetch_and_get_goto_call()
        assert goto_call.kwargs.get("wait_until") == "domcontentloaded"

    @pytest.mark.asyncio
    async def test_screenshot_uses_networkidle(self):
        goto_call = await _fetch_and_get_goto_call(screenshot=True)
        assert goto_call.kwargs.get("wait_until") == "networkidle"

    @pytest.mark.asyncio
    async def test_pdf_uses_networkidle(self):
        goto_call = await _fetch_and_get_goto_call(pdf=True)
        assert goto_call.kwargs.get("wait_until") == "networkidle"


class _FakeStream:
    """Mock for httpx streaming response."""

    def __init__(self, chunks: list[bytes]):
        self._chunks = chunks

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass

    @property
    def status_code(self):
        return 200

    @property
    def url(self):
        return "https://example.com"

    @property
    def headers(self):
        return {}

    @property
    def charset_encoding(self):
        return "utf-8"

    async def aiter_bytes(self, chunk_size=8192):
        for chunk in self._chunks:
            yield chunk


class _FakeClient:
    """Mock for httpx.AsyncClient that returns a given stream."""

    def __init__(self, stream: _FakeStream, **kwargs):
        self.init_kwargs = kwargs
        self._stream = stream

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass

    def stream(self, method, url):
        return self._stream


class TestFetchStaticHardening:
    """Verify httpx client hardening in fetch_static."""

    @pytest.mark.asyncio
    async def test_redirect_limit(self):
        captured = {}

        class CapturingClient(_FakeClient):
            def __init__(self, **kwargs):
                captured.update(kwargs)
                super().__init__(_FakeStream([b"<html></html>"]), **kwargs)

        with patch("c2md.fetch.httpx.AsyncClient", CapturingClient):
            from c2md.fetch import fetch_static
            await fetch_static("https://example.com")

        assert captured.get("max_redirects") == MAX_REDIRECTS

    @pytest.mark.asyncio
    async def test_response_size_limit(self):
        # 60 x 1MB chunks = 60MB, exceeds 50MB limit
        oversized_chunks = [b"x" * (1024 * 1024)] * 60
        fake_stream = _FakeStream(oversized_chunks)

        class OversizedClient(_FakeClient):
            def __init__(self, **kwargs):
                super().__init__(fake_stream, **kwargs)

        with patch("c2md.fetch.httpx.AsyncClient", OversizedClient):
            from c2md.fetch import fetch_static
            with pytest.raises(ValueError, match="size limit"):
                await fetch_static("https://example.com")
