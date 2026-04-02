"""Tests for c2md.media security hardening."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path
from unittest.mock import MagicMock, patch

import httpx
import pytest
from PIL import Image


def _make_tiny_jpeg() -> bytes:
    """Create a minimal valid JPEG image in memory."""
    img = Image.new("RGB", (10, 10), color="red")
    buf = BytesIO()
    img.save(buf, "JPEG")
    return buf.getvalue()


class TestDownloadAndCompressImages:
    def test_skips_oversized_response(self, tmp_path: Path):
        from c2md.fetch import MAX_IMAGE_BYTES
        from c2md.media import download_and_compress_images

        oversized_content = b"x" * (MAX_IMAGE_BYTES + 1)
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.content = oversized_content
        mock_resp.headers = {"content-type": "image/jpeg"}
        mock_resp.raise_for_status = MagicMock()

        with patch("c2md.media.httpx.Client") as mock_cls:
            mock_client = MagicMock()
            mock_client.get.return_value = mock_resp
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_cls.return_value = mock_client

            result = download_and_compress_images(
                ["https://example.com/big.jpg"], tmp_path
            )
            assert "https://example.com/big.jpg" not in result

    def test_skips_non_image_content_type(self, tmp_path: Path):
        from c2md.media import download_and_compress_images

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.content = b"<html>not an image</html>"
        mock_resp.headers = {"content-type": "text/html"}
        mock_resp.raise_for_status = MagicMock()

        with patch("c2md.media.httpx.Client") as mock_cls:
            mock_client = MagicMock()
            mock_client.get.return_value = mock_resp
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_cls.return_value = mock_client

            result = download_and_compress_images(
                ["https://example.com/fake.jpg"], tmp_path
            )
            assert "https://example.com/fake.jpg" not in result

    def test_accepts_valid_image(self, tmp_path: Path):
        from c2md.media import download_and_compress_images

        jpeg_bytes = _make_tiny_jpeg()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.content = jpeg_bytes
        mock_resp.headers = {"content-type": "image/jpeg"}
        mock_resp.raise_for_status = MagicMock()

        with patch("c2md.media.httpx.Client") as mock_cls:
            mock_client = MagicMock()
            mock_client.get.return_value = mock_resp
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_cls.return_value = mock_client

            result = download_and_compress_images(
                ["https://example.com/real.jpg"], tmp_path
            )
            assert "https://example.com/real.jpg" in result

    def test_redirect_limit(self, tmp_path: Path):
        from c2md.fetch import MAX_REDIRECTS
        from c2md.media import download_and_compress_images

        with patch("c2md.media.httpx.Client") as mock_cls:
            mock_client = MagicMock()
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client.get.side_effect = httpx.ConnectError("skip")
            mock_cls.return_value = mock_client

            download_and_compress_images(
                ["https://example.com/img.jpg"], tmp_path
            )

            call_kwargs = mock_cls.call_args.kwargs
            assert call_kwargs.get("max_redirects") == MAX_REDIRECTS


class TestDownloadImagesAsBase64:
    def test_skips_oversized_response(self):
        from c2md.fetch import MAX_IMAGE_BYTES
        from c2md.media import download_images_as_base64

        oversized_content = b"x" * (MAX_IMAGE_BYTES + 1)
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.content = oversized_content
        mock_resp.headers = {"content-type": "image/jpeg"}
        mock_resp.raise_for_status = MagicMock()

        with patch("c2md.media.httpx.Client") as mock_cls:
            mock_client = MagicMock()
            mock_client.get.return_value = mock_resp
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_cls.return_value = mock_client

            result = download_images_as_base64(["https://example.com/big.jpg"])
            assert "https://example.com/big.jpg" not in result

    def test_skips_non_image_content_type(self):
        from c2md.media import download_images_as_base64

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.content = b"not an image"
        mock_resp.headers = {"content-type": "text/html"}
        mock_resp.raise_for_status = MagicMock()

        with patch("c2md.media.httpx.Client") as mock_cls:
            mock_client = MagicMock()
            mock_client.get.return_value = mock_resp
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_cls.return_value = mock_client

            result = download_images_as_base64(["https://example.com/fake.jpg"])
            assert "https://example.com/fake.jpg" not in result

    def test_returns_data_uri(self):
        from c2md.media import download_images_as_base64

        jpeg_bytes = _make_tiny_jpeg()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.content = jpeg_bytes
        mock_resp.headers = {"content-type": "image/jpeg"}
        mock_resp.raise_for_status = MagicMock()

        with patch("c2md.media.httpx.Client") as mock_cls:
            mock_client = MagicMock()
            mock_client.get.return_value = mock_resp
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_cls.return_value = mock_client

            result = download_images_as_base64(["https://example.com/real.jpg"])
            uri = result["https://example.com/real.jpg"]
            assert uri.startswith("data:image/jpeg;base64,")


class TestFindImageUrls:
    def test_extracts_http_urls(self):
        from c2md.media import find_image_urls

        md = "![alt](https://example.com/img.png) and ![](http://other.com/pic.jpg)"
        urls = find_image_urls(md)
        assert "https://example.com/img.png" in urls
        assert "http://other.com/pic.jpg" in urls

    def test_ignores_relative_urls(self):
        from c2md.media import find_image_urls

        md = "![alt](images/local.png)"
        urls = find_image_urls(md)
        assert len(urls) == 0

    def test_ignores_data_uris(self):
        from c2md.media import find_image_urls

        md = "![alt](data:image/png;base64,abc123)"
        urls = find_image_urls(md)
        assert len(urls) == 0
