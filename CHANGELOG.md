# Changelog

All notable changes to the Digital Scribe project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- **Temporal HTR Server**: FastMCP server (`temporal-htr`) for 1880 U.S. Census handwritten transcription
- **transcribe_census_row tool**: MCP tool that accepts `image_path` and `row_index`, uses a 19th-century Paleographer system persona, and returns a mock `Census1880Record` with `handwriting_confidence`
- **1880 Form Geometry**: `CENSUS_1880_COLUMN_MAP` and `CENSUS_1880_FORM_GEOMETRY` constants defining column-to-field mapping for Vision/HTR models (e.g., Column 3 = Name, Column 10 = Occupation)
- **Form Geometry resource**: `digital-scribe://form-geometry/1880` MCP resource exposing form geometry as JSON
- **examples/test_server.py**: Script that connects to the local Temporal HTR server via stdio and transcribes Row 1 of a dummy image

### Changed

- **Consolidated structure**: Moved `src/models/census_1880.py` to `src/digital_scribe/models/census_1880.py`
- **Package exports**: Updated `digital_scribe` package to export `Census1880Record` from `digital_scribe.models`
- **pyproject.toml**: Simplified to single package `src/digital_scribe` (removed `src/models` as separate package)

## [0.1.0] - 2025-03-12

### Added

- Initial project structure with Python 3.12 and uv
- `Census1880Record` Pydantic model for 1880 U.S. Census records
- Dependencies: mcp, pydantic, spacy, presidio-analyzer
- HTR readiness validation tests
