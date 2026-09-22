"""Regression tests for the PDF renderer's URL fetcher.

WeasyPrint 70.0 replaced the ``default_url_fetcher`` function with a
``URLFetcher`` class and now reads ``url_fetcher._fail_on_errors`` whenever a
fetch raises. A plain function has no such attribute, so any renderer that
still used the old API failed with::

    AttributeError: 'function' object has no attribute '_fail_on_errors'

...but only once the document actually referenced a resource — i.e. only when
a report template carried a logo. These tests pin both halves of the contract:
data: URIs must render, everything else must stay blocked.
"""
import base64

import pytest

from app.services.report_renderer.engine import _make_url_fetcher

# Smallest valid 1x1 transparent PNG.
_PNG_BYTES = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c489"
    "0000000d4944415478da6364f8cf000000030101002d0bf963"
    "0000000049454e44ae426082"
)
_LOGO_DATA_URI = f"data:image/png;base64,{base64.b64encode(_PNG_BYTES).decode()}"


def _render(html: str) -> bytes:
    from weasyprint import HTML as WeasyHTML  # noqa: N811

    return WeasyHTML(string=html, url_fetcher=_make_url_fetcher()).write_pdf()


def test_renders_pdf_with_data_uri_logo():
    """A report whose template has an uploaded logo must render, not raise."""
    pdf = _render(f'<html><body><img src="{_LOGO_DATA_URI}"></body></html>')
    assert pdf.startswith(b"%PDF")


def test_renders_pdf_without_logo():
    pdf = _render("<html><body><h1>Incident report</h1></body></html>")
    assert pdf.startswith(b"%PDF")


def test_fetcher_returns_weasyprint_response_for_data_uri():
    from weasyprint.urls import URLFetcherResponse

    assert isinstance(_make_url_fetcher()(_LOGO_DATA_URI), URLFetcherResponse)


@pytest.mark.parametrize(
    "url",
    [
        "file:///etc/passwd",
        "http://169.254.169.254/latest/meta-data/",
        "https://example.com/logo.png",
        "ftp://example.com/logo.png",
    ],
)
def test_non_data_schemes_are_blocked(url):
    """SSRF / local-file-disclosure guard: only data: may be fetched."""
    with pytest.raises(ValueError):
        _make_url_fetcher()(url)


def test_blocked_url_does_not_abort_the_render():
    """A blocked resource degrades to a missing image, it does not fail the report."""
    pdf = _render('<html><body><img src="https://example.com/logo.png"></body></html>')
    assert pdf.startswith(b"%PDF")
