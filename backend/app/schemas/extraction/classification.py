"""Document type detected by the LLM."""

from typing import Annotated

from pydantic import BeforeValidator, Field

from app.domain.enums import Confidence, DocumentType
from app.schemas.extraction.spanish_input import SpanishInput
from app.schemas.helpers import classified_type_from_spanish, confidence_from_spanish


class Classification(SpanishInput):
    """Document type detected by the LLM.

    Attributes:
        document_type: ``policy``, ``invoice`` or ``unknown`` (``tipo`` on input,
            ``poliza``/``factura``/``desconocido``; any other text becomes
            ``unknown``).
        confidence: Confidence of the classification (``baja``/``media``/``alta``
            on input).
    """

    document_type: Annotated[DocumentType, BeforeValidator(classified_type_from_spanish)] = Field(
        alias="tipo"
    )
    confidence: Annotated[Confidence, BeforeValidator(confidence_from_spanish)] = Field(
        alias="confianza"
    )
