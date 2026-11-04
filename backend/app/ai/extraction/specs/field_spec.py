"""Definition of one extractable field."""

from dataclasses import dataclass

from pydantic import TypeAdapter

from app.domain.enums import FieldValueType


@dataclass(frozen=True)
class FieldSpec:
    """Definition of one extractable field.

    Attributes:
        name: English name stored in the database and exposed by the API.
        key: Spanish key the LLM uses in its JSON answer.
        adapter: Pydantic adapter that validates the ``{valor, confianza}`` object.
        value_adapter: Pydantic adapter that validates a bare value, as the
            API returns it (used when the user edits a field).
        value_type: Shape of the value, so the UI can pick the editor.
    """

    name: str
    key: str
    adapter: TypeAdapter
    value_adapter: TypeAdapter
    value_type: FieldValueType
