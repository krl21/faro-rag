"""ORM models, one module per table.

Importing this package registers every model on ``Base.metadata``, which
Alembic relies on for autogenerate.
"""

from app.db.models.base import Base
from app.db.models.chunk import Chunk
from app.db.models.conversation import Conversation
from app.db.models.document import Document
from app.db.models.extracted_field import ExtractedField

__all__ = ["Base", "Chunk", "Conversation", "Document", "ExtractedField"]
