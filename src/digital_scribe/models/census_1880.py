"""1880 U.S. Census record schema based on official historical column headers."""

from typing import Self

from pydantic import BaseModel, ConfigDict, Field


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
        """Logic for inheriting values from previous_record when "do." or '"' is detected.

        Placeholder for the Knowledge Graph phase: resolves ditto marks by copying
        values from the prior row. Not yet implemented.
        """
        return self
