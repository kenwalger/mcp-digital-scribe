# Changelog

All notable changes to the Digital Scribe project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- **test_link_multi_family_dwelling_atomicity**: Two families in one dwelling; both linked in single call
- **test_link_household_dry_run**: Verifies dry run returns proposed links and leaves archive unchanged (hash comparison)
- **test_search_by_dwelling_tool**: Verifies dwelling_number < 1 raises ValueError
- **test_multi_relation_household**: Head + Wife + two Boarders; verifies symmetric spouse, Head knows both boarders, no data overwritten
- **Social Graph (Extended Household)**: `link_household` in `knowledge_store.py` — Nuclear: Wife→spouse, Son/Daughter→parent to Head. Extended: Boarder/Servant/Employee/Cook→`memberOfHousehold` + `schema:knows` to Head. All links include `relationshipDescription` to preserve census term
- **search_by_dwelling**: Returns all residents in a dwelling (physical building); critical for "Mapping the Block" / multi-family dwellings
- **link_household_relationships tool**: MCP tool groups by `family_number` (handles multiple heads in one dwelling), links households. Dry Run mode returns proposed links without writing
- **test_social_graph_links**: Ingest Head (Farmer) + Boarder (Blacksmith), link household, verify Blacksmith has `memberOfHousehold` to Farmer

### Changed

- **README**: New "Social Graph (Non-Nuclear Relationships)" section — models extended household as graph, not just genealogy
- **_add_to_relation**: Returns bool (True if added); used for accurate link counting; memberOfHousehold now uses it
- **link_household**: Returns LinkResult/DryRunResult (type-safe); uses _process_family_links helper
- **link_dwelling**: Atomic linking — load once, link all families in memory, save once
- **link_household_relationships**: Calls link_dwelling; no isinstance dispatch
- **search_by_dwelling**: dwelling_number < 1 validation moved into store (single source of truth); server lets ValueError propagate
- **test_link_household_dry_run**: Uses `with open(...) as f` for file operations

### Fixed

- **knows data-loss**: Extended-household knows now uses _add_to_relation; no overwrite when multiple boarders/servants

### Added (prior)

- **_parse_historical_name**: Robust name parsing for Schema.org Person; handles "Surname, Given Name" and multi-word given names (e.g. "Mary Ann Jones")
- **Atomic ingestion**: JSONLDStore uses threading.Lock + write-to-temp + os.replace for atomic writes; prevents silent corruption from concurrent writes
- **isolated_archive_path**: Pytest autouse fixture in tests/conftest.py that mocks the archive path to a temp directory; prevents production data pollution
- **DIGITAL_SCRIBE_ARCHIVE_PATH**: Environment variable to override archive path; memory_test uses data/memory_test_run.jsonld (non-tracked)
- **Deterministic fallback IDs**: Legacy entities without @id get urn:digital-scribe:legacy:{content_hash}; RFC-compliant for JSON-LD validation
- **test_ingest_and_recall_success**: Positive-path test for ingest → recall flow
- **Ingest deduplication**: Skip duplicate records; key: (givenName, familyName, censusDwellingNumber, censusFamilyNumber); prevents merging unrelated residents at same address
- **Transparent ingest status**: ingest returns (entity_id, was_created); ingest_resident returns status "ingested" or "duplicate_skipped" with "id"
- **ArchiveCorruptionError**: Custom RuntimeError for corrupt archive; distinguishes corruption (raise) from absence (return [])

### Changed

- **Thread-safe reads**: All search methods (search_by_surname, search_by_family_number, search_by_surname_or_family) hold self._lock during _load_graph; eliminates data-race with concurrent ingest
- **Runtime path resolution**: DIGITAL_SCRIBE_ARCHIVE_PATH resolved inside JSONLDStore.__init__; respects env set after module import
- **memory_test hardening**: Replaced bare asserts in validation block with explicit RuntimeError checks
- **conftest**: Uses monkeypatch.setenv for DIGITAL_SCRIBE_ARCHIVE_PATH (archive resolution moved to store)
- **Name parsing**: Replaced _split_name with _parse_historical_name for correct familyName/givenName mapping
- **Directory creation**: data/ folder is created only in JSONLDStore.__init__ (when store is instantiated), not on every save
- **Lazy store instantiation**: server.py creates JSONLDStore only when ingest_resident or cross_reference_resident is first called
- **Deduplication fix**: search_by_surname_or_family no longer drops entities without @id; assigns urn:digital-scribe:legacy:* fallback for legacy records; ingest enforces @id on all new entities
- **Thread-safe singleton**: _get_knowledge_store() uses global threading.Lock and double-checked locking for true singleton
- **_content_hash**: Hoisted to module-level helper in knowledge_store.py
- **_save_graph**: Trailing newline + f.flush() + os.fsync() before os.replace; replaced flag for tmp cleanup
- **_parse_historical_name**: Strip trailing/leading commas from comma-split parts; exclude empty givenName from JSON-LD
- **Schema symmetry**: Exclude empty givenName from JSON-LD output; single-token names no longer emit empty string for givenName
- **memory_test**: Handles status "error" for both ingest and recall; data/test_archive.jsonld trailing newline added
- **PEP 8**: logger = logging.getLogger(__name__) moved after all imports in knowledge_store.py
- **_record_to_jsonld_entity docstring**: name parsing described as familyName (last token) and givenName (all preceding tokens)

### Fixed

- **Silent corruption**: Atomic write pattern and lock prevent concurrent write collisions and partial writes
- **Postcondition hardening**: Replaced bare assert with RuntimeError for @id validation; safe in optimized Python (-O)
- **family_number validation**: cross_reference_resident now rejects family_number < 1 with a clear error message
- **Dead code**: Removed unreachable len(parts)==1 branch in _parse_historical_name comma-handling
- **Atomic write robustness**: _save_graph uses replaced flag; tmp unlink only when replace failed
- **cross_reference_resident**: Guard uses explicit surname is None and family_number is None checks
- **Robust legacy dedup**: Ingest loop generates fallback ID via _content_hash when match lacks @id; ensures was_created=False skip always triggers
- **Corruption vs absence**: _load_graph: missing file → []; JSONDecodeError → raise ArchiveCorruptionError (prevents data loss from overwriting with [])
- **ingest_resident**: Catches ArchiveCorruptionError; returns status "error" with CRITICAL message; ingestion halted
- **cross_reference_resident**: Catches ArchiveCorruptionError; returns status "error" with CRITICAL message; recall halted (consistent with ingest_resident)

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
