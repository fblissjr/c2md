"""Tests for c2md.media security hardening."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path
from unittest.mock import MagicMock, patch

import httpx
from PIL import Image

from c2md.fetch import MAX_REDIRECTS
from c2md.media import (
    MAX_IMAGE_BYTES,
    download_and_compress_images,
    download_images_as_base64,
    find_image_urls,
)


def _make_tiny_jpeg() -> bytes:
    """Create a minimal valid JPEG image in memory."""
    img = Image.new("RGB", (10, 10), color="red")
    buf = BytesIO()
    img.save(buf, "JPEG")
    return buf.getvalue()


def _mock_httpx_client(response: MagicMock) -> tuple[MagicMock, MagicMock]:
    """Return (mock_cls, mock_client) for patching httpx.Client."""
    mock_client = MagicMock()
    mock_client.get.return_value = response
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=False)
    mock_cls = MagicMock(return_value=mock_client)
    return mock_cls, mock_client


def _make_response(content: bytes, content_type: str = "image/jpeg") -> MagicMock:
    """Create a mock httpx response."""
    resp = MagicMock()
    resp.status_code = 200
    resp.content = content
    resp.headers = {"content-type": content_type}
    resp.raise_for_status = MagicMock()
    return resp


class TestDownloadAndCompressImages:
    def test_skips_oversized_response(self, tmp_path: Path):
        resp = _make_response(b"x" * (MAX_IMAGE_BYTES + 1))
        mock_cls, _ = _mock_httpx_client(resp)

        with patch("c2md.media.httpx.Client", mock_cls):
            result = download_and_compress_images(
                ["https://example.com/big.jpg"], tmp_path
            )
        assert "https://example.com/big.jpg" not in result

    def test_skips_non_image_content_type(self, tmp_path: Path):
        resp = _make_response(b"<html>not an image</html>", "text/html")
        mock_cls, _ = _mock_httpx_client(resp)

        with patch("c2md.media.httpx.Client", mock_cls):
            result = download_and_compress_images(
                ["https://example.com/fake.jpg"], tmp_path
            )
        assert "https://example.com/fake.jpg" not in result

    def test_accepts_valid_image(self, tmp_path: Path):
        resp = _make_response(_make_tiny_jpeg())
        mock_cls, _ = _mock_httpx_client(resp)

        with patch("c2md.media.httpx.Client", mock_cls):
            result = download_and_compress_images(
                ["https://example.com/real.jpg"], tmp_path
            )
        assert "https://example.com/real.jpg" in result

    def test_redirect_limit(self, tmp_path: Path):
        mock_cls, mock_client = _mock_httpx_client(MagicMock())
        mock_client.get.side_effect = httpx.ConnectError("skip")

        with patch("c2md.media.httpx.Client", mock_cls):
            download_and_compress_images(
                ["https://example.com/img.jpg"], tmp_path
            )
        assert mock_cls.call_args.kwargs.get("max_redirects") == MAX_REDIRECTS


class TestDownloadImagesAsBase64:
    def test_skips_oversized_response(self):
        resp = _make_response(b"x" * (MAX_IMAGE_BYTES + 1))
        mock_cls, _ = _mock_httpx_client(resp)

        with patch("c2md.media.httpx.Client", mock_cls):
            result = download_images_as_base64(["https://example.com/big.jpg"])
        assert "https://example.com/big.jpg" not in result

    def test_skips_non_image_content_type(self):
        resp = _make_response(b"not an image", "text/html")
        mock_cls, _ = _mock_httpx_client(resp)

        with patch("c2md.media.httpx.Client", mock_cls):
            result = download_images_as_base64(["https://example.com/fake.jpg"])
        assert "https://example.com/fake.jpg" not in result

    def test_returns_data_uri(self):
        resp = _make_response(_make_tiny_jpeg())
        mock_cls, _ = _mock_httpx_client(resp)

        with patch("c2md.media.httpx.Client", mock_cls):
            result = download_images_as_base64(["https://example.com/real.jpg"])
        uri = result["https://example.com/real.jpg"]
        assert uri.startswith("data:image/jpeg;base64,")


class TestFindImageUrls:
    def test_extracts_http_urls(self):
        md = "![alt](https://example.com/img.png) and ![](http://other.com/pic.jpg)"
        urls = find_image_urls(md)
        assert "https://example.com/img.png" in urls
        assert "http://other.com/pic.jpg" in urls

    def test_ignores_relative_urls(self):
        assert len(find_image_urls("![alt](images/local.png)")) == 0

    def test_ignores_data_uris(self):
        assert len(find_image_urls("![alt](data:image/png;base64,abc123)")) == 0
