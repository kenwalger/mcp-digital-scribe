"""1880 U.S. Census form geometry — column-to-field mapping for vision/HTR models.

Defines where each Census1880Record field appears on the manuscript schedule.
Column indices follow the official 1880 Population Schedule layout.
Single source of truth: CENSUS_1880_FORM_GEOMETRY.
"""

from typing import Final

# Unified form geometry: column (1-based) -> field metadata
# Used by Vision/HTR models to know where to look for each field
CENSUS_1880_FORM_GEOMETRY: Final[list[dict[str, str | int]]] = [
    {"column": 1, "field": "dwelling_number", "label": "Dwelling Number"},
    {"column": 2, "field": "family_number", "label": "Family Number"},
    {"column": 3, "field": "name", "label": "Name"},
    {"column": 7, "field": "relationship_to_head", "label": "Relationship to Head"},
    {"column": 8, "field": "marital_status", "label": "Marital Status"},
    {"column": 10, "field": "occupation", "label": "Occupation"},
    {"column": 15, "field": "birthplace", "label": "Birthplace"},
]

# Derived: column index -> field name (for quick lookup)
CENSUS_1880_COLUMN_MAP: Final[dict[int, str]] = {
    entry["column"]: entry["field"] for entry in CENSUS_1880_FORM_GEOMETRY
}
