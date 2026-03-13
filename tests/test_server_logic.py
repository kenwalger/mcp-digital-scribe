"""Server logic tests — transcribe_census_row, ingest_resident, and error handling."""

import pytest

from digital_scribe.server import cross_reference_resident, ingest_resident, transcribe_census_row


def test_transcribe_rejects_negative_row_index() -> None:
    """transcribe_census_row raises ValueError for row_index < 0."""
    with pytest.raises(ValueError, match="row_index must be >= 0"):
        transcribe_census_row("sample_data/1880_Salem_Page1.jpg", -1)


def test_transcribe_raises_file_not_found_for_missing_image() -> None:
    """transcribe_census_row raises FileNotFoundError with clear message for non-existent path."""
    with pytest.raises(FileNotFoundError, match="Image not found"):
        transcribe_census_row("sample_data/nonexistent_ghost.jpg", 0)


def test_transcribe_accepts_relative_path_when_file_exists() -> None:
    """transcribe_census_row resolves relative paths against project root."""
    result = transcribe_census_row("sample_data/1880_Salem_Page1.jpg", 0)
    assert "name" in result
    assert "handwriting_confidence" in result
    assert 0.75 <= result["handwriting_confidence"] <= 1.0


def test_transcribe_raises_access_denied_for_path_traversal() -> None:
    """transcribe_census_row raises PermissionError when path escapes data directory."""
    with pytest.raises(PermissionError, match="Access Denied"):
        transcribe_census_row("sample_data/../../../etc/passwd", 0)


def test_transcribe_raises_access_denied_for_absolute_path() -> None:
    """transcribe_census_row raises PermissionError for absolute paths."""
    with pytest.raises(PermissionError, match="Access Denied"):
        transcribe_census_row("/etc/passwd", 0)


def test_ingest_rejects_unresolved_ditto_marks() -> None:
    """ingest_resident raises ValueError when record contains raw ditto (Knowledge Stewardship)."""
    record_with_ditto = {
        "dwelling_number": 1,
        "family_number": 1,
        "name": "Mary",
        "relationship_to_head": "Wife",
        "marital_status": "Married",
        "occupation": "do.",
        "birthplace": "New York",
        "handwriting_confidence": 0.9,
    }
    with pytest.raises(ValueError, match="Knowledge Stewardship.*resolve ditto"):
        ingest_resident(record_with_ditto)


def test_ingest_and_recall_success() -> None:
    """ingest_resident persists a valid record; cross_reference_resident retrieves it."""
    record = {
        "dwelling_number": 1,
        "family_number": 2,
        "name": "Test Person",
        "relationship_to_head": "Head",
        "marital_status": "Married",
        "occupation": "Clerk",
        "birthplace": "Ohio",
        "handwriting_confidence": 0.95,
    }
    ingest_result = ingest_resident(record)
    assert ingest_result.get("status") == "ingested"
    assert ingest_result.get("@id", "").startswith("urn:uuid:")

    recall_result = cross_reference_resident(surname="Person")
    assert recall_result.get("count", 0) >= 1
    residents = recall_result.get("residents", [])
    found = next(
        (r for r in residents if (r.get("familyName") or "").lower() == "person"),
        None,
    )
    assert found is not None
    assert found.get("givenName") == "Test"
    assert found.get("familyName") == "Person"
