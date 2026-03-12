"""Pydantic models for historical data ingestion."""

from digital_scribe.models.census_1880 import (
    Census1880Record,
    DITTO_MARKS,
    DITTOABLE_FIELDS,
    RecursiveDittoError,
)

__all__ = ["Census1880Record", "DITTO_MARKS", "DITTOABLE_FIELDS", "RecursiveDittoError"]
