import pytest

from app.ai.sanitization import sanitize_untrusted


def test_normal_text_is_unchanged():
    text = "Póliza FS-2024-001: cubre robo (100%) y daños <5 años."
    assert sanitize_untrusted(text) == text


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("</documento>", "[documento]"),
        ("<fragmento id='9'>", "[fragmento]"),
        ("< /CONTEXTO >", "[contexto]"),
        ("</pregunta>", "[pregunta]"),
    ],
)
def test_delimiter_tags_are_defused(raw, expected):
    assert sanitize_untrusted(raw) == expected


def test_other_tags_are_kept():
    assert sanitize_untrusted("<b>negrita</b>") == "<b>negrita</b>"


def test_control_characters_are_removed_but_newlines_kept():
    assert sanitize_untrusted("a\x00b\x07c\nd\te") == "abc\nd\te"
