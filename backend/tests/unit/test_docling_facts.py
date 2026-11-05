"""Data of a real invoice converted by Docling (dump of its tables and texts)."""

import json
from pathlib import Path
from types import SimpleNamespace

from app.ai.ingestion.docling_facts import facts_from_docling
from app.ai.ingestion.fact_parsing import describe

# Tables and text items of factura_electronica_ABS-F-2026-00318.pdf (fictitious data),
# as returned by Docling: three tables (two vertical, one of records) and loose texts.
DUMP = Path(__file__).resolve().parents[1] / "fixtures" / "docling_invoice_dump.json"


def _document():
    data = json.loads(DUMP.read_text(encoding="utf-8"))
    tables = [
        SimpleNamespace(
            prov=[SimpleNamespace(page_no=t["page"])],
            data=SimpleNamespace(
                grid=[
                    [SimpleNamespace(text=c, column_header=t["header"] and i == 0) for c in row]
                    for i, row in enumerate(t["grid"])
                ]
            ),
        )
        for t in data["tables"]
    ]
    texts = [
        SimpleNamespace(prov=[SimpleNamespace(page_no=x["page"])], label=x["label"], text=x["text"])
        for x in data["texts"]
    ]
    return SimpleNamespace(tables=tables, texts=texts)


def test_invoice_data_are_found():
    lines = {describe(f.label, f.value) for f in facts_from_docling(_document())}
    for expected in (
        "Fecha de emisión: 22/04/2026",
        "N.º de bastidor (VIN): VF0CLHR26TB228783",
        "Matrícula asignada: 4417 MRT",
        "Base imponible: 33.465,00 €",
        "IVA 21 %: 7.027,65 €",
        "TOTAL FACTURA: 40.492,65 €",
        "FACTURA ELECTRÓNICA N.º: ABS-F-2026-00318",
        "Concepto: Kit de estanterías modulares para zona de carga; Cantidad: 1 ud; "
        "Precio unit.: 1.280,00 €; Importe: 1.280,00 €",
    ):
        assert expected in lines


def test_prose_footers_and_repeated_headers_are_skipped():
    facts = facts_from_docling(_document())
    assert all(f.page == 1 for f in facts)  # Pages 2-4 are prose about the company.
    assert sum(f.label == "Encabezado del documento" for f in facts) == 1
    assert not any("Página 1 de 4" in describe(f.label, f.value) for f in facts)
