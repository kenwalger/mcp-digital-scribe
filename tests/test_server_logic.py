"""Server logic tests — transcribe_census_row, ingest_resident, and error handling."""

import hashlib
import os

import pytest

from digital_scribe.server import (
    cross_reference_resident,
    ingest_resident,
    link_household_relationships,
    search_by_dwelling,
    transcribe_census_row,
)


def test_transcribe_rejects_negative_row_index() -> None:
    """transcribe_census_row raises ValueError for row_index < 0."""
    with pytest.raises(ValueError, match="row_index must be >= 0"):
        transcribe_census_row("sample_data/1880_Salem_Page1.jpg", -1)


def test_transcribe_raises_file_not_found_for_missing_image() -> None:
    """transcribe_census_row raises FileNotFoundError with clear message for non-existent path."""
    with pytest.raises(FileNotFoundError, match="Image not found"):
        transcribe_census_row("sample_data/nonexistent_ghost.jpg", 0)


def test_transcribe_accepts_relative_path_when_file_exists() -> None:
    """transcribe_census_row resolves relative paths against project root."""
    result = transcribe_census_row("sample_data/1880_Salem_Page1.jpg", 0)
    assert "name" in result
    assert "handwriting_confidence" in result
    assert 0.75 <= result["handwriting_confidence"] <= 1.0


def test_transcribe_raises_access_denied_for_path_traversal() -> None:
    """transcribe_census_row raises PermissionError when path escapes data directory."""
    with pytest.raises(PermissionError, match="Access Denied"):
        transcribe_census_row("sample_data/../../../etc/passwd", 0)


def test_transcribe_raises_access_denied_for_absolute_path() -> None:
    """transcribe_census_row raises PermissionError for absolute paths."""
    with pytest.raises(PermissionError, match="Access Denied"):
        transcribe_census_row("/etc/passwd", 0)


def test_ingest_rejects_unresolved_ditto_marks() -> None:
    """ingest_resident raises ValueError when record contains raw ditto (Knowledge Stewardship)."""
    record_with_ditto = {
        "dwelling_number": 1,
        "family_number": 1,
        "name": "Mary",
        "relationship_to_head": "Wife",
        "marital_status": "Married",
        "occupation": "do.",
        "birthplace": "New York",
        "handwriting_confidence": 0.9,
    }
    with pytest.raises(ValueError, match="Knowledge Stewardship.*resolve ditto"):
        ingest_resident(record_with_ditto)


def test_ingest_and_recall_success() -> None:
    """ingest_resident persists a valid record; cross_reference_resident retrieves it."""
    record = {
        "dwelling_number": 1,
        "family_number": 2,
        "name": "Test Person",
        "relationship_to_head": "Head",
        "marital_status": "Married",
        "occupation": "Clerk",
        "birthplace": "Ohio",
        "handwriting_confidence": 0.95,
    }
    ingest_result = ingest_resident(record)
    assert ingest_result.get("status") == "ingested"
    assert ingest_result.get("id", "").startswith("urn:uuid:")

    recall_result = cross_reference_resident(surname="Person")
    assert recall_result.get("count", 0) >= 1
    residents = recall_result.get("residents", [])
    found = next(
        (r for r in residents if (r.get("familyName") or "").lower() == "person"),
        None,
    )
    assert found is not None
    assert found.get("givenName") == "Test"
    assert found.get("familyName") == "Person"


