"""Validation tests ensuring the environment is ready for HTR (Post 4.1) integration."""

import pytest

from digital_scribe.models.census_1880 import Census1880Record


def test_census_1880_record_creation() -> None:
    """Census1880Record accepts valid HTR output and validates handwriting_confidence."""
    record = Census1880Record(
        dwelling_number=1,
        family_number=1,
        name="John Smith",
        relationship_to_head="Head",
        marital_status="Married",
        occupation="Farmer",
        birthplace="New York",
        handwriting_confidence=0.92,
    )
    assert record.name == "John Smith"
    assert record.handwriting_confidence == 0.92


def test_census_1880_confidence_bounds() -> None:
    """handwriting_confidence must be between 0.0 and 1.0 for HTR integration."""
    Census1880Record(
        dwelling_number=1,
        family_number=1,
        name="Jane Doe",
        relationship_to_head="Wife",
        marital_status="Married",
        occupation="Keeping House",
        birthplace="Pennsylvania",
        handwriting_confidence=0.0,
    )
    Census1880Record(
        dwelling_number=1,
        family_number=1,
        name="Jane Doe",
        relationship_to_head="Wife",
        marital_status="Married",
        occupation="Keeping House",
        birthplace="Pennsylvania",
        handwriting_confidence=1.0,
    )


def test_census_1880_invalid_confidence_rejected() -> None:
    """Values outside [0, 1] for handwriting_confidence are rejected."""
    with pytest.raises(ValueError):
        Census1880Record(
            dwelling_number=1,
            family_number=1,
            name="Jane Doe",
            relationship_to_head="Wife",
            marital_status="Married",
            occupation="Keeping House",
            birthplace="Pennsylvania",
            handwriting_confidence=1.5,
        )


def test_mcp_importable() -> None:
    """MCP SDK is available for HTR server implementation."""
    import mcp  # noqa: F401

    assert mcp is not None


def test_presidio_importable() -> None:
    """Presidio analyzer is available for Sovereign Redactor (Post 1+)."""
    from presidio_analyzer import AnalyzerEngine  # noqa: F401

    assert AnalyzerEngine is not None


def test_census_record_rejects_empty_strings() -> None:
    """String fields reject empty strings (min_length=1)."""
    with pytest.raises(ValueError):
        Census1880Record(
            dwelling_number=1,
            family_number=1,
            name="John",
            relationship_to_head="",
            marital_status="Married",
            occupation="Farmer",
            birthplace="New York",
            handwriting_confidence=0.9,
        )


def test_resolve_ditto_marks_raises_on_chained_ditto() -> None:
    """resolve_ditto_marks raises RecursiveDittoError when previous_record also has ditto."""
    from digital_scribe.models.census_1880 import RecursiveDittoError

    previous = Census1880Record(
        dwelling_number=1,
        family_number=1,
        name="John Smith",
        relationship_to_head="Head",
        marital_status="Married",
        occupation="do.",  # previous also has ditto — chained
        birthplace="New York",
        handwriting_confidence=0.9,
    )
    record = Census1880Record(
        dwelling_number=1,
        family_number=1,
        name="Mary",
        relationship_to_head="Wife",
        marital_status="Married",
        occupation="do.",
        birthplace="New York",
        handwriting_confidence=0.85,
    )
    with pytest.raises(RecursiveDittoError, match="Chained ditto.*chronological"):
        record.resolve_ditto_marks(previous)


def test_resolve_ditto_marks_with_previous() -> None:
    """resolve_ditto_marks copies values from previous_record when ditto marks detected."""
    previous = Census1880Record(
        dwelling_number=1,
        family_number=1,
        name="John Smith",
        relationship_to_head="Head",
        marital_status="Married",
        occupation="Farmer",
        birthplace="New York",
        handwriting_confidence=0.9,
    )
    record = Census1880Record(
        dwelling_number=1,
        family_number=1,
        name="Mary",
        relationship_to_head="Wife",
        marital_status="do.",  # ditto — same as head
        occupation="do.",
        birthplace='"',
        handwriting_confidence=0.85,
    )
    resolved = record.resolve_ditto_marks(previous)
    assert resolved.occupation == "Farmer"
    assert resolved.birthplace == "New York"
    assert resolved.marital_status == "Married"
    assert resolved.name == "Mary"  # unchanged (not a ditto)
