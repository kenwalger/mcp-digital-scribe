"""Temporal HTR Server — MCP server for 1880 U.S. Census handwritten transcription."""

import json
import zlib

from mcp.server.fastmcp import FastMCP

from digital_scribe.models.census_1880 import Census1880Record
from digital_scribe.form_geometry import CENSUS_1880_FORM_GEOMETRY

# System persona and HTR instructions for the transcription context
PALEOGRAPHER_PERSONA = """You are a 19th-century Paleographer specializing in U.S. Census cursive.

Analyze the cursive strokes in this row. If you see "do." or symbols representing "ditto" (e.g. \" or 'do.'), transcribe them exactly so the post-processor can resolve them."""

mcp = FastMCP(
    "temporal-htr",
    instructions=PALEOGRAPHER_PERSONA,
    json_response=True,
)


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
    return round(0.75 + (raw % 100) / 100 * 0.22, 2)


@mcp.tool()
def transcribe_census_row(image_path: str, row_index: int) -> dict:
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


if __name__ == "__main__":
    mcp.run(transport="stdio")
