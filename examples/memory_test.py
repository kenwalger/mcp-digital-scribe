"""Memory-Aware Agent Test — full lifecycle: Capture → Resolve → Ingest → Recall.

Demonstrates the Agentic Memory architecture (research/agentic_memory.md):
1. Capture: Transcribe rows via transcribe_census_row
2. Resolve: Apply resolve_ditto_marks (Episodic Memory)
3. Ingest: Save to JSONLDStore via ingest_resident (Persistence)
4. Recall: Call cross_reference_resident (Semantic Memory)

Validation: Two consecutive rows with the same family_number; the second
row successfully recalls the first from the Semantic Memory layer.

Uses data/memory_test_run.jsonld (fresh, non-tracked; never production archive).
Run from project root:
    uv run python examples/memory_test.py
"""

import asyncio
import json
import os
import sys
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root / "src"))

from digital_scribe.models.census_1880 import Census1880Record
from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

SALEM_IMAGE = "sample_data/1880_Salem_Page1.jpg"
TEST_ARCHIVE = project_root / "data" / "memory_test_run.jsonld"
# Rows 0 and 1 share family_number=1 in the mock; second can recall first
ROW_INDICES = (0, 1)


def _extract_record_from_result(result) -> dict | None:
    """Extract Census1880Record dict from MCP tool result."""
    if result.isError or not result.content:
        return None
    for block in result.content:
        if hasattr(block, "structuredContent") and block.structuredContent:
            return block.structuredContent
        if hasattr(block, "text") and block.text:
            try:
                return json.loads(block.text)
            except json.JSONDecodeError:
                pass
    return None


