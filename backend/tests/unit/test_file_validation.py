import pytest

from app.core.errors import EmptyFileError, FileTooLargeError, InvalidFileTypeError
from app.services.file_validation import validate_pdf_upload
from tests.fixtures.pdf_factory import make_pdf

PDF = make_pdf(["hola"])


def test_valid_pdf_returns_safe_filename():
    assert (
        validate_pdf_upload("../../etc/poliza.pdf", "application/pdf", PDF, 10_000) == "poliza.pdf"
    )


def test_empty_file_is_rejected():
    with pytest.raises(EmptyFileError):
        validate_pdf_upload("a.pdf", "application/pdf", b"", 10_000)


def test_too_large_file_is_rejected():
    with pytest.raises(FileTooLargeError):
        validate_pdf_upload("a.pdf", "application/pdf", PDF, max_bytes=10)


def test_wrong_extension_is_rejected():
    with pytest.raises(InvalidFileTypeError):
        validate_pdf_upload("a.txt", "application/pdf", PDF, 10_000)


def test_wrong_content_type_is_rejected():
    with pytest.raises(InvalidFileTypeError):
        validate_pdf_upload("a.pdf", "image/png", PDF, 10_000)


def test_fake_pdf_by_signature_is_rejected():
    with pytest.raises(InvalidFileTypeError):
        validate_pdf_upload("a.pdf", "application/pdf", b"MZ\x90\x00 executable", 10_000)


@pytest.mark.parametrize(
    "content_type", ["application/pdf; charset=binary", "application/octet-stream", None]
)
def test_accepted_content_types(content_type):
    assert validate_pdf_upload("a.PDF", content_type, PDF, 10_000) == "a.PDF"


def test_leading_whitespace_before_signature_is_tolerated():
    assert validate_pdf_upload("a.pdf", "application/pdf", b"\n  " + PDF, 10_000) == "a.pdf"


def test_missing_filename_gets_a_default():
    assert validate_pdf_upload(None, "application/pdf", PDF, 10_000) == "document.pdf"


def test_file_exactly_at_the_limit_is_accepted():
    assert validate_pdf_upload("a.pdf", "application/pdf", PDF, max_bytes=len(PDF))
