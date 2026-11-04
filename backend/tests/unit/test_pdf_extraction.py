from pathlib import Path

import pytest

from app.ai.ingestion.pdf_extractor import ensure_has_text
from app.ai.ingestion.pypdf_extractor import PypdfExtractor
from app.core.errors import CorruptPdfError, NoExtractableTextError, TooManyPagesError
from tests.fixtures.pdf_factory import CORRUPT_PDF, POLICY_TEXT, make_pdf


def _write(tmp_path: Path, content: bytes) -> Path:
    path = tmp_path / "doc.pdf"
    path.write_bytes(content)
    return path


def test_text_is_extracted_per_page(tmp_path):
    path = _write(tmp_path, make_pdf([POLICY_TEXT, "Segunda página con condiciones generales."]))
    pages = PypdfExtractor().extract(path, max_pages=10)
    assert [p.page for p in pages] == [1, 2]
    assert "FS-2024-001" in pages[0].text
    assert "Póliza" in pages[0].text
    assert "condiciones generales" in pages[1].text


def test_corrupt_pdf_raises(tmp_path):
    with pytest.raises(CorruptPdfError):
        PypdfExtractor().extract(_write(tmp_path, CORRUPT_PDF), max_pages=10)


def test_page_limit_is_enforced(tmp_path):
    path = _write(tmp_path, make_pdf(["a"] * 3))
    with pytest.raises(TooManyPagesError):
        PypdfExtractor().extract(path, max_pages=2)


def test_pdf_without_text_is_rejected(tmp_path):
    pages = PypdfExtractor().extract(_write(tmp_path, make_pdf(["", ""])), max_pages=10)
    with pytest.raises(NoExtractableTextError):
        ensure_has_text(pages)


def test_blank_pages_are_dropped_but_text_pages_kept(tmp_path):
    pages = PypdfExtractor().extract(
        _write(tmp_path, make_pdf(["", POLICY_TEXT, ""])), max_pages=10
    )
    useful = ensure_has_text(pages)
    assert [p.page for p in useful] == [2]


def test_page_count_at_the_limit_is_accepted(tmp_path):
    path = _write(tmp_path, make_pdf(["uno", "dos"]))
    assert len(PypdfExtractor().extract(path, max_pages=2)) == 2


def test_missing_file_is_reported_as_corrupt(tmp_path):
    with pytest.raises(CorruptPdfError):
        PypdfExtractor().extract(tmp_path / "no-existe.pdf", max_pages=10)