async def main() -> None:
    """Memory-Aware Agent flow: Capture → Resolve → Ingest → Recall."""
    env = os.environ.copy()
    env["DIGITAL_SCRIBE_ARCHIVE_PATH"] = str(TEST_ARCHIVE)
    server_params = StdioServerParameters(
        command="uv",
        args=["run", "python", "-m", "digital_scribe"],
        cwd=project_root,
        env=env,
    )

    async with stdio_client(server_params) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()

            print("Memory-Aware Agent Test")
            print("=" * 60)

            previous_record: Census1880Record | None = None

            for row_idx in ROW_INDICES:
                # 1. Capture
                transcribe = await session.call_tool(
                    "transcribe_census_row",
                    arguments={"image_path": SALEM_IMAGE, "row_index": row_idx},
                )
                record_dict = _extract_record_from_result(transcribe)
                if not record_dict:
                    print(f"Capture failed for row {row_idx}", file=sys.stderr)
                    sys.exit(1)
                record = Census1880Record.model_validate(record_dict)

                # 2. Resolve (Episodic Memory: ditto marks)
                resolved = record.resolve_ditto_marks(previous_record)
                previous_record = resolved

                # 3. Ingest (Persistence)
                ingest = await session.call_tool(
                    "ingest_resident",
                    arguments={"record": resolved.model_dump()},
                )
                if ingest.isError:
                    print(f"Ingest failed for row {row_idx}: {ingest}", file=sys.stderr)
                    sys.exit(1)
                ingest_result = _extract_record_from_result(ingest)
                if not ingest_result:
                    ingest_result = {}
                status = ingest_result.get("status", "?")
                if status == "error":
                    msg = ingest_result.get("message", "Unknown error")
                    print(f"\n{msg}", file=sys.stderr)
                    sys.exit(1)
                entity_id = ingest_result.get("id", ingest_result.get("@id", "?"))
                print(f"Row {row_idx}: {resolved.name} (family {resolved.family_number}) → [{status}] {entity_id}")

            # 4. Recall (Semantic Memory)
            family_num = 1  # Both rows 0 and 1 have family_number=1 in mock
            recall = await session.call_tool(
                "cross_reference_resident",
                arguments={"family_number": family_num},
            )
            recall_data = _extract_record_from_result(recall)
            if not recall_data:
                print("\nRecall failed", file=sys.stderr)
                sys.exit(1)
            if recall_data.get("status") == "error":
                msg = recall_data.get("message", "Unknown error")
                print(f"\n{msg}", file=sys.stderr)
                sys.exit(1)

            count = recall_data.get("count", 0)
            residents = recall_data.get("residents", [])

            print(f"\nRecall (family_number={family_num}): {count} resident(s)")
            for r in residents:
                name = " ".join(filter(None, [r.get("givenName"), r.get("familyName")])) or "?"
                occ = r.get("hasOccupation") or {}
                occ_name = occ.get("name", "?") if isinstance(occ, dict) else "?"
                bp = r.get("birthPlace") or {}
                bp_name = bp.get("name", "?") if isinstance(bp, dict) else "?"
                print(f"  - {name} ({occ_name}, {bp_name})")

            # Validation: second row must have recalled the first
            if count < 2:
                print(f"\nFAIL: Expected ≥2 residents for family {family_num}, got {count}", file=sys.stderr)
                sys.exit(1)
            print("\n✓ Memory lifecycle validated: Capture → Resolve → Ingest → Recall")

            # Social Graph: link household relationships, then fetch fresh data
            dwelling_num = 1
            link_result = await session.call_tool(
                "link_household_relationships",
                arguments={"dwelling_number": dwelling_num},
            )
            link_data = _extract_record_from_result(link_result)
            if link_data and link_data.get("status") in ("linked", "no_links_created"):
                links = link_data.get("links_created", 0)
                print(f"\nSocial Graph (dwelling {dwelling_num}): {links} link(s) created")
                search_result = await session.call_tool(
                    "search_by_dwelling",
                    arguments={"dwelling_number": dwelling_num},
                )
                search_data = _extract_record_from_result(search_result)
                if search_data and search_data.get("status") != "error":
                    dwell_residents = search_data.get("residents", [])
                    id_to_name = {
                        r.get("@id"): " ".join(filter(None, [r.get("givenName"), r.get("familyName")])) or "?"
                        for r in dwell_residents
                    }
                    def _links(r: dict, key: str, label: str) -> list[str]:
                        val = r.get(key)
                        items = val if isinstance(val, list) else ([val] if val else [])
                        return [f"{label}: {id_to_name.get(i['@id'], i['@id'])}" for i in items if isinstance(i, dict) and i.get("@id")]

                    for r in dwell_residents:
                        name = id_to_name.get(r.get("@id"), "?")
                        role = r.get("censusRelationshipToHead", "?")
                        links_info = _links(r, "spouse", "Spouse") + _links(r, "parent", "Parent") + _links(r, "knows", "Knows") + _links(r, "memberOfHousehold", "MemberOfHousehold")
                        line = f"  - {name} ({role})"
                        if links_info:
                            line += " [" + "; ".join(links_info) + "]"
                        print(line)
                # Idempotency: second call on same dwelling creates no new links
                link2_result = await session.call_tool(
                    "link_household_relationships",
                    arguments={"dwelling_number": dwelling_num},
                )
                link2_data = _extract_record_from_result(link2_result)
                if link2_data and link2_data.get("status") == "no_links_created" and link2_data.get("links_created", -1) == 0:
                    print("  (idempotent run: 0 new links)")
            elif link_data and link_data.get("status") == "error":
                print(f"\nSocial Graph: {link_data.get('message', 'Unknown error')}", file=sys.stderr)

            # Verify test archive is valid JSON-LD for Schema Markup Validator
            archive_text = TEST_ARCHIVE.read_text(encoding="utf-8")
            parsed = json.loads(archive_text)
            if not isinstance(parsed, list) or len(parsed) < 2:
                raise RuntimeError(
                    "Archive must be a list with at least 2 entities"
                )
            for ent in parsed[:2]:
                if ent.get("@context") != "https://schema.org/":
                    raise RuntimeError(
                        f"Entity missing @context: {ent.get('@context')!r}"
                    )
                if ent.get("@type") != "Person":
                    raise RuntimeError(
                        f"Entity missing @type Person: {ent.get('@type')!r}"
                    )
                eid = ent.get("@id", "")
                if eid and not (
                    eid.startswith("urn:uuid:") or eid.startswith("urn:digital-scribe:legacy:")
                ):
                    raise RuntimeError(
                        f"Entity @id must be urn:uuid: or urn:digital-scribe:legacy: if present: got {eid!r}"
                    )
            print("✓ data/memory_test_run.jsonld valid JSON-LD (Schema.org Person)")


if __name__ == "__main__":
    asyncio.run(main())
