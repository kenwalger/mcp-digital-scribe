"""Temporal HTR Server — MCP server for 1880 U.S. Census handwritten transcription."""

import json
import random

from mcp.server.fastmcp import FastMCP

from digital_scribe.models.census_1880 import Census1880Record
from digital_scribe.form_geometry import CENSUS_1880_FORM_GEOMETRY

# System persona for the transcription context
PALEOGRAPHER_PERSONA = (
    "A 19th-century Paleographer specializing in U.S. Census cursive."
)

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


@mcp.tool()
def transcribe_census_row(image_path: str, row_index: int) -> dict:
    """Transcribe a single row from an 1880 Census manuscript image into a structured record.

    Uses a 19th-century Paleographer persona to interpret cursive handwriting.
    For now, returns a mock transcription; real HTR integration will come in Post 4.1.

    Args:
        image_path: Path to the census manuscript image (file path or URI).
        row_index: Zero-based row index within the image (0 = first data row).

    Returns:
        A Census1880Record as JSON with dwelling_number, family_number, name,
        relationship_to_head, marital_status, occupation, birthplace,
        and handwriting_confidence.
    """
    # Mock implementation: simulate transcription with deterministic-seeding for reproducibility
    rng = random.Random(hash(f"{image_path}:{row_index}") % (2**32))
    confidence = round(0.75 + rng.random() * 0.22, 2)

    record = Census1880Record(
        dwelling_number=max(1, row_index // 5 + 1),
        family_number=max(1, row_index // 4 + 1),
        name=["John Smith", "Mary Johnson", "William Brown", "Elizabeth Davis", "James Wilson"][row_index % 5],
        relationship_to_head=["Head", "Wife", "Son", "Daughter", "Boarder"][row_index % 5],
        marital_status=["Married", "Single", "Widowed"][row_index % 3],
        occupation=["Farmer", "Keeping House", "Laborer", "At School", "None"][row_index % 5],
        birthplace=["New York", "Pennsylvania", "Ohio", "Ireland", "Germany"][row_index % 5],
        handwriting_confidence=confidence,
    )
    return record.model_dump()


if __name__ == "__main__":
    mcp.run(transport="stdio")
