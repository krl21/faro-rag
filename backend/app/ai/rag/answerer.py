"""RAG pipeline: retrieve, build the prompt, generate and check the answer."""

import logging
import uuid
from collections.abc import Sequence

from app.ai.providers.base import LLMProvider
from app.ai.rag.guardrails import check_answer
from app.ai.rag.prompt_builder import build_answer_messages
from app.ai.rag.retriever import HybridRetriever
from app.core.flow_logging import fields
from app.core.telemetry import get_tracer
from app.domain.dtos import AnswerResult, FieldFact, PageRange, RetrievedChunk
from app.schemas.ask import Citation

logger = logging.getLogger(__name__)

NOT_ENOUGH_INFORMATION = "No hay información suficiente para responder."
"""Message shown in the chat when there is no evidence (user-facing, Spanish)."""

EXCERPT_CHARS = 300


def _not_enough_information() -> AnswerResult:
    """Build the "not enough information" result.

    Returns:
        The result with ``answered=False`` and no citations.
    """
    return AnswerResult(answer=NOT_ENOUGH_INFORMATION, answered=False)


class Answerer:
    """Answer questions using only retrieved document fragments."""

    def __init__(self, retriever: HybridRetriever, llm: LLMProvider) -> None:
        """Create the answerer.

        Args:
            retriever: Hybrid retriever.
            llm: Chat provider.
        """
        self._retriever = retriever
        self._llm = llm

    def answer(
        self,
        question: str,
        document_ids: Sequence[uuid.UUID] | None = None,
        search_text: str | None = None,
        pages: PageRange | None = None,
        facts: Sequence[FieldFact] = (),
    ) -> AnswerResult:
        """Answer a question with citations.

        The LLM is not called when there is no evidence: no fragment passed
        retrieval and there are no extracted fields to cite.

        Args:
            question: User question, sent to the LLM as written.
            document_ids: Restrict the answer to these documents (the ones that
                pass the filters); ``None`` uses every document.
            search_text: Text used for retrieval, when it differs from the
                question (the question without its filters).
            pages: Restrict the fragments to these pages (``None``: all).
            facts: Extracted fields of the document, given to the LLM as
                citable sources before the fragments (questions about one
                document). They answer questions such as "¿la factura es de
                2003?" even when no text fragment is similar enough.

        Returns:
            The answer with its citations, or the "not enough information"
            message with ``answered=False``.

        Raises:
            ProviderError: If the embedding or LLM provider fails.
        """
        with get_tracer().start_as_current_span("rag.answer") as span:
            if document_ids is not None:
                span.set_attribute("rag.document_filter_count", len(document_ids))
            if pages is not None:
                span.set_attribute("rag.pages", f"{pages.start or ''}-{pages.end or ''}")

            print("---> estoy aquí ...")

            fragments = self._retriever.retrieve(search_text or question, document_ids, pages)

            print(f"---> fragmentos del recuperador: {fragments}")

            span.set_attribute("rag.fragments", len(fragments))
            span.set_attribute("rag.facts", len(facts))
            if not fragments and not facts:
                span.set_attribute("rag.answered", False)
                logger.info("no evidence found: the llm is not called")
                return _not_enough_information()

            response = self._llm.complete(
                build_answer_messages(question, fragments, facts), purpose="answer"
            )
            # Same order as in the prompt: facts first, then fragments.
            sources: list[FieldFact | RetrievedChunk] = [*facts, *fragments]
            checked = check_answer(response.text, len(sources))
            span.set_attribute("rag.answered", checked.has_evidence)
            span.set_attribute("rag.citations", len(checked.cited))
            if not checked.has_evidence:
                logger.warning(
                    "llm answer discarded: no valid citation",
                    extra=fields(fragments=len(fragments), facts=len(facts)),
                )
                logger.debug("discarded llm answer", extra=fields(answer=response.text))
                return _not_enough_information()

            # ``checked.cited[i - 1]`` is the source behind marker ``[i]``.
            citations = [
                _citation(marker, sources[number - 1])
                for marker, number in enumerate(checked.cited, start=1)
            ]
            logger.info(
                "answer generated",
                extra=fields(
                    fragments=len(fragments), facts=len(facts), citations=len(citations)
                ),
            )
            return AnswerResult(answer=checked.text, answered=True, citations=citations)


def _citation(marker: int, source: FieldFact | RetrievedChunk) -> Citation:
    """Build the citation of an extracted field or a text fragment.

    Args:
        marker: Number used in the answer text.
        source: The cited source.

    Returns:
        The citation, with ``source`` telling the UI which kind it is.
    """
    if isinstance(source, FieldFact):
        return Citation(
            marker=marker,
            document_id=source.document_id,
            filename=source.filename,
            page=source.page,
            excerpt=f"{source.label}: {source.value}",
            source="field",
            field=source.name,
        )
    chunk = source.chunk
    return Citation(
        marker=marker,
        document_id=chunk.document_id,
        filename=chunk.filename,
        page=chunk.page,
        excerpt=chunk.content[:EXCERPT_CHARS],
    )
