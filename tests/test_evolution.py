"""
Unit tests for the CKS evolution module (CKS‑004).
"""

import pytest

from cks.core import (
    CanonicalRelation,
    KnowledgeObject,
    KnowledgeStructure,
    ObjectIdentity,
)
from cks.evolution import (
    AddObject,
    AddRelation,
    RemoveObject,
    RemoveRelation,
    UpdateObject,
    compose,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_obj(oid: str, otype: str = "Definition", name: str = "") -> KnowledgeObject:
    return KnowledgeObject(
        identity=ObjectIdentity(id=oid, type=otype, name=name or oid)
    )


def _make_rel(
    oid: str,
    participants: list[str],
    relation_type: str = "depends_on",
) -> CanonicalRelation:
    return CanonicalRelation(
        identity=ObjectIdentity(id=oid, type="Relation", name=oid),
        participants=participants,
        relation_type=relation_type,
    )


def _make_structure() -> KnowledgeStructure:
    return KnowledgeStructure([
        _make_obj("obj-1"),
        _make_obj("obj-2"),
        _make_rel("rel-1", ["obj-1", "obj-2"]),
    ])


# ---------------------------------------------------------------------------
# AddObject
# ---------------------------------------------------------------------------

def test_add_object():
    structure = _make_structure()
    new_obj = _make_obj("obj-3", "Lemma", "New Lemma")
    op = AddObject(new_obj)
    result = op.apply(structure)
    assert result.get("obj-3") is not None
    assert len(result.objects) == len(structure.objects) + 1


def test_add_duplicate_object_raises():
    structure = _make_structure()
    duplicate = _make_obj("obj-1")
    op = AddObject(duplicate)
    with pytest.raises(ValueError, match="already exists"):
        op.apply(structure)


# ---------------------------------------------------------------------------
# AddRelation
# ---------------------------------------------------------------------------

def test_add_relation():
    structure = _make_structure()
    new_rel = _make_rel("rel-2", ["obj-1", "obj-2"], "derives")
    op = AddRelation(new_rel)
    result = op.apply(structure)
    assert result.get("rel-2") is not None
    assert len(result.relations()) == len(structure.relations()) + 1


def test_add_relation_missing_participant_raises():
    structure = _make_structure()
    bad_rel = _make_rel("rel-bad", ["obj-1", "missing"])
    op = AddRelation(bad_rel)
    with pytest.raises(ValueError, match="does not exist"):
        op.apply(structure)


def test_add_duplicate_relation_raises():
    structure = _make_structure()
    duplicate = _make_rel("rel-1", ["obj-1", "obj-2"])
    op = AddRelation(duplicate)
    with pytest.raises(ValueError, match="already exists"):
        op.apply(structure)


def test_parse_operations_rejects_string_participants():
    """
    Regression test for the exact dict-based path evolve_knowledge
    routes through: cks.evolution.parse_operations had no participants
    validation of its own for 'add_relation' (unlike
    CanonicalDeserializer in serialization.py), relying entirely on
    CanonicalRelation's constructor. A caller-supplied
    'participants': 'earth' used to be silently accepted and turned
    into a corrupted five-participant relation
    ('e', 'a', 'r', 't', 'h') instead of raising.
    """
    from cks.evolution import parse_operations

    with pytest.raises(TypeError, match="not a bare str"):
        parse_operations([
            {
                "type": "add_relation",
                "identity": {"id": "rel-x", "type": "Relation", "name": "r"},
                "participants": "earth",
                "relation_type": "orbits",
            }
        ])


# ---------------------------------------------------------------------------
# RemoveObject
# ---------------------------------------------------------------------------

def test_remove_object():
    structure = _make_structure()
    op = RemoveObject("obj-1")
    result = op.apply(structure)
    assert result.get("obj-1") is None
    # relation referencing obj-1 should also be removed
    assert result.get("rel-1") is None
    assert len(result.objects) == 1  # only obj-2 remains


def test_remove_nonexistent_object_raises():
    structure = _make_structure()
    op = RemoveObject("missing")
    with pytest.raises(ValueError, match="does not exist"):
        op.apply(structure)


# ---------------------------------------------------------------------------
# RemoveRelation
# ---------------------------------------------------------------------------

def test_remove_relation():
    structure = _make_structure()
    op = RemoveRelation("rel-1")
    result = op.apply(structure)
    assert result.get("rel-1") is None
    assert len(result.relations()) == 0


def test_remove_nonexistent_relation_raises():
    structure = _make_structure()
    op = RemoveRelation("missing")
    with pytest.raises(ValueError, match="does not exist"):
        op.apply(structure)


def test_remove_relation_on_object_id_raises():
    """
    Regression test: RemoveRelation must reject an id that belongs to
    a plain KnowledgeObject rather than a CanonicalRelation. Silently
    accepting it would remove the object without cascading to
    relations that reference it, leaving a dangling reference behind.
    """
    structure = _make_structure()
    op = RemoveRelation("obj-1")
    with pytest.raises(TypeError, match="KnowledgeObject, not a"):
        op.apply(structure)
    # Nothing should have been removed.
    assert structure.get("obj-1") is not None
    assert structure.get("rel-1") is not None


# ---------------------------------------------------------------------------
# UpdateObject
# ---------------------------------------------------------------------------

def test_update_object_merge_mode_overwrites_and_preserves_keys():
    structure = KnowledgeStructure([
        KnowledgeObject(
            identity=ObjectIdentity(id="obj-1", type="Definition", name="obj-1"),
            structure={"content": "old", "tags": ["a"]},
        ),
        _make_obj("obj-2"),
        _make_rel("rel-1", ["obj-1", "obj-2"]),
    ])
    op = UpdateObject("obj-1", {"content": "new"})  # mode="merge" by default
    result = op.apply(structure)
    updated = result.get("obj-1")
    assert updated.structure["content"] == "new"
    assert updated.structure["tags"] == ("a",)  # untouched key survives (canonicalized to a tuple)


def test_update_object_merge_mode_none_removes_key():
    structure = KnowledgeStructure([
        KnowledgeObject(
            identity=ObjectIdentity(id="obj-1", type="Definition", name="obj-1"),
            structure={"content": "old", "scratch": "drop me"},
        ),
    ])
    op = UpdateObject("obj-1", {"scratch": None})
    result = op.apply(structure)
    assert "scratch" not in result.get("obj-1").structure
    assert result.get("obj-1").structure["content"] == "old"


def test_update_object_replace_mode():
    structure = KnowledgeStructure([
        KnowledgeObject(
            identity=ObjectIdentity(id="obj-1", type="Definition", name="obj-1"),
            structure={"content": "old", "tags": ["a"]},
        ),
    ])
    op = UpdateObject("obj-1", {"content": "new"}, mode="replace")
    result = op.apply(structure)
    assert result.get("obj-1").structure == {"content": "new"}


def test_update_object_preserves_relations_without_cascade():
    structure = _make_structure()
    op = UpdateObject("obj-1", {"note": "renamed content"})
    result = op.apply(structure)
    # The relation referencing obj-1 must survive untouched -- this is
    # the whole point of UpdateObject over remove_object + add_object.
    assert result.get("rel-1") is not None
    assert len(result.objects) == len(structure.objects)


def test_update_object_identity_unchanged():
    structure = _make_structure()
    original_identity = structure.get("obj-1").identity
    op = UpdateObject("obj-1", {"note": "x"})
    result = op.apply(structure)
    assert result.get("obj-1").identity == original_identity


def test_update_nonexistent_object_raises():
    structure = _make_structure()
    op = UpdateObject("missing", {"content": "x"})
    with pytest.raises(ValueError, match="does not exist"):
        op.apply(structure)


def test_update_object_on_relation_id_raises():
    structure = _make_structure()
    op = UpdateObject("rel-1", {"relation_type": "x"})
    with pytest.raises(TypeError, match="CanonicalRelation"):
        op.apply(structure)


def test_update_object_unknown_mode_raises():
    with pytest.raises(ValueError, match="Unknown update mode"):
        UpdateObject("obj-1", {"content": "x"}, mode="bogus")


# ---------------------------------------------------------------------------
# Compose
# ---------------------------------------------------------------------------

def test_compose_multiple_operators():
    structure = _make_structure()
    ops = [
        AddObject(_make_obj("obj-3", "Lemma")),
        AddRelation(_make_rel("rel-2", ["obj-2", "obj-3"], "derives")),
        RemoveObject("obj-1"),
    ]
    result = compose(structure, ops)
    assert result.get("obj-1") is None
    assert result.get("rel-1") is None  # removed because obj-1 removed
    assert result.get("obj-3") is not None
    assert result.get("rel-2") is not None
    assert len(result.objects) == 3  # obj-2, obj-3, rel-2


def test_compose_rollback_on_error():
    """Composition stops at the first error, but prior changes are committed."""
    structure = _make_structure()
    ops = [
        AddObject(_make_obj("obj-3")),
        AddRelation(_make_rel("bad", ["obj-1", "missing"])),  # fails
        RemoveObject("obj-2"),
    ]
    with pytest.raises(ValueError, match="does not exist"):
        compose(structure, ops)
    # Prior AddObject should have been committed, so obj-3 exists,
    # but RemoveObject was never reached.
    # Note: compose currently has no transaction/rollback, so we just verify
    # the error is raised.  This test documents the current behavior.