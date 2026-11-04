"""Data transfer objects shared across layers, one module per class."""

from app.domain.dtos.chunk_draft import ChunkDraft
from app.domain.dtos.field_draft import FieldDraft
from app.domain.dtos.field_value_draft import FieldValueDraft
from app.domain.dtos.llm_document import LLMDocument
from app.domain.dtos.page_range import PageRange
from app.domain.dtos.scored_chunk import ScoredChunk

__all__ = ["ChunkDraft", "FieldDraft", "FieldValueDraft", "LLMDocument", "PageRange", "ScoredChunk"]
