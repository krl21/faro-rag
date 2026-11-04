"""How a chat question was answered."""

from enum import StrEnum


class AskMode(StrEnum):
    """How a chat question was answered.

    ``ANSWER`` is a RAG answer with citations. ``LIST`` is a list of documents
    matching the filters, returned without calling the LLM.
    """

    ANSWER = "answer"
    LIST = "list"
