"""Label-value data in tables (vertical, horizontal, records) and in text lines."""

from app.ai.ingestion.fact_parsing import dedupe, describe, facts_from_grid, facts_from_lines


def _pairs(facts):
    return [(f.label, f.value) for f in facts]


# --- Tables ---


def test_vertical_table_gives_one_pair_per_row():
    grid = [["Fecha de emisión", "22/04/2026"], ["Matrícula asignada", "4417 MRT"]]
    facts = facts_from_grid(grid, page=1, table_index=0)
    assert _pairs(facts) == [("Fecha de emisión", "22/04/2026"), ("Matrícula asignada", "4417 MRT")]
    assert [(f.page, f.table_index, f.row_index) for f in facts] == [(1, 0, 0), (1, 0, 1)]


def test_vertical_table_with_a_marked_header_skips_it():
    grid = [["Campo", "Valor"], ["Titular", "ACME, S.L."]]
    facts = facts_from_grid(grid, page=1, table_index=0, header_marked=True)
    assert _pairs(facts) == [("Titular", "ACME, S.L.")]


def test_horizontal_table_pairs_each_header_with_the_value_below():
    grid = [["Póliza", "Fecha", "Importe"], ["FS-2024-001", "01/01/2026", "100,00 €"]]
    facts = facts_from_grid(grid, page=2, table_index=1)
    assert _pairs(facts) == [
        ("Póliza", "FS-2024-001"),
        ("Fecha", "01/01/2026"),
        ("Importe", "100,00 €"),
    ]


def test_table_of_records_gives_one_datum_per_row_with_all_its_columns():
    grid = [
        ["Concepto", "Cantidad", "Importe"],
        ["Kit de estanterías", "1 ud", "1.280,00 €"],
        ["Revestimiento", "1 ud", "340,00 €"],
    ]
    facts = facts_from_grid(grid, page=1, table_index=2, header_marked=True)
    assert len(facts) == 2
    assert facts[0].label == "Kit de estanterías"
    assert facts[0].value == {
        "Concepto": "Kit de estanterías",
        "Cantidad": "1 ud",
        "Importe": "1.280,00 €",
    }
    assert facts[1].row_index == 1
    assert describe(facts[1].label, facts[1].value) == (
        "Concepto: Revestimiento; Cantidad: 1 ud; Importe: 340,00 €"
    )


def test_records_header_is_detected_without_marks():
    grid = [
        ["Cobertura", "Capital", "Franquicia"],
        ["Robo", "3.000 €", "150 €"],
        ["Lunas", "600 €", "0 €"],
    ]
    facts = facts_from_grid(grid, page=1, table_index=0)
    assert facts[0].value == {"Cobertura": "Robo", "Capital": "3.000 €", "Franquicia": "150 €"}


def test_empty_cells_rows_and_columns_are_skipped():
    grid = [["Titular", "", "ACME"], ["", "", ""], ["NIF", "", "B12345678"]]
    assert _pairs(facts_from_grid(grid, page=1, table_index=0)) == [
        ("Titular", "ACME"),
        ("NIF", "B12345678"),
    ]


def test_single_column_table_gives_nothing():
    assert facts_from_grid([["Solo"], ["texto"]], page=1, table_index=0) == []


# --- Lines outside tables ---


def test_colon_pairs_one_under_another():
    lines = [
        "Titular: Distribuciones Gaditanas del Sur, S.L.",
        "NIF: B-11000005",
        "Matrícula: 4417 MRT",
    ]
    assert _pairs(facts_from_lines(lines, page=1)) == [
        ("Titular", "Distribuciones Gaditanas del Sur, S.L."),
        ("NIF", "B-11000005"),
        ("Matrícula", "4417 MRT"),
    ]


def test_several_pairs_on_the_same_line():
    facts = facts_from_lines(["Fecha: 22/04/2026 Forma de pago: Transferencia"], page=1)
    assert _pairs(facts) == [("Fecha", "22/04/2026"), ("Forma de pago", "Transferencia")]


def test_label_line_followed_by_its_value_line():
    lines = [
        "Base imponible",
        "33.465,00 €",
        "IVA 21 %",
        "7.027,65 €",
        "TOTAL FACTURA",
        "40.492,65 €",
    ]
    assert _pairs(facts_from_lines(lines, page=1)) == [
        ("Base imponible", "33.465,00 €"),
        ("IVA 21 %", "7.027,65 €"),
        ("TOTAL FACTURA", "40.492,65 €"),
    ]


def test_label_with_colon_and_value_on_the_next_line():
    assert _pairs(facts_from_lines(["Fecha de vencimiento:", "15/05/2026"], page=1)) == [
        ("Fecha de vencimiento", "15/05/2026")
    ]


def test_amount_or_date_at_the_end_of_the_line():
    lines = ["TOTAL FACTURA 40.492,65 €", "Fecha de emisión 22/04/2026"]
    assert _pairs(facts_from_lines(lines, page=1)) == [
        ("TOTAL FACTURA", "40.492,65 €"),
        ("Fecha de emisión", "22/04/2026"),
    ]


def test_number_sign_heading():
    facts = facts_from_lines(["FACTURA ELECTRÓNICA N.º ABS-F-2026-00318"], page=1)
    assert _pairs(facts) == [("FACTURA ELECTRÓNICA N.º", "ABS-F-2026-00318")]


def test_prose_is_not_taken_as_data():
    lines = [
        "La seguridad en el taller es innegociable: cada puesto tiene su equipo de protección, "
        "se revisan los elevadores cada mes y se hace un simulacro de emergencia al año.",
        "Nuestro código de conducta se resume en tres reglas para tratar a clientes: escuchar.",
        "Creemos que un cliente bien atendido empieza por un equipo bien tratado.",
    ]
    assert facts_from_lines(lines, page=4) == []


def test_dedupe_keeps_the_first_occurrence():
    facts = facts_from_lines(["NIF: B1", "NIF: B1", "NIF: B2"], page=1)
    assert _pairs(dedupe(facts)) == [("NIF", "B1"), ("NIF", "B2")]
