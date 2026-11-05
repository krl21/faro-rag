from pathlib import Path

import pytest

from app.ai.ingestion.docling_extractor import DoclingExtractor
from app.ai.ingestion.pdf_extractor import ensure_has_text
from app.ai.ingestion.pdf_pages import count_pages, read_text_layer
from app.core.errors import CorruptPdfError, NoExtractableTextError, TooManyPagesError
from app.domain.dtos import PageText
from tests.fixtures.pdf_factory import CORRUPT_PDF, POLICY_TEXT, make_pdf


def _write(tmp_path: Path, content: bytes) -> Path:
    path = tmp_path / "doc.pdf"
    path.write_bytes(content)
    return path


def test_pages_are_counted(tmp_path):
    assert count_pages(_write(tmp_path, make_pdf(["uno", "dos", "tres"]))) == 3


def test_text_layer_is_read_per_page():
    texts = read_text_layer(make_pdf([POLICY_TEXT, "Segunda página con condiciones generales."]))
    assert len(texts) == 2
    assert "FS-2024-001" in texts[0]
    assert "Póliza" in texts[0]
    assert "condiciones generales" in texts[1]


def test_corrupt_pdf_raises(tmp_path):
    with pytest.raises(CorruptPdfError):
        DoclingExtractor().extract(_write(tmp_path, CORRUPT_PDF), max_pages=10)


def test_corrupt_bytes_raise():
    with pytest.raises(CorruptPdfError):
        read_text_layer(CORRUPT_PDF)


def test_page_limit_is_enforced_before_converting(tmp_path):
    # Raised before Docling is loaded: it also works in the test image.
    path = _write(tmp_path, make_pdf(["a"] * 3))
    with pytest.raises(TooManyPagesError):
        DoclingExtractor().extract(path, max_pages=2)


def test_missing_file_is_reported_as_corrupt(tmp_path):
    with pytest.raises(CorruptPdfError):
        DoclingExtractor().extract(tmp_path / "no-existe.pdf", max_pages=10)


def test_pdf_without_text_is_rejected():
    with pytest.raises(NoExtractableTextError):
        ensure_has_text([PageText(page=1, text=""), PageText(page=2, text="  \n ")])


def test_blank_pages_are_dropped_but_text_pages_kept():
    pages = [PageText(page=1, text=""), PageText(page=2, text=POLICY_TEXT)]
    assert [p.page for p in ensure_has_text(pages)] == [2]
