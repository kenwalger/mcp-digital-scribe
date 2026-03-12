"""Validation tests ensuring the environment is ready for HTR (Post 4.1) integration."""

import pytest

from models.census_1880 import Census1880Record


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
