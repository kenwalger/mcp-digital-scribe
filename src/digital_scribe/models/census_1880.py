"""1880 U.S. Census record schema based on official historical column headers."""

from typing import Self

from pydantic import BaseModel, ConfigDict, Field

# Ditto marks: "do." (with period), quote symbols, standalone "do" (exact match only)
DITTO_MARKS: frozenset[str] = frozenset(("do.", '"', '""', "''", "do"))

# Fields that may contain ditto marks and can be resolved from previous_record
DITTOABLE_FIELDS: tuple[str, ...] = (
    "occupation",
    "birthplace",
    "name",
    "relationship_to_head",
    "marital_status",
)


class RecursiveDittoError(ValueError):
    """Raised when previous_record also contains a ditto in a field we need to resolve.

    Enforces chronological resolution: the orchestrator must process records in order
    so that ditto chains can be resolved (row N inherits from N-1, which must be
    already resolved).
    """


class Census1880Record(BaseModel):
    """
    Pydantic model for an 1880 U.S. Census record.

    Schema aligned with official historical column headers from the
    1880 Census manuscript schedules (Population Schedule).
    """

    dwelling_number: int = Field(
        ...,
        description="Sequential number of the dwelling house in the order of visitation",
        ge=1,
    )
    family_number: int = Field(
        ...,
        description="Sequential number of the family in the order of visitation",
        ge=1,
    )
    name: str = Field(
        ...,
        description="Name of each person whose usual place of abode on the first day of June 1880 was in this family",
        min_length=1,
        max_length=255,
    )
    relationship_to_head: str = Field(
        ...,
        description="Relationship of each person to the head of the family",
        min_length=1,
        max_length=50,
    )
    marital_status: str = Field(
        ...,
        description="Whether single, married, widowed, or divorced",
        min_length=1,
        max_length=20,
    )
    occupation: str = Field(
        ...,
        description="Profession, trade, or occupation of each person",
        min_length=1,
        max_length=100,
    )
    birthplace: str = Field(
        ...,
        description="State or territory of United States, or country of birth",
        min_length=1,
        max_length=100,
    )
    handwriting_confidence: float = Field(
        ...,
        description="HTR confidence score for this record (0.0 to 1.0)",
        ge=0.0,
        le=1.0,
    )

    model_config = ConfigDict(
        str_strip_whitespace=True,
        extra="forbid",
    )

    def resolve_ditto_marks(self, previous_record: "Census1880Record | None") -> Self:
        """Logic for inheriting values from previous_record when ditto marks are detected.

        When a dittoable field contains a ditto mark, copies from previous_record.
        Raises RecursiveDittoError if previous_record also has a ditto in that field
        (chained ditto); forces the orchestrator to resolve records in chronological order.
        Returns a new record; does not mutate self.
        """
        if previous_record is None:
            return self

        updates: dict[str, str] = {}
        for field in DITTOABLE_FIELDS:
            val = getattr(self, field)
            if val in DITTO_MARKS:
                prev_val = getattr(previous_record, field)
                if prev_val in DITTO_MARKS:
                    raise RecursiveDittoError(
                        f"Chained ditto in {field}: previous_record also has ditto {prev_val!r}. "
                        "Resolve records in chronological order."
                    )
                updates[field] = prev_val

        if not updates:
            return self
        return self.model_copy(update=updates)
