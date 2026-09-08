"""Unit tests for pdf_template_service parsing logic."""
import pytest

from app.services.pdf_template_service import _extract_page_css, _split_at_marker

# ── _split_at_marker ──────────────────────────────────────────────────────────

def test_split_at_marker_basic():
    html = "<p>Cover content</p><p>{{IRDoc_CONTENT}}</p><p>Back matter</p>"
    prefix, suffix = _split_at_marker(html)
    assert "Cover content" in prefix
    assert "Back matter" in suffix
    assert "IRDoc_CONTENT" not in prefix
    assert "IRDoc_CONTENT" not in suffix


def test_split_at_marker_no_marker_raises():
    html = "<p>Some content without the marker</p>"
    with pytest.raises(ValueError, match="{{IRDoc_CONTENT}}"):
        _split_at_marker(html)


def test_split_empty_prefix():
    html = "<p>{{IRDoc_CONTENT}}</p><p>Back matter</p>"
    prefix, suffix = _split_at_marker(html)
    assert prefix == ""
    assert "Back matter" in suffix


def test_split_empty_suffix():
    html = "<p>Cover content</p><p>{{IRDoc_CONTENT}}</p>"
    prefix, suffix = _split_at_marker(html)
    assert "Cover content" in prefix
    assert suffix == ""


# ── _extract_page_css ─────────────────────────────────────────────────────────

def test_extract_page_css_returns_string():
    # Minimal valid DOCX bytes (we mock with an empty doc)
    import io

    from docx import Document
    doc = Document()
    buf = io.BytesIO()
    doc.save(buf)
    css = _extract_page_css(buf.getvalue())
    assert isinstance(css, str)
    assert "@page" in css


def test_extract_page_css_includes_page_numbers():
    import io

    from docx import Document
    doc = Document()
    buf = io.BytesIO()
    doc.save(buf)
    css = _extract_page_css(buf.getvalue())
    assert "counter(page)" in css
