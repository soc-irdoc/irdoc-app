"""Smoke test: PdfTemplate model imports and has expected columns."""
from app.models.pdf_template import PdfTemplate


def test_pdf_template_has_required_columns():
    cols = {c.key for c in PdfTemplate.__table__.columns}
    assert "id" in cols
    assert "org_id" in cols
    assert "prefix_html" in cols
    assert "suffix_html" in cols
    assert "page_css" in cols
    assert "mammoth_warnings" in cols
    assert "original_docx_path" in cols
    assert "is_default" in cols