def test_social_graph_links() -> None:
    """Ingest Head (Farmer) and Boarder (Blacksmith), link household, verify memberOfHousehold."""
    head_record = {
        "dwelling_number": 5,
        "family_number": 3,
        "name": "John Farmer",
        "relationship_to_head": "Head",
        "marital_status": "Married",
        "occupation": "Farmer",
        "birthplace": "Ohio",
        "handwriting_confidence": 0.9,
    }
    boarder_record = {
        "dwelling_number": 5,
        "family_number": 3,
        "name": "Tom Blacksmith",
        "relationship_to_head": "Boarder",
        "marital_status": "Single",
        "occupation": "Blacksmith",
        "birthplace": "Ireland",
        "handwriting_confidence": 0.85,
    }
    ingest_resident(head_record)
    ingest_resident(boarder_record)

    result = link_household_relationships(dwelling_number=5, dry_run=False)
    assert result.get("status") == "linked"
    assert result.get("families") == 1
    assert result.get("links_created") == 3

    recall = cross_reference_resident(family_number=3)
    residents = recall.get("residents", [])
    blacksmith = next(
        (r for r in residents if (r.get("hasOccupation", {}).get("name") == "Blacksmith")),
        None,
    )
    assert blacksmith is not None
    moh = blacksmith.get("memberOfHousehold")
    member_of = moh[0] if isinstance(moh, list) and moh else (moh if isinstance(moh, dict) else None)
    assert member_of is not None
    assert member_of.get("@id") is not None

    farmer = next(
        (r for r in residents if (r.get("hasOccupation", {}).get("name") == "Farmer")),
        None,
    )
    assert farmer is not None
    assert member_of.get("@id") == farmer.get("@id")
    assert member_of.get("relationshipDescription") == "Boarder"
    knows = blacksmith.get("knows")
    head_knows_ref = next(
        (k for k in (knows if isinstance(knows, list) else [knows]) if isinstance(k, dict) and k.get("@id") == farmer.get("@id")),
        None,
    )
    assert head_knows_ref is not None, "Boarder must have knows link to Head"
    assert head_knows_ref.get("relationshipDescription") == "Boarder", "relationshipDescription in persisted knows"


def test_multi_relation_household() -> None:
    """Ingest Head, Wife, two Boarders; verify symmetric spouse, Head knows both, no data loss."""
    head_record = {
        "dwelling_number": 7,
        "family_number": 4,
        "name": "George Head",
        "relationship_to_head": "Head",
        "marital_status": "Married",
        "occupation": "Farmer",
        "birthplace": "Ohio",
        "handwriting_confidence": 0.9,
    }
    wife_record = {
        "dwelling_number": 7,
        "family_number": 4,
        "name": "Martha Head",
        "relationship_to_head": "Wife",
        "marital_status": "Married",
        "occupation": "Keeping House",
        "birthplace": "Pennsylvania",
        "handwriting_confidence": 0.92,
    }
    boarder1_record = {
        "dwelling_number": 7,
        "family_number": 4,
        "name": "Joe Boarder",
        "relationship_to_head": "Boarder",
        "marital_status": "Single",
        "occupation": "Laborer",
        "birthplace": "Ireland",
        "handwriting_confidence": 0.85,
    }
    boarder2_record = {
        "dwelling_number": 7,
        "family_number": 4,
        "name": "Kate Boarder",
        "relationship_to_head": "Boarder",
        "marital_status": "Single",
        "occupation": "Servant",
        "birthplace": "Germany",
        "handwriting_confidence": 0.88,
    }
    ingest_resident(head_record)
    ingest_resident(wife_record)
    ingest_resident(boarder1_record)
    ingest_resident(boarder2_record)

    result = link_household_relationships(dwelling_number=7, dry_run=False)
    assert result.get("status") == "linked"
    assert result.get("families") == 1
    assert result.get("links_created") == 8

    recall = cross_reference_resident(family_number=4)
    residents = recall.get("residents", [])
    head = next(
        (r for r in residents if (r.get("hasOccupation", {}).get("name") == "Farmer")),
        None,
    )
    wife = next(
        (r for r in residents if (r.get("givenName") == "Martha" and r.get("familyName") == "Head")),
        None,
    )
    boarder1 = next(
        (r for r in residents if (r.get("givenName") == "Joe" and r.get("familyName") == "Boarder")),
        None,
    )
    boarder2 = next(
        (r for r in residents if (r.get("givenName") == "Kate" and r.get("familyName") == "Boarder")),
        None,
    )
    assert head is not None
    assert wife is not None
    assert boarder1 is not None
    assert boarder2 is not None

    head_id = head.get("@id")
    wife_id = wife.get("@id")

    def _spouse_refs(person: dict) -> list[dict]:
        s = person.get("spouse")
        if s is None:
            return []
        if isinstance(s, list):
            return [x for x in s if isinstance(x, dict) and x.get("@id")]
        return [s] if isinstance(s, dict) and s.get("@id") else []

    head_spouses = _spouse_refs(head)
    wife_spouses = _spouse_refs(wife)
    assert any(s.get("@id") == wife_id for s in head_spouses), "Head must have spouse link to Wife"
    assert any(s.get("@id") == head_id for s in wife_spouses), "Wife must have spouse link to Head"

    def _knows_ids(person: dict) -> list[str]:
        k = person.get("knows")
        if k is None:
            return []
        if isinstance(k, list):
            return [
                x.get("@id") for x in k
                if isinstance(x, dict) and x.get("@id")
            ]
        return [k.get("@id")] if isinstance(k, dict) and k.get("@id") else []

    head_knows = _knows_ids(head)
    assert boarder1.get("@id") in head_knows, "Head must know Boarder1"
    assert boarder2.get("@id") in head_knows, "Head must know Boarder2"
    assert len(head_knows) == 2, "Head has exactly two knows entries (both Boarders, no overwrite)"

    def _moh_head_id(person: dict) -> str | None:
        moh = person.get("memberOfHousehold")
        if isinstance(moh, list) and moh and isinstance(moh[0], dict):
            return moh[0].get("@id")
        return moh.get("@id") if isinstance(moh, dict) else None

    assert _moh_head_id(boarder1) == head_id
    assert _moh_head_id(boarder2) == head_id

    def _first_moh(entity: dict) -> dict | None:
        moh = entity.get("memberOfHousehold")
        if isinstance(moh, list) and moh and isinstance(moh[0], dict):
            return moh[0]
        return moh if isinstance(moh, dict) else None

    for b in (boarder1, boarder2):
        moh = _first_moh(b)
        assert moh is not None and moh.get("relationshipDescription") == "Boarder"
        knows = b.get("knows")
        k = next((x for x in (knows if isinstance(knows, list) else [knows]) if isinstance(x, dict) and x.get("@id") == head_id), None)
        assert k is not None and k.get("relationshipDescription") == "Boarder"


