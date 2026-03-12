"""Pytest configuration and shared fixtures."""

from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def isolated_archive_path(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Point the Knowledge Archive at a temporary directory for all tests.

    Prevents production data (data/archive.jsonld) from being touched during tests.
    Resets the lazy store so it is re-created with the temp path on next use.
    """
    archive = tmp_path / "archive.jsonld"
    monkeypatch.setenv("DIGITAL_SCRIBE_ARCHIVE_PATH", str(archive))
    monkeypatch.setattr("digital_scribe.server._KNOWLEDGE_STORE", None)
