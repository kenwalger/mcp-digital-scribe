"""Test script: connects to the local Temporal HTR MCP server and transcribes Row 1.

Run from project root:
    uv run python examples/test_server.py

Spawns the server via stdio (subprocess); transcribes Row 1 of a Salem census
page from sample_data/.
"""

import asyncio
import json
import sys
from pathlib import Path

# Add project root so digital_scribe is importable when run directly
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root / "src"))

from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client


async def main() -> None:
    """Connect to Temporal HTR server, transcribe row 1 of a Salem census image."""
    server_params = StdioServerParameters(
        command="uv",
        args=["run", "python", "-m", "digital_scribe"],
        cwd=project_root,
    )

    async with stdio_client(server_params) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()

            # Transcribe Row 1 (index 0) of 1880 Salem census page
            result = await session.call_tool(
                "transcribe_census_row",
                arguments={
                    "image_path": "sample_data/1880A_hi.jpg",
                    "row_index": 0,
                },
            )

            if result.isError:
                print(f"Error: {result}", file=sys.stderr)
                sys.exit(1)

            content = result.content
            if content:
                for block in content:
                    if hasattr(block, "text") and block.text:
                        print("Transcription result (Row 1):")
                        print(block.text)
                    elif hasattr(block, "structuredContent") and block.structuredContent:
                        print("Transcription result (Row 1):")
                        print(json.dumps(block.structuredContent, indent=2))
            else:
                print("No content in result", file=sys.stderr)
                sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
