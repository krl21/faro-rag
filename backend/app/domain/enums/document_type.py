"""Document category detected by the LLM."""

from enum import StrEnum


class DocumentType(StrEnum):
    """Document category detected by the LLM."""

    POLICY = "policy"
    INVOICE = "invoice"
    UNKNOWN = "unknown"  # Neither a policy nor an invoice: not used by the chat.
