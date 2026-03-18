"""JSON-LD Knowledge Store — Semantic Memory layer for Census1880Record persistence.

Transforms census records into Schema.org Person entities and persists them
to a file-based Knowledge Archive. Aligned with Schema.org standards for
interoperability. Enables cross-referencing by familyName or censusFamilyNumber.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import threading
import uuid
from collections import defaultdict
from pathlib import Path
from typing import TypedDict

from digital_scribe.models.census_1880 import Census1880Record, DITTO_MARKS, DITTOABLE_FIELDS


class LinkResult(TypedDict):
    """Type-safe result of household linking (write path)."""
    processed_entities: list[dict]
    links_created: int


class DryRunResult(TypedDict):
    """Type-safe result of household linking (dry run path)."""
    proposed_links: list[dict]
    families: int

logger = logging.getLogger(__name__)

LEGACY_ID_PREFIX = "urn:digital-scribe:legacy:"


class ArchiveCorruptionError(RuntimeError):
    """Raised when the knowledge archive file exists but is corrupt (invalid JSON).

    Distinguishes corruption from absence: missing file returns []; corrupt
    file raises to prevent _save_graph from overwriting with empty list.
    """


def _add_to_relation(entity: dict, property_name: str, value: dict) -> bool:
    """Append a relation value without overwriting existing entries.

    If entity[property_name] does not exist, sets it to [value].
    If it is a single string/dict, converts to list with [old, value].
    If already a list, appends value only if not already present (deduplication by @id).

    Returns True if a new pointer was added, False if skipped (duplicate).
    """
    target_id = value.get("@id") if isinstance(value, dict) else None
    if not target_id:
        logger.warning(
            "_add_to_relation called with value missing @id: property=%s, value=%s",
            property_name,
            value,
        )
        return False

    existing = entity.get(property_name)
    if existing is None:
        entity[property_name] = [value]
        return True

    if isinstance(existing, dict):
        if existing.get("@id") == target_id:
            return False
        entity[property_name] = [existing, value]
        return True

    if isinstance(existing, str):
        if existing == target_id:
            return False
        entity[property_name] = [existing, value]
        return True

    if isinstance(existing, list):
        for item in existing:
            if isinstance(item, dict) and item.get("@id") == target_id:
                return False
            if item == target_id:
                return False
        existing.append(value)
        return True
    return False


def _resolve_entity_id(entity: dict) -> str:
    """Return deterministic @id; never null. Uses _content_hash fallback."""
    eid = entity.get("@id")
    if eid and isinstance(eid, str):
        return eid
    return f"{LEGACY_ID_PREFIX}{_content_hash(entity)}"


def _process_family_links(family: list[dict], dry_run: bool) -> tuple[list[dict], int]:
    """Apply linking logic to a family. Mutates when not dry_run. Returns (proposed_links, links_created).

    Dry-run proposed_links is a 1:1 mirror of what would be written: every pointer including
    symmetric back-links (e.g., Head->Spouse, Head->Boarder). IDs use _resolve_entity_id.
    """
    proposed: list[dict] = []
    links_created = 0
    head = next(
        (e for e in family if (e.get("censusRelationshipToHead") or "").strip().lower() == "head"),
        None,
    )
    if not head:
        return (proposed, links_created)
    head_id = _resolve_entity_id(head)

    for entity in family:
        if entity is head:
            continue
        member_id = _resolve_entity_id(entity)
        rel_raw = (entity.get("censusRelationshipToHead") or "").strip()
        rel_lower = rel_raw.lower()

        if rel_lower == "wife":
            proposed.append({
                "from_id": member_id,
                "to_id": head_id,
                "link_type": "spouse",
                "relationshipDescription": rel_raw,
            })
            proposed.append({
                "from_id": head_id,
                "to_id": member_id,
                "link_type": "spouse",
                "relationshipDescription": rel_raw,
            })
            if not dry_run:
                spouse_link = {"@id": head_id, "relationshipDescription": rel_raw}
                spouse_back = {"@id": member_id, "relationshipDescription": rel_raw}
                if _add_to_relation(entity, "spouse", spouse_link):
                    links_created += 1
                if _add_to_relation(head, "spouse", spouse_back):
                    links_created += 1
        elif rel_lower in ("son", "daughter"):
            proposed.append({
                "from_id": member_id,
                "to_id": head_id,
                "link_type": "parent",
                "relationshipDescription": rel_raw,
            })
            if not dry_run:
                if _add_to_relation(entity, "parent", {"@id": head_id, "relationshipDescription": rel_raw}):
                    links_created += 1
        elif rel_lower in ("boarder", "servant", "employee", "cook"):
            proposed.append({
                "from_id": member_id,
                "to_id": head_id,
                "link_type": "memberOfHousehold",
                "relationshipDescription": rel_raw,
            })
            proposed.append({
                "from_id": member_id,
                "to_id": head_id,
                "link_type": "knows",
                "relationshipDescription": rel_raw,
            })
            proposed.append({
                "from_id": head_id,
                "to_id": member_id,
                "link_type": "knows",
                "relationshipDescription": rel_raw,
            })
            if not dry_run:
                moh_val = {"@id": head_id, "relationshipDescription": rel_raw}
                knows_head = {"@id": head_id, "relationshipDescription": rel_raw}
                knows_member = {"@id": member_id, "relationshipDescription": rel_raw}
                if _add_to_relation(entity, "memberOfHousehold", moh_val):
                    links_created += 1
                if _add_to_relation(entity, "knows", knows_head):
                    links_created += 1
                if _add_to_relation(head, "knows", knows_member):
                    links_created += 1
    return (proposed, links_created)


def _content_hash(entity: dict) -> str:
    """Deterministic content hash for legacy entity IDs (usedforsecurity=False for FIPS)."""
    return hashlib.md5(
        json.dumps(entity, sort_keys=True).encode(),
        usedforsecurity=False,
    ).hexdigest()


def _parse_historical_name(full_name: str) -> tuple[str, str]:
    """Parse historical census name into givenName and familyName (Schema.org Person).

    Handles:
    - "Surname, Given Name" (e.g. "Smith, John")
    - Multi-word given names (e.g. "Mary Ann Jones" → givenName="Mary Ann", familyName="Jones")
    - Default "Given Name" order (e.g. "John Smith" → givenName="John", familyName="Smith")
    """
    s = full_name.strip()
    if not s:
        return ("", "")

    # "Surname, Given Name" format
    if "," in s:
        parts = [p.strip().strip(",").strip() for p in s.split(",", 1)]
        if len(parts) == 2:
            given, family = parts[1], parts[0]
            if given or family:
                return (given, family)  # givenName, familyName (may be empty)

    # Default: "Given Name(s) Surname" — last token is familyName
    tokens = s.split()
    if not tokens:
        return ("", "")
    if len(tokens) == 1:
        return (tokens[0], "")
    return (" ".join(tokens[:-1]), tokens[-1])


def _record_to_jsonld_entity(record: Census1880Record, entity_id: str | None = None) -> dict:
    """Transform a Census1880Record into a Schema.org Person JSON-LD entity.

    Mapping:
    - name → parsed into familyName (last token) and givenName (all preceding tokens)
    - occupation → hasOccupation (nested Occupation with name)
    - birthplace → birthPlace (nested Place with name)
    """
    if entity_id is None:
        entity_id = f"urn:uuid:{uuid.uuid4()}"

    given, family = _parse_historical_name(record.name)

    entity = {
        "@context": "https://schema.org/",
        "@type": "Person",
        "@id": entity_id,
        "givenName": given,
        "familyName": family,
        "hasOccupation": {
            "@type": "Occupation",
            "name": record.occupation,
        },
        "birthPlace": {
            "@type": "Place",
            "name": record.birthplace,
        },
        "censusFamilyNumber": record.family_number,
        "censusDwellingNumber": record.dwelling_number,
        "censusRelationshipToHead": record.relationship_to_head,
        "censusMaritalStatus": record.marital_status,
    }
    if not family:
        del entity["familyName"]
    if not given:
        del entity["givenName"]
    return entity


class JSONLDStore:
    """File-based Knowledge Archive for Census1880Record entities as JSON-LD.

    Ingest records, transform to Schema.org Person, persist to a local file.
    Supports search by surname or family_number (Semantic Memory / Recall).
    """

    def __init__(
        self,
        archive_path: str | Path | None = None,
        default_archive_path: str | Path | None = None,
    ) -> None:
        """Resolve archive path at runtime. Respects DIGITAL_SCRIBE_ARCHIVE_PATH env if set after import."""
        resolved = archive_path
        if resolved is None:
            resolved = os.environ.get("DIGITAL_SCRIBE_ARCHIVE_PATH") or default_archive_path
        if resolved is None:
            resolved = Path("data") / "archive.jsonld"
        self._path = Path(resolved)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()

    def _load_graph(self) -> list[dict]:
        """Load existing entities from the archive file.

        Missing file → []. Corrupt JSON → raises ArchiveCorruptionError.
        """
        if not self._path.exists():
            return []
        text = self._path.read_text(encoding="utf-8")
        if not text.strip():
            return []
        try:
            data = json.loads(text)
        except json.JSONDecodeError as e:
            logger.critical("Corrupt archive: %s (%s)", self._path, e)
            raise ArchiveCorruptionError(
                f"Knowledge archive is corrupt: {self._path} ({e})"
            ) from e
        if isinstance(data, list):
            return data
        if isinstance(data, dict) and "@graph" in data:
            return data["@graph"]
        return [data] if isinstance(data, dict) else []

    def _save_graph(self, entities: list[dict]) -> None:
        """Persist entities using write-to-temp + fsync + os.replace for atomic writes."""
        tmp_path = self._path.with_suffix(self._path.suffix + ".tmp")
        replaced = False
        try:
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(entities, f, indent=2, ensure_ascii=False)
                f.write("\n")
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp_path, self._path)
            replaced = True
        finally:
            if not replaced and tmp_path.exists():
                tmp_path.unlink()

    def ingest(self, record: Census1880Record) -> tuple[str, bool]:
        """Ingest a Census1880Record, transform to JSON-LD, append to archive.

        Returns (entity_id, was_created). was_created is False if duplicate skipped.
        Dedup key: (givenName, familyName, censusDwellingNumber, censusFamilyNumber).
        """
        for field in DITTOABLE_FIELDS:
            val = getattr(record, field)
            if val in DITTO_MARKS:
                raise ValueError(
                    f"Knowledge Stewardship: resolve ditto marks before ingest. "
                    f"Field '{field}' contains raw ditto {val!r}."
                )
        given, family = _parse_historical_name(record.name)
        with self._lock:
            entities = self._load_graph()
            for e in entities:
                if (
                    (e.get("givenName") or "") == given
                    and (e.get("familyName") or "") == family
                    and e.get("censusDwellingNumber") == record.dwelling_number
                    and e.get("censusFamilyNumber") == record.family_number
                ):
                    existing_id = e.get("@id")
                    if not existing_id or not isinstance(existing_id, str):
                        existing_id = f"{LEGACY_ID_PREFIX}{_content_hash(e)}"
                    logger.info(
                        "Record already exists, skipping ingest: %s %s (dwelling %s, family %s)",
                        given or "?",
                        family or "?",
                        record.dwelling_number,
                        record.family_number,
                    )
                    return (existing_id, False)
            entity_id = f"urn:uuid:{uuid.uuid4()}"
            entity = _record_to_jsonld_entity(record, entity_id)
            if "@id" not in entity or not entity["@id"].startswith("urn:uuid:"):
                raise RuntimeError(
                    "Entity must have valid urn:uuid:@id before persistence"
                )
            entities.append(entity)
            self._save_graph(entities)
        return (entity_id, True)

    def search_by_surname(self, surname: str) -> list[dict]:
        """Return entities with matching familyName (Schema.org property)."""
        surname_clean = surname.strip()
        if not surname_clean:
            return []
        surname_lower = surname_clean.lower()
        with self._lock:
            entities = self._load_graph()
            return [
                e for e in entities
                if (e.get("familyName") or "").lower() == surname_lower
            ]

    def search_by_family_number(self, family_number: int) -> list[dict]:
        """Return entities with the given censusFamilyNumber."""
        with self._lock:
            entities = self._load_graph()
            return [
                e
                for e in entities
                if e.get("censusFamilyNumber") == family_number
            ]

    def search_by_surname_or_family(
        self,
        surname: str | None = None,
        family_number: int | None = None,
    ) -> list[dict]:
        """Search by surname and/or family_number. Combines results (OR), deduplicated by @id.

        Loads the graph once and filters in-memory for consistent fallback IDs.
        Uses deterministic content-hash for legacy entities without @id.
        """
        if not surname and family_number is None:
            return []
        with self._lock:
            entities = self._load_graph()
            surname_lower = (surname or "").strip().lower() if surname else ""
            candidates: list[dict] = []
            for e in entities:
                match_surname = (
                    bool(surname_lower)
                    and (e.get("familyName") or "").lower() == surname_lower
                )
                match_family = (
                    family_number is not None
                    and family_number >= 1
                    and e.get("censusFamilyNumber") == family_number
                )
                if match_surname or match_family:
                    candidates.append(e)
            seen_ids: set[str] = set()
            results: list[dict] = []
            for e in candidates:
                eid = e.get("@id")
                if not eid or not isinstance(eid, str):
                    eid = f"{LEGACY_ID_PREFIX}{_content_hash(e)}"
                    e = {**e, "@id": eid}
                if eid not in seen_ids:
                    seen_ids.add(eid)
                    results.append(e)
        return results

    def search_by_dwelling(self, dwelling_number: int) -> list[dict]:
        """Return all entities in the given dwelling_number (physical building).

        Primary method for 'Mapping the Block' and multi-family analysis —
        returns everyone in the same physical structure regardless of family unit.
        Handles multi-family dwellings (e.g. two families sharing one building).

        Raises ValueError if dwelling_number < 1 (single source of truth).
        """
        if dwelling_number < 1:
            raise ValueError("dwelling_number must be >= 1")
        with self._lock:
            entities = self._load_graph()
            return [e for e in entities if e.get("censusDwellingNumber") == dwelling_number]

    def link_dwelling(
        self, dwelling_number: int, dry_run: bool = False
    ) -> LinkResult | DryRunResult:
        """Single, atomic entry point for building household relationships in the Knowledge Graph.

        Loads the graph once, links all families in the dwelling in memory, then saves once.
        Multi-family dwellings are updated atomically (all-or-nothing).
        Dry-run path returns DryRunResult with proposed_links and families (always present).
        """
        if dwelling_number < 1:
            raise ValueError("dwelling_number must be >= 1")
        with self._lock:
            entities = self._load_graph()
            residents = [e for e in entities if e.get("censusDwellingNumber") == dwelling_number]
            if not residents:
                return {"proposed_links": [], "families": 0} if dry_run else {"processed_entities": [], "links_created": 0}
            by_family: defaultdict[int, list[dict]] = defaultdict(list)
            for r in residents:
                fn = r.get("censusFamilyNumber")
                if fn is not None and fn >= 1:
                    by_family[fn].append(r)
                else:
                    name = " ".join(filter(None, [r.get("givenName"), r.get("familyName")])) or r.get("name", "?")
                    logger.warning(
                        "Resident excluded from linking: censusFamilyNumber invalid (name=%s, fn=%s)",
                        name,
                        fn,
                    )
            all_proposed: list[dict] = []
            total_links = 0
            for family_number, family_entities in sorted(by_family.items()):
                proposed, count = _process_family_links(family_entities, dry_run)
                for link in proposed:
                    all_proposed.append({**link, "family_number": family_number})
                total_links += count
            if dry_run:
                return {"proposed_links": all_proposed, "families": len(by_family)}
            self._save_graph(entities)
            return {"processed_entities": residents, "links_created": total_links}