def test_dry_run_symmetry() -> None:
    """Proposed links includes symmetric back-links (e.g., Head->Wife and Wife->Head)."""
    ingest_resident({
        "dwelling_number": 11,
        "family_number": 7,
        "name": "Husband Test",
        "relationship_to_head": "Head",
        "marital_status": "Married",
        "occupation": "Farmer",
        "birthplace": "Ohio",
        "handwriting_confidence": 0.9,
    })
    ingest_resident({
        "dwelling_number": 11,
        "family_number": 7,
        "name": "Wife Test",
        "relationship_to_head": "Wife",
        "marital_status": "Married",
        "occupation": "Keeping House",
        "birthplace": "Pennsylvania",
        "handwriting_confidence": 0.92,
    })
    result = link_household_relationships(dwelling_number=11, dry_run=True)
    assert result.get("status") == "dry_run"
    proposed = result.get("proposed_links", [])
    spouse_links = [p for p in proposed if p.get("link_type") == "spouse"]
    assert len(spouse_links) == 2, "Husband/Wife pair must produce two spouse links (forward + back)"
    from_ids = {p["from_id"] for p in spouse_links}
    to_ids = {p["to_id"] for p in spouse_links}
    assert len(from_ids) == 2 and len(to_ids) == 2
    assert from_ids == to_ids, "Symmetric: from_ids and to_ids must be the same set"


def test_link_household_dry_run() -> None:
    """Dry run returns proposed links but does NOT modify the archive on disk."""
    record = {
        "dwelling_number": 9,
        "family_number": 6,
        "name": "Dry Run Family",
        "relationship_to_head": "Head",
        "marital_status": "Married",
        "occupation": "Farmer",
        "birthplace": "Ohio",
        "handwriting_confidence": 0.9,
    }
    ingest_resident(record)
    ingest_resident({
        **record,
        "name": "Wife Dry",
        "relationship_to_head": "Wife",
        "occupation": "Keeping House",
    })

    archive_path = os.environ.get("DIGITAL_SCRIBE_ARCHIVE_PATH")
    assert archive_path, "DIGITAL_SCRIBE_ARCHIVE_PATH must be set by conftest"
    with open(archive_path, "rb") as f:
        content_before = f.read()
    hash_before = hashlib.sha256(content_before).hexdigest()

    result = link_household_relationships(dwelling_number=9, dry_run=True)
    assert result.get("status") == "dry_run"
    assert "proposed_links" in result
    assert len(result.get("proposed_links", [])) >= 1

    with open(archive_path, "rb") as f:
        content_after = f.read()
    hash_after = hashlib.sha256(content_after).hexdigest()
    assert hash_before == hash_after, "Archive must be unchanged after dry run"


