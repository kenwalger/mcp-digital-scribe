"""Temporal HTR Server — MCP server for 1880 U.S. Census handwritten transcription."""

import json
import zlib
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

from digital_scribe.form_geometry import CENSUS_1880_FORM_GEOMETRY
from digital_scribe.memory.knowledge_store import JSONLDStore
from digital_scribe.models.census_1880 import Census1880Record

# Project root: parent of src/ (server.py lives in src/digital_scribe/)
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_DATA_DIR = _PROJECT_ROOT / "sample_data"
_ARCHIVE_PATH = _PROJECT_ROOT / "data" / "archive.jsonld"

_KNOWLEDGE_STORE: JSONLDStore | None = None


def _get_knowledge_store() -> JSONLDStore:
    """Lazy-instantiate the store on first use. Data dir is created only when instantiated."""
    global _KNOWLEDGE_STORE
    if _KNOWLEDGE_STORE is None:
        _KNOWLEDGE_STORE = JSONLDStore(_ARCHIVE_PATH)
    return _KNOWLEDGE_STORE


def _safe_resolve_path(image_path: str) -> Path:
    """Resolve image_path strictly within the project's data directory.

    Rejects absolute paths and paths (e.g. ../) that escape the data directory.
    Raises PermissionError with 'Access Denied' for path traversal attempts.
    """
    path = Path(image_path)
    if path.is_absolute():
        raise PermissionError("Access Denied: absolute paths not allowed")

    resolved = (_PROJECT_ROOT / image_path).resolve()
    data_dir = _DATA_DIR.resolve()

    try:
        resolved.relative_to(data_dir)
    except ValueError:
        raise PermissionError(
            "Access Denied: path must resolve within the project data directory"
        )

    if not resolved.exists():
        raise FileNotFoundError(f"Image not found: {image_path}")
    return resolved


# System persona and HTR instructions for the transcription context
PALEOGRAPHER_PERSONA = """You are a 19th-century Paleographer specializing in U.S. Census cursive.

Analyze the cursive strokes in this row. If you see "do." or symbols representing "ditto" (e.g. \" or 'do.'), transcribe them exactly so the post-processor can resolve them."""

mcp = FastMCP(
    "temporal-htr",
    instructions=PALEOGRAPHER_PERSONA,
    json_response=True,
)


# @resource = Data: read-only content the client can fetch (e.g. form geometry).
# @tool   = Action: an operation the client invokes with arguments (e.g. transcribe).
@mcp.resource("digital-scribe://form-geometry/1880")
def get_1880_form_geometry() -> str:
    """Return the 1880 Census form geometry (column-to-field mapping) for Vision/HTR models."""
    return json.dumps(
        {
            "description": "Column indices and field mappings for the 1880 U.S. Census Population Schedule",
            "geometry": CENSUS_1880_FORM_GEOMETRY,
        },
        indent=2,
    )


def _deterministic_confidence(image_path: str, row_index: int) -> float:
    """Produce reproducible confidence in [0.75, 0.97] from image_path + row_index."""
    raw = zlib.adler32(f"{image_path}{row_index}".encode())
    # raw%100 in [0,99]; /99 maps to [0,1]; *0.22 gives [0,0.22]; +0.75 → [0.75, 0.97]
    return round(0.75 + (raw % 100) / 99.0 * 0.22, 2)


@mcp.tool()
def transcribe_census_row(image_path: str, row_index: int) -> dict[str, Any]:
    """Transcribe a single row from an 1880 Census manuscript image into a structured record.

    Part of the Capture Layer in the Digital Scribe knowledge system: converts
    handwritten manuscript pixels into typed Census1880Record fields. Uses a
    19th-century Paleographer persona to interpret period cursive. For now,
    returns a mock transcription; real HTR integration will come in Post 4.1.

    Args:
        image_path: Path to the census manuscript image (file path or URI).
        row_index: Zero-based row index within the image (0 = first data row).

    Returns:
        A Census1880Record as JSON with dwelling_number, family_number, name,
        relationship_to_head, marital_status, occupation, birthplace,
        and handwriting_confidence.
    """
    if row_index < 0:
        raise ValueError("row_index must be >= 0")

    _safe_resolve_path(image_path)  # validates path and raises on violation

    # Mock implementation: deterministic confidence via adler32 for reproducibility
    confidence = _deterministic_confidence(image_path, row_index)

    # Simulate ditto handling: row 5 often has "do." for occupation (same as head)
    occupations = [
        "Farmer",
        "Keeping House",
        "Laborer",
        "At School",
        "None",
        "do.",  # ditto mark — post-processor resolves from prior row
    ]
    birthplaces = [
        "New York",
        "Pennsylvania",
        "Ohio",
        "Ireland",
        "Germany",
        '"',  # ditto mark — post-processor resolves from prior row
    ]

    record = Census1880Record(
        dwelling_number=max(1, row_index // 5 + 1),
        family_number=max(1, row_index // 4 + 1),
        name=["John Smith", "Mary Johnson", "William Brown", "Elizabeth Davis", "James Wilson", "Sarah Smith"][
            row_index % 6
        ],
        relationship_to_head=["Head", "Wife", "Son", "Daughter", "Boarder", "Daughter"][row_index % 6],
        marital_status=["Married", "Single", "Widowed"][row_index % 3],
        occupation=occupations[row_index % 6],
        birthplace=birthplaces[row_index % 6],
        handwriting_confidence=confidence,
    )
    return record.model_dump()


# Semantic Memory (Long-Term Knowledge): ingest and recall residents
@mcp.tool()
def ingest_resident(record: dict[str, Any]) -> dict[str, Any]:
    """Ingest a Census1880Record into the Knowledge Archive (Semantic Memory).

    Transforms the record to JSON-LD (Schema.org Person) and persists it
    so it can be recalled by cross_reference_resident.
    """
    parsed = Census1880Record.model_validate(record)
    entity_id = _get_knowledge_store().ingest(parsed)
    return {"status": "ingested", "@id": entity_id}


@mcp.tool()
def cross_reference_resident(
    surname: str | None = None,
    family_number: int | None = None,
) -> dict[str, Any]:
    """Search the Knowledge Archive for residents by surname or family number.

    Semantic Memory (Long-Term Knowledge) layer: allows the Scribe to recall
    residents from previous pages or census years. Provide at least one of
    surname or family_number.
    """
    if not (surname or family_number is not None):
        raise ValueError("Provide surname and/or family_number")
    results = _get_knowledge_store().search_by_surname_or_family(
        surname=surname,
        family_number=family_number,
    )
    return {"count": len(results), "residents": results}
