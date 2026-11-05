"""Source page of extracted values and the value type of each field."""

import json

import pytest
from pydantic import ValidationError

from app.ai.extraction.field_validation import validate_field
from app.ai.extraction.specs import FIELD_SPECS, find_spec
from app.ai.providers.fake_provider import FakeLLMProvider
from app.ai.providers.types import Attachment, ChatMessage
from app.domain.enums import DocumentType, FieldValueType
from app.schemas.ask import DocumentAskRequest, PageRangeIn
from app.schemas.extraction import ExtractedValue
from app.schemas.helpers import page_or_none
from tests.fixtures.pdf_factory import make_pdf


@pytest.mark.parametrize(("raw", "page"), [(3, 3), ("2", 2), (1, 1)])
def test_valid_pages(raw, page):
    assert page_or_none(raw) == page


@pytest.mark.parametrize("raw", [0, -1, "última", None, 2.5j, True, [], {}])
def test_unusable_pages_become_none(raw):
    assert page_or_none(raw) is None


def test_extracted_value_reads_the_spanish_page():
    value = ExtractedValue[str].model_validate({"valor": "x", "confianza": "alta", "pagina": 4})
    assert value.page == 4
    assert ExtractedValue[str].model_validate({"valor": "x", "confianza": "alta"}).page is None


def test_an_invalid_page_does_not_reject_the_value():
    value = ExtractedValue[str].model_validate({"valor": "x", "confianza": "alta", "pagina": "?"})
    assert (value.value, value.page) == ("x", None)


def _policy_number_spec():
    return find_spec("policy", "policy_number")


def test_validated_field_keeps_its_page():
    data = {"numero_poliza": {"valor": "FS-1", "confianza": "alta", "pagina": 2}}
    draft, error = validate_field(_policy_number_spec(), data, attempts=1, page_count=3)
    assert error == ""
    assert draft.page == 2


def test_page_beyond_the_document_is_dropped():
    data = {"numero_poliza": {"valor": "FS-1", "confianza": "alta", "pagina": 9}}
    draft, _ = validate_field(_policy_number_spec(), data, attempts=1, page_count=3)
    assert draft.value == "FS-1"
    assert draft.page is None


def test_not_found_fields_have_no_page():
    data = {"numero_poliza": {"valor": None, "confianza": "baja", "pagina": 1}}
    draft, _ = validate_field(_policy_number_spec(), data, attempts=1, page_count=3)
    assert draft.page is None


@pytest.mark.parametrize(
    ("document_type", "name", "value_type"),
    [
        ("policy", "policy_number", FieldValueType.TEXT),
        ("policy", "validity", FieldValueType.PERIOD),
        ("policy", "coverages", FieldValueType.TEXT_LIST),
        ("invoice", "invoice_amount", FieldValueType.MONEY),
        ("invoice", "invoice_date", FieldValueType.DATE),
    ],
)
def test_every_field_declares_its_value_type(document_type, name, value_type):
    assert find_spec(document_type, name).value_type is value_type


@pytest.mark.parametrize(
    ("document_type", "name"),
    [
        ("policy", "invoice_amount"),
        ("policy", "document_type"),
        (None, "holder"),
        ("x", "holder"),
        ("unknown", "holder"),
        ("other", "holder"),
    ],
)
def test_unknown_fields_have_no_spec(document_type, name):
    assert find_spec(document_type, name) is None


def test_every_spec_has_a_value_type():
    for specs in FIELD_SPECS.values():
        assert all(isinstance(spec.value_type, FieldValueType) for spec in specs)


def test_value_adapter_validates_the_api_shape():
    spec = find_spec("invoice", "invoice_amount")
    money = spec.value_adapter.validate_python({"amount": "10.5", "currency": "eur"})
    assert spec.value_adapter.dump_python(money, mode="json") == {
        "amount": "10.5",
        "currency": "EUR",
    }


def test_fake_reports_the_page_of_each_value():
    pdf = make_pdf(["Portada", "Factura número 7\nImporte total: 10,00 EUR", "Matrícula 1234-BCD"])
    message = ChatMessage(
        role="user",
        content="extrae",
        attachments=(Attachment(data=pdf, mime_type="application/pdf"),),
    )
    answer = json.loads(FakeLLMProvider().complete([message], purpose="extract.invoice").text)
    assert answer["monto_factura"]["pagina"] == 2
    assert answer["matricula"]["pagina"] == 3
    assert answer["numero_poliza"]["pagina"] is None  # Not found.


def test_document_type_fields_are_known():
    assert set(FIELD_SPECS) == set(DocumentType)


def test_page_range_uses_from_and_to():
    pages = PageRangeIn.model_validate({"from": 2, "to": 5})
    assert (pages.start, pages.end) == (2, 5)
    assert pages.model_dump(by_alias=True) == {"from": 2, "to": 5}


@pytest.mark.parametrize(
    "data", [{"from": 5, "to": 2}, {"from": 0}, {"to": -1}, {"desde": 1}, {"from": "a"}]
)
def test_invalid_page_ranges_are_rejected(data):
    with pytest.raises(ValidationError):
        PageRangeIn.model_validate(data)


def test_document_question_body():
    body = DocumentAskRequest.model_validate({"question": "¿qué cubre?", "pages": {"to": 3}})
    assert body.conversation_id is None
    assert (body.pages.start, body.pages.end) == (None, 3)
    with pytest.raises(ValidationError):
        DocumentAskRequest.model_validate({"question": "ab"})


def test_other_documents_have_no_fields():
    assert FIELD_SPECS[DocumentType.UNKNOWN] == ()
