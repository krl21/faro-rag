"""Spanish prompts for document classification and field extraction.

Both calls receive the document in the same form, chosen with
``LLM_DOCUMENT_INPUT``: the original PDF as an attachment (default, the model
sees the whole document with its layout and tables) or the extracted text with
``[Página n]`` markers (for models without PDF input).
``build_document_message`` is the single place that decides it.

Each message is a complete file in ``app/ai/prompts/extraction/`` (one per
call, document type and input mode), loaded once, here; the code only fills
in values such as the document text.
"""

from string import Template

from app.ai.prompt_loader import load_prompt, render
from app.ai.providers.types import Attachment, ChatMessage
from app.ai.sanitization import sanitize_untrusted
from app.domain.dtos import LLMDocument
from app.domain.enums import DocumentInput, DocumentType

# Loaded once, when the module is imported. Each file is a complete message:
# the code only chooses the file (by document type and input mode) and fills
# in values such as the document text.
_CLASSIFY_SYSTEM: dict[DocumentInput, str] = {
    mode: load_prompt(f"extraction/classify_system_{mode.value}.txt").template
    for mode in DocumentInput
}
_CLASSIFY_USER: dict[DocumentInput, Template] = {
    mode: load_prompt(f"extraction/classify_user_{mode.value}.txt") for mode in DocumentInput
}
_EXTRACT_SYSTEM: dict[tuple[DocumentType, DocumentInput], str] = {
    (doc_type, mode): load_prompt(
        f"extraction/extract_system_{doc_type.value}_{mode.value}.txt"
    ).template
    for doc_type in (DocumentType.POLICY, DocumentType.INVOICE)
    for mode in DocumentInput
}
_EXTRACT_USER: dict[DocumentInput, Template] = {
    mode: load_prompt(f"extraction/extract_user_{mode.value}.txt") for mode in DocumentInput
}
_CORRECTION = load_prompt("extraction/correction.txt")


def build_document_message(
    document: LLMDocument,
    mode: DocumentInput,
    template: Template,
    *,
    max_chars: int | None = None,
) -> ChatMessage:
    """Build the user message that carries the document, as PDF or as text.

    Args:
        document: The document in both forms.
        mode: ``pdf`` attaches the original file; ``text`` puts the sanitized
            text in the ``$text`` placeholder of the template.
        template: User message of the call, for that mode.
        max_chars: Only for ``text``: keep at most this many characters
            (``None`` keeps the whole text). Ignored for ``pdf``.

    Returns:
        The user message.
    """
    if mode is DocumentInput.PDF:
        attachment = Attachment(
            data=document.pdf, mime_type="application/pdf", filename=document.filename
        )
        return ChatMessage(role="user", content=render(template), attachments=(attachment,))
    text = sanitize_untrusted(document.text)
    if max_chars is not None:
        text = text[:max_chars]
    return ChatMessage(role="user", content=render(template, text=text))


def build_classification_messages(
    document: LLMDocument, mode: DocumentInput, text_max_chars: int
) -> list[ChatMessage]:
    """Build the classification prompt.

    Args:
        document: The document.
        mode: How the document is sent (PDF or text).
        text_max_chars: Characters kept in ``text`` mode (the start of the
            document usually identifies it). The PDF is always sent whole.

    Returns:
        System and user messages.
    """
    return [
        ChatMessage(role="system", content=_CLASSIFY_SYSTEM[mode]),
        build_document_message(document, mode, _CLASSIFY_USER[mode], max_chars=text_max_chars),
    ]


def build_extraction_messages(
    document_type: DocumentType, document: LLMDocument, mode: DocumentInput
) -> list[ChatMessage]:
    """Build the field extraction prompt for a document type.

    The whole document is always sent (every page), as PDF or as text.

    Args:
        document_type: Detected document type (policy or invoice).
        document: The document.
        mode: How the document is sent (PDF or text).

    Returns:
        System and user messages.
    """
    return [
        ChatMessage(role="system", content=_EXTRACT_SYSTEM[(document_type, mode)]),
        build_document_message(document, mode, _EXTRACT_USER[mode]),
    ]


def pages_to_text(pages: list[tuple[int, str]]) -> str:
    """Join page texts with ``[Página n]`` markers, so the model can tell pages apart.

    Args:
        pages: ``(page number, text)`` pairs in order.

    Returns:
        The full text.
    """
    return "\n\n".join(f"[Página {number}]\n{text}" for number, text in pages)


def build_correction_message(error: str) -> ChatMessage:
    """Build the follow-up message sent when the previous answer was invalid.

    Args:
        error: Validation error of the previous answer.

    Returns:
        A user message asking the model to fix its answer.
    """
    return ChatMessage(role="user", content=render(_CORRECTION, error=error[:1000]))
