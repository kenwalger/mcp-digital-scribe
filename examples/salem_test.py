"""Salem Smoke Test — transcribes Row 5 of an 1880 Salem census page.

Validates the Temporal HTR server against real handwritten images, including
verification of ditto mark handling ("do." or ") in the Census1880Record output.

Run from project root:
    uv run python examples/salem_test.py
"""

import asyncio
import json
import sys
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root / "src"))

from digital_scribe.models.census_1880 import DITTO_MARKS, DITTOABLE_FIELDS
from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

SALEM_IMAGE = "sample_data/1880_Salem_Page1.jpg"
ROW_INDEX = 5  # Row 5 — handwriting typically clear; may contain ditto marks


async def main() -> None:
    """Salem Smoke Test: transcribe Row 5 and print full Census1880Record JSON."""
    server_params = StdioServerParameters(
        command="uv",
        args=["run", "python", "-m", "digital_scribe"],
        cwd=project_root,
    )

    async with stdio_client(server_params) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()

            print(f"Salem Smoke Test: {SALEM_IMAGE}, Row {ROW_INDEX}")
            print("-" * 60)

            result = await session.call_tool(
                "transcribe_census_row",
                arguments={
                    "image_path": SALEM_IMAGE,
                    "row_index": ROW_INDEX,
                },
            )

            if result.isError:
                print(f"Error: {result}", file=sys.stderr)
                sys.exit(1)

            content = result.content
            if not content:
                print("No content in result", file=sys.stderr)
                sys.exit(1)

            record = None
            for block in content:
                if hasattr(block, "structuredContent") and block.structuredContent:
                    record = block.structuredContent
                    break
                if hasattr(block, "text") and block.text:
                    try:
                        record = json.loads(block.text)
                        break
                    except json.JSONDecodeError:
                        record = {"_raw": block.text}
                        break

            if record is None:
                print("No content in result", file=sys.stderr)
                sys.exit(1)

            print("Full Census1880Record (JSON):")
            print(json.dumps(record, indent=2))

            # Ditto verification: use canonical DITTO_MARKS; includes marital_status
            for field in DITTOABLE_FIELDS:
                val = record.get(field, "")
                if val in DITTO_MARKS:
                    print(f"\n[Ditto detected] {field}: {val!r} → post-processor should resolve")


if __name__ == "__main__":
    asyncio.run(main())
