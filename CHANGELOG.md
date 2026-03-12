# Changelog

All notable changes to the Digital Scribe project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- **_parse_historical_name**: Robust name parsing for Schema.org Person; handles "Surname, Given Name" and multi-word given names (e.g. "Mary Ann Jones")
- **Atomic ingestion**: JSONLDStore uses threading.Lock + write-to-temp + os.replace for atomic writes; prevents silent corruption from concurrent writes
- **isolated_archive_path**: Pytest autouse fixture in tests/conftest.py that mocks the archive path to a temp directory; prevents production data pollution
- **DIGITAL_SCRIBE_ARCHIVE_PATH**: Environment variable to override archive path; used by memory_test to target data/test_archive.jsonld

### Changed

- **Name parsing**: Replaced _split_name with _parse_historical_name for correct familyName/givenName mapping
- **Directory creation**: data/ folder is created only in JSONLDStore.__init__ (when store is instantiated), not on every save
- **Lazy store instantiation**: server.py creates JSONLDStore only when ingest_resident or cross_reference_resident is first called
- **Deduplication fix**: search_by_surname_or_family no longer drops entities without @id; assigns urn:uuid:legacy-* fallback for legacy records; ingest enforces @id on all new entities
- **Thread-safe singleton**: _get_knowledge_store() uses global threading.Lock and double-checked locking for true singleton
- **search_by_surname_or_family**: Loads graph once and filters in-memory; ensures consistent fallback IDs for deduplication
- **memory_test**: Uses data/test_archive.jsonld via DIGITAL_SCRIBE_ARCHIVE_PATH; no longer truncates production archive

### Fixed

- **Silent corruption**: Atomic write pattern and lock prevent concurrent write collisions and partial writes
- **Postcondition hardening**: Replaced bare assert with RuntimeError for @id validation; safe in optimized Python (-O)
- **family_number validation**: cross_reference_resident now rejects family_number < 1 with a clear error message

---

### Added (prior)

- **JSONLDStore** (`memory/knowledge_store.py`): Semantic Memory layer; ingests Census1880Record, transforms to Schema.org Person JSON-LD (Schema.org-aligned), persists to `data/archive.jsonld`; search by familyName or censusFamilyNumber
- **ingest_resident tool**: MCP tool to ingest a census record into the Knowledge Archive (Persistence)
- **cross_reference_resident tool**: MCP tool to search the archive by surname and/or family_number (Recall / Semantic Memory)
- **examples/memory_test.py**: Memory-Aware Agent flow — Capture → Resolve → Ingest → Recall; validates two consecutive rows with same family_number can recall each other
- **RecursiveDittoError**: Raised when previous_record also has a ditto in a field; forces chronological resolution
- **DITTOABLE_FIELDS**: Module-level tuple for canonical dittoable field list
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

- **Schema.org alignment**: JSON-LD now uses givenName/familyName (split by first space), hasOccupation (nested Occupation), birthPlace (nested Place); @context "https://schema.org/"
- **Unique identifiers**: @id uses urn:uuid for every entity
- **Semantic recall**: cross_reference_resident queries familyName (Schema.org) and censusFamilyNumber
- **Knowledge Stewardship**: ingest_resident rejects records with unresolved ditto marks; forces resolve_ditto_marks before persistence
- **Memory lifecycle**: Orchestrator (memory_test) follows agentic_memory.md: Capture (transcribe) → Resolve (ditto) → Ingest (JSONLDStore) → Recall (cross_reference_resident)
- **Chained ditto resolution**: resolve_ditto_marks raises RecursiveDittoError when previous_record has ditto in same field
- **salem_test consistency**: Uses DITTO_MARKS and DITTOABLE_FIELDS from model; marital_status in detection loop
- **transcribe_census_row**: Return type -> dict[str, Any] for static analysis
- **Blog-ready comments**: Inline @resource (Data) vs @tool (Action) in server.py
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
