"""Server logic tests — transcribe_census_row validation and error handling."""

import pytest

from digital_scribe.server import transcribe_census_row


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
