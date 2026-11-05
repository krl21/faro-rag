"""Fields a chat question can filter documents by."""

from enum import StrEnum


class FilterField(StrEnum):
    """Fields a chat question can filter documents by.

    Every value except ``DOCUMENT_TYPE`` is also the name of an extracted field
    with filter columns in ``extracted_fields``.
    """

    DOCUMENT_TYPE = "document_type"
    POLICY_NUMBER = "policy_number"
    HOLDER = "holder"
    TAX_ID = "tax_id"
    LICENSE_PLATE = "license_plate"
    ISSUER = "issuer"
