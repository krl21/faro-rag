"""Build the RAG prompt with numbered, delimited fragments.

The texts live in ``app/ai/prompts/rag/*.txt`` and are loaded once, here.
"""

from collections.abc import Sequence
from html import escape

from app.ai.prompt_loader import load_prompt, render
from app.ai.providers.types import ChatMessage
from app.ai.sanitization import sanitize_untrusted
from app.domain.dtos import FieldFact, RetrievedChunk

NO_EVIDENCE_TOKEN = "NO_EVIDENCE"  # noqa: S105 - not a secret
"""Exact reply the model must give when the fragments do not answer the question."""

# Loaded once, when the module is imported (texts in app/ai/prompts/rag/).
ANSWER_SYSTEM = render(load_prompt("rag/answer_system.txt"), no_evidence_token=NO_EVIDENCE_TOKEN)
_ANSWER_USER = load_prompt("rag/answer_user.txt")
_FRAGMENT = load_prompt("rag/fragment.txt")
_FIELD_FACT = load_prompt("rag/field_fact.txt")


def format_fragment(number: int, retrieved: RetrievedChunk) -> str:
    """Render one fragment as a tagged block.

    Args:
        number: Citation number shown to the model (1-based).
        retrieved: The retrieved chunk.

    Returns:
        The fragment wrapped in ``<fragmento>`` tags with its document and page.
    """
    chunk = retrieved.chunk
    filename = escape(sanitize_untrusted(chunk.filename), quote=True)
    return render(
        _FRAGMENT,
        number=number,
        filename=filename,
        page=chunk.page,
        content=sanitize_untrusted(chunk.content),
    )


def format_field_fact(number: int, fact: FieldFact) -> str:
    """Render one extracted field as a tagged, citable block.

    Args:
        number: Citation number shown to the model (1-based).
        fact: The extracted field.

    Returns:
        The field wrapped in ``<dato>`` tags with its document and page.
    """
    return render(
        _FIELD_FACT,
        number=number,
        filename=escape(sanitize_untrusted(fact.filename), quote=True),
        page=fact.page if fact.page is not None else "",
        label=fact.label,
        value=sanitize_untrusted(fact.value),
        edited_note=" (corregido por el usuario)" if fact.edited else "",
    )


def build_answer_messages(
    question: str,
    fragments: Sequence[RetrievedChunk],
    facts: Sequence[FieldFact] = (),
) -> list[ChatMessage]:
    """Build the messages for the answer generation call.

    Sources are numbered in this order: first the extracted fields
    (``facts``), then the fragments. ``[n]`` refers to the n-th source.

    Args:
        question: User question.
        fragments: Retrieved chunks.
        facts: Extracted fields of the document, when the question is about one.

    Returns:
        System and user messages.
    """
    blocks = [format_field_fact(i, f) for i, f in enumerate(facts, start=1)]
    blocks += [format_fragment(i, f) for i, f in enumerate(fragments, start=len(facts) + 1)]
    context = "\n\n".join(blocks)
    user = render(_ANSWER_USER, context=context, question=sanitize_untrusted(question))
    return [
        ChatMessage(role="system", content=ANSWER_SYSTEM),
        ChatMessage(role="user", content=user),
    ]
