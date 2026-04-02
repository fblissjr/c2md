"""Tests for c2md CLI security behavior."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import click
from click.testing import CliRunner

from c2md.cli import main
from c2md.fetch import FetchResult


class TestSSLFallback:
    def test_ssl_error_without_insecure_raises(self):
        """SSL failure should error with a message suggesting --insecure."""
        runner = CliRunner()

        ssl_click_error = click.ClickException(
            "SSL certificate verification failed. Use --insecure to bypass."
        )

        with patch("c2md.cli.asyncio.run", side_effect=ssl_click_error):
            result = runner.invoke(main, ["https://expired.badssl.com"])

        assert result.exit_code != 0
        assert "--insecure" in result.output

    def test_insecure_flag_exists(self):
        """The --insecure flag should appear in CLI help."""
        runner = CliRunner()
        result = runner.invoke(main, ["--help"])
        assert "--insecure" in result.output

    def test_insecure_flag_threads_to_fetch_single(self):
        """--insecure should pass insecure=True to _fetch_single."""
        runner = CliRunner()

        with patch("c2md.cli._fetch_single", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = FetchResult(
                html="<html><body>Hello</body></html>",
                url="https://example.com",
                status=200,
            )
            with patch("c2md.cli.asyncio.run", side_effect=lambda coro: None):
                # Patch asyncio.run to invoke the coroutine arg and capture _fetch_single call
                import asyncio

                def run_and_capture(coro):
                    return asyncio.get_event_loop().run_until_complete(coro)

            # Re-patch with a run that actually executes the coroutine
            with patch("c2md.cli.asyncio.run", side_effect=run_and_capture):
                result = runner.invoke(main, ["https://example.com", "--insecure"])

            # Verify _fetch_single was called with insecure=True
            assert mock_fetch.called
            call_args = mock_fetch.call_args
            assert call_args[0][5] is True or call_args.kwargs.get("insecure") is True
