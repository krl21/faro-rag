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


# --- Tables (Markdown from Docling) ---

from app.ai.ingestion.chunker import split_page, split_table  # noqa: E402

TABLE_PAGE = """## FACTURA N.º ABS-1
Factura emitida en formato electrónico.
## DATOS DEL VEHÍCULO
| Concepto                 | Cantidad | Importe     |
|--------------------------|----------|-------------|
| Furgoneta Cargo Line     | 1 ud     | 31.450,00 € |
| Kit de estanterías       | 1 ud     | 1.280,00 €  |
| Revestimiento del suelo  | 1 ud     | 340,00 €    |
Base imponible 33.070,00 € TOTAL FACTURA 40.014,70 €"""


def test_table_goes_to_its_own_chunk_without_cutting_rows():
    chunks = split_page(TABLE_PAGE, size=1000, overlap=100)
    table = [c for c in chunks if "| Concepto" in c]
    assert len(table) == 1
    assert table[0].splitlines() == [
        "## DATOS DEL VEHÍCULO",
        "| Concepto | Cantidad | Importe |",
        "|---|---|---|",
        "| Furgoneta Cargo Line | 1 ud | 31.450,00 € |",
        "| Kit de estanterías | 1 ud | 1.280,00 € |",
        "| Revestimiento del suelo | 1 ud | 340,00 € |",
    ]
    assert any("Factura emitida" in c for c in chunks)
    assert "## DATOS DEL VEHÍCULO" not in chunks  # The heading goes with its table.
    assert any("TOTAL FACTURA 40.014,70 €" in c for c in chunks)


def test_long_table_repeats_its_header_in_every_chunk():
    rows = [f"| Concepto número {n} | {n} ud | {n},00 € |" for n in range(40)]
    lines = ["| Concepto | Cantidad | Importe |", "|---|---|---|", *rows]
    chunks = split_table(lines, size=300, heading="## LÍNEAS")
    assert len(chunks) > 1
    for chunk in chunks:
        assert chunk.startswith("## LÍNEAS\n| Concepto | Cantidad | Importe |\n|---|---|---|\n")
        assert len(chunk) <= 300
    body = [line for c in chunks for line in c.splitlines()[3:]]
    assert body == rows  # Every row once, none cut.


def test_row_longer_than_the_size_is_kept_whole():
    long_row = "| " + "x" * 500 + " | 1 |"
    chunks = split_table(["| A | B |", "|---|---|", long_row], size=100)
    assert chunks == ["| A | B |\n|---|---|\n" + long_row]


def test_table_without_header_separator_is_split_by_rows():
    lines = ["| Fecha de emisión | 22/04/2026 |", "| Matrícula | 4417 MRT |"]
    assert split_table(lines, size=1000) == ["\n".join(lines)]


def test_single_pipe_line_is_prose():
    assert split_page("Precio | 10 € |", size=100, overlap=10) == ["Precio | 10 € |"]


def test_pages_without_tables_are_chunked_as_before():
    text = "palabra " * 300
    assert split_page(text, size=200, overlap=30) == split_text(text, size=200, overlap=30)