def test_search_by_dwelling_tool() -> None:
    """search_by_dwelling returns structured error for dwelling_number < 1."""
    for invalid in (0, -1):
        result = search_by_dwelling(invalid)
        assert result.get("status") == "error"
        assert "message" in result
        assert "dwelling_number" in result.get("message", "").lower()


def test_link_invalid_dwelling_id() -> None:
    """link_household_relationships returns structured error for dwelling_number < 1."""
    for invalid in (0, -1):
        result = link_household_relationships(dwelling_number=invalid)
        assert result.get("status") == "error"
        assert "message" in result
        assert "dwelling_number" in result.get("message", "").lower()


def test_link_multi_family_dwelling_atomicity() -> None:
    """Two families in one dwelling; both linked correctly in a single tool call."""
    dwelling = 10
    ingest_resident({
        "dwelling_number": dwelling,
        "family_number": 8,
        "name": "Adam Alpha",
        "relationship_to_head": "Head",
        "marital_status": "Married",
        "occupation": "Farmer",
        "birthplace": "Ohio",
        "handwriting_confidence": 0.9,
    })
    ingest_resident({
        "dwelling_number": dwelling,
        "family_number": 8,
        "name": "Eve Alpha",
        "relationship_to_head": "Wife",
        "marital_status": "Married",
        "occupation": "Keeping House",
        "birthplace": "Pennsylvania",
        "handwriting_confidence": 0.92,
    })
    ingest_resident({
        "dwelling_number": dwelling,
        "family_number": 9,
        "name": "Bob Beta",
        "relationship_to_head": "Head",
        "marital_status": "Single",
        "occupation": "Laborer",
        "birthplace": "Ireland",
        "handwriting_confidence": 0.88,
    })
    ingest_resident({
        "dwelling_number": dwelling,
        "family_number": 9,
        "name": "Carl Boarder",
        "relationship_to_head": "Boarder",
        "marital_status": "Single",
        "occupation": "Servant",
        "birthplace": "Germany",
        "handwriting_confidence": 0.85,
    })

    result = link_household_relationships(dwelling_number=dwelling, dry_run=False)
    assert result.get("status") == "linked"
    assert result.get("families") == 2

    fam8 = cross_reference_resident(family_number=8)
    fam9 = cross_reference_resident(family_number=9)
    residents_8 = fam8.get("residents", [])
    residents_9 = fam9.get("residents", [])

    adam = next((r for r in residents_8 if (r.get("hasOccupation") or {}).get("name") == "Farmer"), None)
    eve = next((r for r in residents_8 if (r.get("hasOccupation") or {}).get("name") == "Keeping House"), None)
    bob = next((r for r in residents_9 if (r.get("hasOccupation") or {}).get("name") == "Laborer"), None)
    carl = next((r for r in residents_9 if (r.get("hasOccupation") or {}).get("name") == "Servant"), None)

    assert adam is not None and eve is not None
    assert bob is not None and carl is not None

    def _spouse_ids(p: dict) -> list[str]:
        s = p.get("spouse")
        if isinstance(s, list):
            return [x.get("@id") for x in s if isinstance(x, dict) and x.get("@id")]
        return [s.get("@id")] if isinstance(s, dict) and s.get("@id") else []

    assert eve.get("@id") in _spouse_ids(adam)
    assert adam.get("@id") in _spouse_ids(eve)

    def _moh_id(p: dict) -> str | None:
        moh = p.get("memberOfHousehold")
        if isinstance(moh, list) and moh:
            return moh[0].get("@id") if isinstance(moh[0], dict) else None
        return moh.get("@id") if isinstance(moh, dict) else None

    assert _moh_id(carl) == bob.get("@id")
