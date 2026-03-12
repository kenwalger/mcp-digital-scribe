# Changelog

All notable changes to the Digital Scribe project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- **_safe_resolve_path helper**: Validates image_path stays within project data directory; raises PermissionError("Access Denied") for absolute paths or path traversal (../)
- **GeometryEntry TypedDict**: `form_geometry.GeometryEntry` with keys `column`, `field`, `description` — fixes `Final[dict[int, str]]` typing
- **Fail-fast path validation**: `transcribe_census_row` raises `FileNotFoundError` when `image_path` does not exist (pathlib.Path)
- **tests/test_server_logic.py**: Path failure test (FileNotFoundError for non-existent image), relative path acceptance test
- **resolve_ditto_marks implementation**: Copies values from `previous_record` when dittoable fields contain ditto marks; includes marital_status; DITTO_MARKS module-level constant
- **Temporal HTR Server**: FastMCP server (`temporal-htr`) for 1880 U.S. Census handwritten transcription
- **transcribe_census_row tool**: Capture Layer tool accepting `image_path` and `row_index`, using a 19th-century Paleographer persona, returning a mock `Census1880Record` with deterministic `handwriting_confidence`
- **1880 Form Geometry**: Unified `CENSUS_1880_FORM_GEOMETRY` (single source of truth) and derived `CENSUS_1880_COLUMN_MAP` for Vision/HTR models
- **Form Geometry resource**: `digital-scribe://form-geometry/1880` MCP resource exposing form geometry as JSON
- **examples/test_server.py**: Script that spawns the server via stdio and transcribes Row 1 of `sample_data/1880A_hi.jpg`
- **README**: Explicit mention of pure Python stack and uv for dependency management

### Changed

- **Secure path resolution**: `_safe_resolve_path` enforces paths within sample_data/; rejects ../ and absolute paths with Access Denied
- **DITTO_MARKS**: Module-level frozenset with specific patterns ("do.", '"', '""', "''", "do" as standalone); marital_status added to resolve_ditto_marks
- **Test reorganization**: test_transcribe_rejects_negative_row_index moved to test_server_logic.py
- **Absolute path resolution**: Relative `image_path` resolved against project root (via `src/` location); absolute paths unchanged
- **resolve_ditto_marks**: Implemented (was placeholder); returns new record via `model_copy(update=...)`
- **server.py cleanup**: Removed redundant `if __name__ == "__main__"` guard; entry point is `__main__.py`
- **Geometry typing**: `CENSUS_1880_FORM_GEOMETRY` uses `list[GeometryEntry]`; renamed `label` to `description`
- **Pydantic v2 idioms**: `Census1880Record.model_config` uses `ConfigDict` instead of plain dict
- **__main__.py**: Simplified to `main()` + `if __name__ == "__main__": main()` pattern
- **Pydantic hardening**: `min_length=1` on all string fields (occupation, birthplace, relationship_to_head, marital_status); `str_strip_whitespace=True` prevents empty strings in archives
- **Server validation**: `transcribe_census_row` raises `ValueError` for `row_index < 0`
- **Form geometry scoping**: Module docstring states focused subset prioritizing genealogical identifiers over full statistical columns (health, literacy)
- **Confidence formula**: `_deterministic_confidence` uses `/99` divisor so range [0.75, 0.97] is reached accurately
- **Determinism fix**: Replaced `hash()`-based confidence with `zlib.adler32()` for reproducible confidence across server restarts
- **Integration test**: Use actual Salem census image `sample_data/1880A_hi.jpg`; move `import json` to module level
- **Form geometry consolidation**: `CENSUS_1880_FORM_GEOMETRY` is now the single source of truth; `CENSUS_1880_COLUMN_MAP` is derived
- **Consolidated structure**: Moved `src/models/census_1880.py` to `src/digital_scribe/models/census_1880.py`
- **Package exports**: Updated `digital_scribe` package to export `Census1880Record` from `digital_scribe.models`
- **pyproject.toml**: Simplified to single package `src/digital_scribe` (removed `src/models` as separate package)

## [0.1.0] - 2025-03-12

### Added

- Initial project structure with Python 3.12 and uv
- `Census1880Record` Pydantic model for 1880 U.S. Census records
- Dependencies: mcp, pydantic, spacy, presidio-analyzer
- HTR readiness validation tests
