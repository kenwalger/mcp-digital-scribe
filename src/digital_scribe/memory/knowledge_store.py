"""JSON-LD Knowledge Store — Semantic Memory layer for Census1880Record persistence.

Transforms census records into Schema.org Person entities and persists them
to a file-based Knowledge Archive. Aligned with Schema.org standards for
interoperability. Enables cross-referencing by familyName or censusFamilyNumber.
"""

import hashlib
import json
import os
import threading
import uuid
from pathlib import Path

from digital_scribe.models.census_1880 import Census1880Record, DITTO_MARKS, DITTOABLE_FIELDS


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
        parts = [p.strip() for p in s.split(",", 1)]
        if len(parts) == 2 and parts[0] and parts[1]:
            return (parts[1], parts[0])  # givenName, familyName

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
    - name → givenName + familyName (split by first space)
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
        """Load existing entities from the archive file."""
        if not self._path.exists():
            return []
        text = self._path.read_text(encoding="utf-8")
        if not text.strip():
            return []
        # Support both JSON array and JSON-LD graph (single object with @graph)
        data = json.loads(text)
        if isinstance(data, list):
            return data
        if isinstance(data, dict) and "@graph" in data:
            return data["@graph"]
        return [data] if isinstance(data, dict) else []

    def _save_graph(self, entities: list[dict]) -> None:
        """Persist entities using write-to-temp + os.replace for atomic writes."""
        tmp_path = self._path.with_suffix(self._path.suffix + ".tmp")
        try:
            tmp_path.write_text(
                json.dumps(entities, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
            os.replace(tmp_path, self._path)
        finally:
            if tmp_path.exists():
                tmp_path.unlink()

    def ingest(self, record: Census1880Record) -> str:
        """Ingest a Census1880Record, transform to JSON-LD, append to archive. Returns entity @id.

        Knowledge Stewardship: Rejects records with unresolved ditto marks.
        Call resolve_ditto_marks(previous_record) before ingest.
        Atomic: uses Lock + write-to-temp + os.replace to prevent corruption.
        """
        for field in DITTOABLE_FIELDS:
            val = getattr(record, field)
            if val in DITTO_MARKS:
                raise ValueError(
                    f"Knowledge Stewardship: resolve ditto marks before ingest. "
                    f"Field '{field}' contains raw ditto {val!r}."
                )
        entity_id = f"urn:uuid:{uuid.uuid4()}"
        entity = _record_to_jsonld_entity(record, entity_id)
        if "@id" not in entity or not entity["@id"].startswith("urn:uuid:"):
            raise RuntimeError("Entity must have valid urn:uuid:@id before persistence")
        with self._lock:
            entities = self._load_graph()
            entities.append(entity)
            self._save_graph(entities)
        return entity_id

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
        def _content_hash(entity: dict) -> str:
            return hashlib.md5(
                json.dumps(entity, sort_keys=True).encode(),
                usedforsecurity=False,
            ).hexdigest()

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
                    eid = f"urn:uuid:legacy-{_content_hash(e)}"
                    e = {**e, "@id": eid}
                if eid not in seen_ids:
                    seen_ids.add(eid)
                    results.append(e)
        return results
