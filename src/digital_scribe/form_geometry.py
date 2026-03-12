"""1880 U.S. Census form geometry — column-to-field mapping for vision/HTR models.

This is a focused subset of the 1880 U.S. Census Population Schedule, prioritizing
genealogical identifiers (name, relationship, birthplace) over the full statistical
columns (e.g., health, literacy, months unemployed). Defines where each
Census1880Record field appears on the manuscript schedule. Column indices follow
the official layout. Single source of truth: CENSUS_1880_FORM_GEOMETRY.
"""

from typing import Final, TypedDict


class GeometryEntry(TypedDict):
    """Single entry in the 1880 Census form geometry mapping."""

    column: int
    field: str
    description: str


# Unified form geometry: column (1-based) -> field metadata
# Used by Vision/HTR models to know where to look for each field
CENSUS_1880_FORM_GEOMETRY: Final[list[GeometryEntry]] = [
    {"column": 1, "field": "dwelling_number", "description": "Dwelling Number"},
    {"column": 2, "field": "family_number", "description": "Family Number"},
    {"column": 3, "field": "name", "description": "Name"},
    {"column": 7, "field": "relationship_to_head", "description": "Relationship to Head"},
    {"column": 8, "field": "marital_status", "description": "Marital Status"},
    {"column": 10, "field": "occupation", "description": "Occupation"},
    {"column": 15, "field": "birthplace", "description": "Birthplace"},
]

# Derived: column index -> field name (for quick lookup)
CENSUS_1880_COLUMN_MAP: Final[dict[int, str]] = {
    entry["column"]: entry["field"] for entry in CENSUS_1880_FORM_GEOMETRY
}
