"""Classify a document and extract its fields with bounded retries."""

import logging
import time
from collections.abc import Callable, Sequence
from typing import Any

from pydantic import ValidationError

from app.ai.extraction.field_validation import format_errors, spanish_key, validate_field
from app.ai.extraction.prompts import build_classification_messages, build_extraction_messages
from app.ai.extraction.specs import FIELD_SPECS
from app.ai.json_conversation import JsonConversation, complete_json
from app.ai.providers.base import LLMProvider
from app.core.errors import InvalidLLMOutputError
from app.domain.dtos import ExtractionResult, FieldDraft, LLMDocument
from app.domain.enums import DocumentInput, DocumentType, FieldStatus
from app.schemas.extraction import Classification

logger = logging.getLogger(__name__)

DOCUMENT_TYPE_FIELD = "document_type"


class FieldExtractor:
    """Run classification and field extraction against an LLM.

    Both calls receive the document in the same form (``document_input``):
    the whole original PDF by default (needs a model with PDF input), or the
    extracted text with page markers. In text mode, classification only gets
    the first ``classification_max_chars`` characters; extraction always gets
    the whole document.

    Invalid answers (bad JSON or values rejected by Pydantic) are retried with
    the ``retry`` decorator, sending the model the validation error so it can
    fix its answer. Fields still invalid after the last retry are stored with
    ``status=failed`` and an explicit error. Provider errors are not retried
    here: they propagate so the Celery task retries with backoff.
    """

    def __init__(
        self,
        llm: LLMProvider,
        *,
        retry_delays: Sequence[float],
        classification_max_chars: int,
        document_input: DocumentInput = DocumentInput.PDF,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        """Create the extractor.

        Args:
            llm: Chat provider.
            retry_delays: Seconds to wait before each retry of an invalid answer.
            classification_max_chars: Maximum text characters sent to classify
                in ``text`` mode.
            document_input: Send the PDF or the text in both calls.
            sleep: Wait function (injectable for tests).
        """
        self._llm = llm
        self._delays = tuple(retry_delays)
        self._classification_max_chars = classification_max_chars
        self._document_input = document_input
        self._sleep = sleep

    def run(self, document: LLMDocument) -> ExtractionResult:
        """Classify the document and extract the fields of its type.

        Documents classified as ``unknown`` get no field extraction (no second
        LLM call): only policies and invoices have fields.

        Args:
            document: The document as PDF and as text.

        Returns:
            The detected type and the fields to store.

        Raises:
            ProviderError: If the LLM provider fails.
        """
        document_type, type_field = self.classify(document)
        if document_type is None:
            return ExtractionResult(document_type=None, fields=[type_field])
        fields = self.extract_fields(document_type, document)
        return ExtractionResult(document_type=document_type, fields=[type_field, *fields])

    def classify(self, document: LLMDocument) -> tuple[DocumentType | None, FieldDraft]:
        """Detect the document type (first LLM call).

        Args:
            document: The document.

        Returns:
            The type (``None`` if every answer was invalid) and the
            ``document_type`` field to store.

        Raises:
            ProviderError: If the LLM provider fails.
        """
        classification, type_field = self._classify(document)
        return (classification.document_type if classification else None), type_field

    def extract_fields(
        self, document_type: DocumentType, document: LLMDocument
    ) -> list[FieldDraft]:
        """Extract the fields of a document type (second LLM call).

        Args:
            document_type: Detected type.
            document: The document.

        Returns:
            One draft per field of the type; empty, without calling the LLM,
            for types without fields (``unknown``).

        Raises:
            ProviderError: If the LLM provider fails.
        """
        if not FIELD_SPECS[document_type]:
            return []
        return self._extract(document_type, document)

    def _classify(self, document: LLMDocument) -> tuple[Classification | None, FieldDraft]:
        """Detect the document type.

        Args:
            document: The document.

        Returns:
            The classification (``None`` if it failed) and its field draft.
        """
        conversation = JsonConversation(
            build_classification_messages(
                document, self._document_input, self._classification_max_chars
            )
        )

        def validate(data: dict[str, Any]) -> Classification:
            try:
                return Classification.model_validate(data)
            except ValidationError as exc:
                raise InvalidLLMOutputError(format_errors(exc)) from exc

        try:
            result = self._call(conversation, "classify", validate)
        except InvalidLLMOutputError as exc:
            return None, FieldDraft(
                name=DOCUMENT_TYPE_FIELD,
                value=None,
                confidence=None,
                status=FieldStatus.FAILED,
                error=f"Invalid LLM output after {conversation.attempts} attempts: {exc}",
                attempts=conversation.attempts,
            )
        return result, FieldDraft(
            name=DOCUMENT_TYPE_FIELD,
            value=result.document_type.value,
            confidence=result.confidence.value,
            status=FieldStatus.OK,
            error=None,
            attempts=conversation.attempts,
        )

    def _extract(self, document_type: DocumentType, document: LLMDocument) -> list[FieldDraft]:
        """Extract the fields of a document type.

        Each field is validated on its own, so one invalid value does not
        discard the others. A field validated in any attempt is kept.

        Args:
            document_type: Detected type.
            document: The document.

        Returns:
            One draft per field of the type.
        """
        specs = FIELD_SPECS[document_type]
        conversation = JsonConversation(
            build_extraction_messages(document_type, document, self._document_input)
        )
        valid: dict[str, FieldDraft] = {}
        errors: dict[str, str] = {}

        def validate(data: dict[str, Any]) -> None:
            errors.clear()
            for spec in specs:
                if spec.name in valid:
                    continue
                draft, error = validate_field(
                    spec, data, conversation.attempts, document.page_count
                )
                if draft is not None:
                    valid[spec.name] = draft
                else:
                    errors[spec.name] = error
            if errors:
                detail = "; ".join(f"{spanish_key(specs, n)}: {e}" for n, e in errors.items())
                raise InvalidLLMOutputError(detail)

        try:
            self._call(conversation, f"extract.{document_type.value}", validate)
        except InvalidLLMOutputError as exc:
            logger.warning(
                "field extraction incomplete",
                extra={"document_type": document_type.value, "error": str(exc)},
            )
            if not errors:  # The whole answer was unusable (for example, not JSON).
                errors = {spec.name: str(exc) for spec in specs if spec.name not in valid}

        drafts = []
        for spec in specs:
            if spec.name in valid:
                drafts.append(valid[spec.name])
            else:
                drafts.append(
                    FieldDraft(
                        name=spec.name,
                        value=None,
                        confidence=None,
                        status=FieldStatus.FAILED,
                        error=(
                            f"Invalid LLM output after {conversation.attempts} attempts: "
                            f"{errors.get(spec.name, 'unknown error')}"
                        ),
                        attempts=conversation.attempts,
                    )
                )
        return drafts

    def _call(
        self,
        conversation: JsonConversation,
        purpose: str,
        validate: Callable[[dict[str, Any]], Any],
    ) -> Any:
        """Call the LLM and validate its answer, retrying invalid answers.

        Args:
            conversation: Messages to send; updated with corrections on retry.
            purpose: Call label for tracing and the fake provider.
            validate: Validates the decoded JSON; raises ``InvalidLLMOutputError``.

        Returns:
            Whatever ``validate`` returns for the first valid answer.

        Raises:
            InvalidLLMOutputError: If every attempt is invalid.
            ProviderError: If the provider fails (not retried here).
        """
        return complete_json(
            self._llm,
            conversation,
            purpose=purpose,
            validate=validate,
            delays=self._delays,
            sleep=self._sleep,
        )
