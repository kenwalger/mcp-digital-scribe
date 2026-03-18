# 🏛️ The Digital Scribe

**The Digital Scribe** is a reference implementation for a sovereign, high-integrity historical ingestion pipeline. Moving beyond simple digital archiving, it uses the **Model Context Protocol (MCP)** to bridge the gap between fragile 19th-century artifacts and modern, searchable knowledge graphs.

This repository demonstrates how to build a **"Clean-Room Ingestion"** architecture: using local perception (Multimodal Vision/HTR) for privacy and edge-processing, while utilizing frontier cloud reasoning for historical synthesis.

The project uses a **pure Python stack** with [uv](https://docs.astral.sh/uv/) for dependency management.

## 🛠️ Key Architectural Patterns
- **Temporal HTR:** Specialized Handwriting Text Recognition tools for 19th-century cursive (focused on 1880 U.S. Census records).
- **Spatial Metadata Extraction:** Using MCP to analyze 3D photogrammetry models for condition grading and physical wear analysis.
- **The Contextual Cross-Referencer:** An MCP tool-chain that enriches ingested names/places with historical records from public APIs.
- **Sovereign Ingestion:** Protecting data integrity from the moment of capture using the **Sovereign Redactor** and **Guardian** patterns.

## 📊 The Social Graph (Non-Nuclear Relationships)

The Digital Scribe models household structure as a **Social Graph**, not just genealogy. Beyond nuclear family ties, it captures the full extended household: boarders, servants, employees, and cooks who shared a dwelling with the census Head.

### Relationship Types

- **Nuclear Family**: Wife → `spouse` link to Head; Son/Daughter → `parent` link to Head. The original census term (e.g. "Wife") is preserved in `relationshipDescription`.
- **Extended Household**: Boarder, Servant, Employee, Cook → `memberOfHousehold` (linking to the Head's `@id`), `schema:knows` link, and `relationshipDescription` for the census term.

### Tools

- **search_by_dwelling**: Returns everyone in the same physical building — critical for Post 4.3's "Mapping the Block" narrative (multi-family dwellings).
- **link_household_relationships**: Groups residents by `family_number` (handles multiple heads in one dwelling), creates semantic links. Supports a Dry Run mode to verify proposed links before committing to the graph.

## 🗺️ Post Roadmap
1. **Post 1: The Census Specialist** — Building a Temporal HTR pipeline for 1880 handwritten ledgers.
2. **Post 2: The Knowledge Graph Ingestor** — Moving from flat tables to agentic historical cross-referencing.
3. **Post 3: Spatial Forensics** — Analyzing texture and geometry from Met Museum Photogrammetry sets.
4. **Post 4: The Durable Archive** — Why protocol-driven ingestion is the only way to build for a 100-year horizon.

## 🚀 Quick Start (Coming Soon)
*Instructions for connecting to the local Census HTR server and museum metadata tools will be added in Post 4.1.*