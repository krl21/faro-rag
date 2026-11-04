"""Processing error of a document."""

from pydantic import BaseModel


class DocumentError(BaseModel):
    """Processing error of a document.

    Attributes:
        code: Machine-readable error code (for example ``no_extractable_text``).
        message: Description of the error.
    """

    code: str
    message: str
