"""Chat filters end to end: question -> filters -> SQL on the indexed fields -> answer."""

from datetime import UTC, datetime, time, timedelta

import pytest
from sqlalchemy import update

from app.config import get_settings
from app.db.models import Document
from app.db.session import session_scope
from tests.fixtures.pdf_factory import make_pdf

pytestmark = pytest.mark.integration

POLICY_A = """Seguros Faro del Sur
Póliza de seguro de automóvil
Número de póliza: FS-1001
Tomador: Juan Pérez García
Vigencia: desde 01/01/2025 hasta 31/12/2025
Coberturas incluidas:
- Robo total del vehículo"""

POLICY_B = """Seguros Faro del Sur
Póliza de seguro de hogar
Número de póliza: FS-2002
Tomador: Ana López Ruiz
Vigencia: desde 01/01/2026 hasta 31/12/2026
Coberturas incluidas:
- Daños por agua en la vivienda"""

INVOICE_A = """Taller Mecánico El Faro
Factura número 2025-0042
Fecha: 15/03/2025
Referencia póliza: FS-1001
Vehículo matrícula 1234-BCD
Importe total: 1.250,50 EUR"""

INVOICE_B = """Taller Mecánico El Faro
Factura número 2026-0007
Fecha: 10/02/2026
Referencia póliza: FS-2002
Importe total: 300,00 EUR"""


def _upload(client, text: str, filename: str) -> str:
    response = client.post(
        "/documents", files={"file": (filename, make_pdf([text]), "application/pdf")}
    )
    assert response.status_code == 202
    return response.json()["id"]


@pytest.fixture
def docs(client) -> dict[str, str]:
    return {
        "policy_a": _upload(client, POLICY_A, "poliza_a.pdf"),
        "policy_b": _upload(client, POLICY_B, "poliza_b.pdf"),
        "invoice_a": _upload(client, INVOICE_A, "factura_a.pdf"),
        "invoice_b": _upload(client, INVOICE_B, "factura_b.pdf"),
    }


def _ask(client, question: str, **extra) -> dict:
    response = client.post("/ask", json={"question": question, **extra})
    assert response.status_code == 200, response.text
    return response.json()


def _listed(body: dict) -> set[str]:
    assert body["mode"] == "list"
    return {d["id"] for d in body["documents"]}


def _set_uploaded(document_id: str, when: datetime) -> None:
    with session_scope() as session:
        session.execute(update(Document).where(Document.id == document_id).values(created_at=when))


def _toronto_today_start() -> datetime:
    tz = get_settings().tzinfo
    return datetime.combine(datetime.now(tz).date(), time.min, tz)


def test_listing_by_type_does_not_call_the_llm(client, docs):
    body = _ask(client, "necesito las facturas")
    assert _listed(body) == {docs["invoice_a"], docs["invoice_b"]}
    assert body["answer"] == "Encontré 2 documentos que cumplen los filtros."
    assert body["filter_source"] == "rules"
    assert body["filters"]["document_type"] == "invoice"
    assert body["citations"] == []


def test_invoices_saved_yesterday_in_the_configured_time_zone(client, docs):
    # One hour before today's midnight in Toronto: "yesterday" there, even if
    # it is already "today" in UTC.
    _set_uploaded(docs["invoice_a"], _toronto_today_start() - timedelta(hours=1))
    body = _ask(client, "necesito las facturas guardadas ayer")
    assert _listed(body) == {docs["invoice_a"]}


def test_uploaded_today_excludes_older_documents(client, docs):
    _set_uploaded(docs["invoice_b"], datetime.now(UTC) - timedelta(days=10))
    assert _listed(_ask(client, "facturas subidas hoy")) == {docs["invoice_a"]}


def test_amount_range(client, docs):
    assert _listed(_ask(client, "facturas de más de 1000 €")) == {docs["invoice_a"]}
    assert _listed(_ask(client, "facturas de menos de 500 euros")) == {docs["invoice_b"]}
    assert _listed(_ask(client, "facturas entre 100 y 2000 euros")) == {
        docs["invoice_a"],
        docs["invoice_b"],
    }


