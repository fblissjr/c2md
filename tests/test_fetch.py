"""Tests for c2md.fetch security hardening."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestBrowserSessionFlags:
    """Verify Chromium is launched with security-hardening flags."""

    async def _launch_and_get_args(self):
        """Helper: launch a BrowserSession with mocked Playwright, return launch args."""
        mock_browser = AsyncMock()
        mock_context = AsyncMock()
        mock_browser.new_context.return_value = mock_context
        mock_instance = AsyncMock()
        mock_instance.chromium.launch.return_value = mock_browser

        mock_pw_cm = AsyncMock()
        mock_pw_cm.start.return_value = mock_instance

        with patch("c2md.fetch.async_playwright", return_value=mock_pw_cm):
            from c2md.fetch import BrowserSession

            session = BrowserSession()
            # Manually call to avoid the dynamic import path
            session._playwright = await mock_pw_cm.start()
            session._browser = await session._playwright.chromium.launch(
                headless=True,
                args=session._get_chromium_args() if hasattr(session, '_get_chromium_args') else [],
            )

        # Instead, just call __aenter__ with the right patch
        return mock_instance.chromium.launch.call_args

    @pytest.mark.asyncio
    async def test_disables_dns_prefetch(self):
        mock_browser = AsyncMock()
        mock_browser.new_context.return_value = AsyncMock()
        mock_instance = AsyncMock()
        mock_instance.chromium.launch.return_value = mock_browser
        mock_pw = AsyncMock()
        mock_pw.start.return_value = mock_instance

        # Patch at the module level where async_playwright is imported dynamically
        with patch("playwright.async_api.async_playwright", return_value=mock_pw):
            from c2md.fetch import BrowserSession
            session = BrowserSession()
            await session.__aenter__()
            args = mock_instance.chromium.launch.call_args.kwargs.get("args", [])
            assert "--dns-prefetch-disable" in args
            await session.__aexit__(None, None, None)

    @pytest.mark.asyncio
    async def test_disables_pings(self):
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
            assert "--no-pings" in args
            await session.__aexit__(None, None, None)

    @pytest.mark.asyncio
    async def test_disables_safe_browsing(self):
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
            assert "--disable-client-side-phishing-detection" in args
            assert "--safebrowsing-disable-auto-update" in args
            await session.__aexit__(None, None, None)

    @pytest.mark.asyncio
    async def test_disables_network_prediction_features(self):
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
            features_flag = [a for a in args if a.startswith("--disable-features=")]
            assert len(features_flag) >= 1
            # The flag may be split across lines in source but joined as one string
            all_features = ",".join(f.split("=", 1)[1] for f in features_flag)
            assert "NetworkPrediction" in all_features
            assert "MediaRouter" in all_features
            assert "DialMediaRouteProvider" in all_features
            await session.__aexit__(None, None, None)


class TestBrowserSessionWaitUntil:
    """Verify wait_until strategy varies by fetch mode."""

    async def _fetch_with_mock(self, screenshot=False, pdf=False):
        """Helper: run BrowserSession.fetch with full mock stack, return goto call."""
        mock_page = AsyncMock()
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_page.goto.return_value = mock_response
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

    @pytest.mark.asyncio
    async def test_default_wait_until_is_domcontentloaded(self):
        goto_call = await self._fetch_with_mock()
        assert goto_call.kwargs.get("wait_until") == "domcontentloaded"

    @pytest.mark.asyncio
    async def test_screenshot_uses_networkidle(self):
        goto_call = await self._fetch_with_mock(screenshot=True)
        assert goto_call.kwargs.get("wait_until") == "networkidle"

    @pytest.mark.asyncio
    async def test_pdf_uses_networkidle(self):
        goto_call = await self._fetch_with_mock(pdf=True)
        assert goto_call.kwargs.get("wait_until") == "networkidle"


class TestFetchStaticHardening:
    """Verify httpx client hardening in fetch_static."""

    @pytest.mark.asyncio
    async def test_redirect_limit(self):
        """Verify max_redirects=5 is passed to AsyncClient."""
        from c2md.fetch import MAX_REDIRECTS

        captured_kwargs = {}

        class FakeClient:
            def __init__(self, **kwargs):
                captured_kwargs.update(kwargs)

            async def __aenter__(self):
                return self

            async def __aexit__(self, *args):
                pass

            def stream(self, method, url):
                return FakeStream()

        class FakeStream:
            async def __aenter__(self):
                return self

            async def __aexit__(self, *args):
                pass

            self_ref = self

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
                yield b"<html></html>"

        with patch("c2md.fetch.httpx.AsyncClient", FakeClient):
            from c2md.fetch import fetch_static
            await fetch_static("https://example.com")

        assert captured_kwargs.get("max_redirects") == MAX_REDIRECTS

    @pytest.mark.asyncio
    async def test_response_size_limit(self):
        """Responses exceeding MAX_RESPONSE_BYTES should raise."""
        from c2md.fetch import MAX_RESPONSE_BYTES

        class FakeClient:
            def __init__(self, **kwargs):
                pass

            async def __aenter__(self):
                return self

            async def __aexit__(self, *args):
                pass

            def stream(self, method, url):
                return FakeStream()

        class FakeStream:
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
                # Yield chunks that exceed the limit
                chunk = b"x" * (1024 * 1024)  # 1MB chunks
                for _ in range(60):  # 60MB total > 50MB limit
                    yield chunk

        with patch("c2md.fetch.httpx.AsyncClient", FakeClient):
            from c2md.fetch import fetch_static
            with pytest.raises(Exception, match="[Ee]xceed|size limit"):
                await fetch_static("https://example.com")
