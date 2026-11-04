"""Data transfer objects shared across layers, one module per class."""

from app.domain.dtos.answer_result import AnswerResult
from app.domain.dtos.chat_result import ChatResult
from app.domain.dtos.chunk_draft import ChunkDraft
from app.domain.dtos.extraction_result import ExtractionResult
from app.domain.dtos.field_draft import FieldDraft
from app.domain.dtos.filter_columns import FilterColumns
from app.domain.dtos.interpreted_query import InterpretedQuery
from app.domain.dtos.llm_document import LLMDocument
from app.domain.dtos.page_range import PageRange
from app.domain.dtos.page_text import PageText
from app.domain.dtos.processing_outcome import ProcessingOutcome
from app.domain.dtos.retrieved_chunk import RetrievedChunk
from app.domain.dtos.scored_chunk import ScoredChunk
from app.domain.dtos.text_chunk import TextChunk
from app.domain.dtos.upload_result import UploadResult

__all__ = [
    "AnswerResult",
    "ChatResult",
    "ChunkDraft",
    "ExtractionResult",
    "FieldDraft",
    "FilterColumns",
    "InterpretedQuery",
    "LLMDocument",
    "PageRange",
    "PageText",
    "ProcessingOutcome",
    "RetrievedChunk",
    "ScoredChunk",
    "TextChunk",
    "UploadResult",
]