def test_amount_in_another_currency_matches_nothing(client, docs):
    body = _ask(client, "facturas de más de 10 USD")
    assert _listed(body) == set()
    assert body["answered"] is False
    assert body["answer"] == "No encontré documentos que cumplan esos filtros."


def test_include_policy_numbers(client, docs):
    # The number filters the field, so the invoices of those policies match too.
    body = _ask(client, "las pólizas FS-1001 y FS-2002")
    assert _listed(body) == set(docs.values())
    filters = {"document_type": "policy", "include": body["filters"]["include"]}
    body = _ask(client, "las pólizas FS-1001 y FS-2002", filters=filters)
    assert _listed(body) == {docs["policy_a"], docs["policy_b"]}


def test_policy_number_also_finds_its_invoices(client, docs):
    assert _listed(_ask(client, "documentos de la póliza FS-1001")) == {
        docs["policy_a"],
        docs["invoice_a"],
    }


def test_exclude_policy_number(client, docs):
    body = _ask(client, "facturas excepto la póliza FS-1001")
    assert _listed(body) == {docs["invoice_b"]}
    assert body["filters"]["exclude"] == [{"field": "policy_number", "values": ["FS-1001"]}]


def test_exclude_document_type(client, docs):
    assert _listed(_ask(client, "documentos de 2025 excepto facturas")) == {docs["policy_a"]}


def test_identifiers_are_normalized(client, docs):
    assert _listed(_ask(client, "matrícula 1234bcd")) == {docs["invoice_a"]}
    assert _listed(_ask(client, "documentos de fs-1001")) == {docs["policy_a"], docs["invoice_a"]}


def test_document_date_overlaps_validity_and_issue_dates(client, docs):
    assert _listed(_ask(client, "pólizas vigentes en marzo de 2025")) == {docs["policy_a"]}
    assert _listed(_ask(client, "facturas emitidas en febrero de 2026")) == {docs["invoice_b"]}


def test_partial_name_match_with_explicit_filters(client, docs):
    filters = {"include": [{"field": "holder", "values": ["pérez"]}]}
    body = _ask(client, "pólizas del titular", filters=filters)
    assert _listed(body) == {docs["policy_a"]}  # "Juan Pérez García", only in policy A.
    assert body["filter_source"] == "explicit"


def test_like_wildcards_in_values_are_literal(client, docs):
    for value in ("%", "_", "%%"):
        filters = {"include": [{"field": "holder", "values": [value]}]}
        assert _listed(_ask(client, "pólizas del titular", filters=filters)) == set()


def test_symbol_only_exclusion_removes_nothing(client, docs):
    filters = {"exclude": [{"field": "holder", "values": ["%"]}]}
    assert _listed(_ask(client, "documentos", filters=filters)) == set(docs.values())


def test_rag_answer_only_uses_filtered_documents(client, docs):
    body = _ask(client, "¿qué coberturas tiene la póliza FS-2002?")
    assert body["mode"] == "answer"
    assert body["answered"] is True
    assert {c["document_id"] for c in body["citations"]} <= {docs["policy_b"], docs["invoice_b"]}


def test_rag_with_filters_that_match_nothing_has_no_evidence(client, docs):
    body = _ask(client, "¿qué coberturas tiene la póliza FS-9999?")
    assert body["mode"] == "answer"
    assert body["answered"] is False


def test_document_id_is_combined_with_the_filters(client, docs):
    body = _ask(client, "necesito las facturas", document_id=docs["policy_a"])
    assert _listed(body) == set()


def test_failed_documents_are_never_listed(client, docs):
    _upload(client, "", "escaneado.pdf")  # No text: failed.
    assert len(_listed(_ask(client, "documentos subidos hoy"))) == 4


def test_invalid_explicit_filters_are_rejected(client):
    response = client.post(
        "/ask",
        json={"question": "hola mundo", "filters": {"include": [{"field": "password"}]}},
    )
    assert response.status_code == 422
