"""Server logic tests — transcribe_census_row validation and error handling."""

import pytest

from digital_scribe.server import transcribe_census_row


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
