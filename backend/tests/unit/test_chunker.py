import itertools

import pytest

from app.ai.ingestion.chunker import chunk_pages, split_text
from app.domain.dtos import PageText


def test_short_text_is_a_single_chunk():
    assert split_text("hola mundo", size=100, overlap=10) == ["hola mundo"]


def test_empty_text_has_no_chunks():
    assert split_text("   \n  ", size=100, overlap=10) == []


def test_chunks_respect_max_size_and_do_not_break_words():
    text = " ".join(f"palabra{i}" for i in range(300))
    chunks = split_text(text, size=100, overlap=20)
    assert len(chunks) > 1
    words = set(text.split())
    for chunk in chunks:
        assert len(chunk) <= 100
        assert set(chunk.split()) <= words


def test_consecutive_chunks_overlap():
    text = " ".join(f"w{i:03d}" for i in range(200))
    chunks = split_text(text, size=100, overlap=30)
    for previous, current in itertools.pairwise(chunks):
        assert current.split()[0] in previous.split()


def test_all_text_is_covered():
    text = " ".join(f"w{i:03d}" for i in range(500))
    chunks = split_text(text, size=120, overlap=25)
    covered = set(" ".join(chunks).split())
    assert covered == set(text.split())


def test_long_word_without_spaces_is_cut():
    chunks = split_text("a" * 250, size=100, overlap=10)
    assert all(len(c) <= 100 for c in chunks)
    assert len(chunks) == 3


@pytest.mark.parametrize(("size", "overlap"), [(0, 0), (100, 100), (100, -1)])
def test_invalid_parameters_are_rejected(size, overlap):
    with pytest.raises(ValueError):
        split_text("texto", size=size, overlap=overlap)


def test_chunks_keep_page_metadata_and_never_cross_pages():
    pages = [PageText(page=1, text="uno " * 60), PageText(page=2, text="dos " * 60)]
    chunks = chunk_pages(pages, size=100, overlap=10)
    assert {c.page for c in chunks} == {1, 2}
    for chunk in chunks:
        expected = "uno" if chunk.page == 1 else "dos"
        assert set(chunk.content.split()) == {expected}
    assert next(c.chunk_index for c in chunks if c.page == 2) == 0
