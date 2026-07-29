"""
Unit tests for canonical serialization.

Covers the canonical serialization model defined by CKS-003.

This module tests only serialization and deserialization.
Validation semantics are tested separately.
"""

from __future__ import annotations

import json

import pytest

from cks.core import (
    CanonicalRelation,
    KnowledgeObject,
    KnowledgeStructure,
    ObjectIdentity,
)
from cks.serialization import (
    SerializationError,
    parse,
    serialize,
)

# =============================================================================
# Helper factories
# =============================================================================


def make_object(
    oid: str,
    otype: str = "Definition",
    name: str | None = None,
) -> KnowledgeObject:
    return KnowledgeObject(
        identity=ObjectIdentity(
            id=oid,
            type=otype,
            name=name or oid,
        )
    )


def make_relation(
    oid: str,
    participants: list[str],
    relation_type: str = "depends_on",
) -> CanonicalRelation:
    return CanonicalRelation(
        identity=ObjectIdentity(
            id=oid,
            type="Relation",
            name=oid,
        ),
        participants=participants,
        relation_type=relation_type,
    )


def make_structure() -> KnowledgeStructure:
    return KnowledgeStructure(
        [
            make_object("obj-1"),
            make_object("obj-2"),
            make_relation(
                "rel-1",
                ["obj-1", "obj-2"],
            ),
        ]
    )


# =============================================================================
# Parsing
# =============================================================================


def test_parse_minimal_structure():
    source = {
        "objects": [
            {
                "identity": {
                    "id": "obj-1",
                    "type": "Definition",
                    "name": "Example",
                },
                "structure": {},
            }
        ]
    }

    structure = parse(source)

    assert len(structure) == 1
    assert structure.get("obj-1") is not None


def test_parse_invalid_json():
    with pytest.raises(SerializationError):
        parse("{invalid json}")


def test_parse_requires_top_level_object():
    with pytest.raises(SerializationError):
        parse([])


def test_parse_requires_objects_key():
    with pytest.raises(SerializationError):
        parse({})


def test_parse_requires_object_array():
    with pytest.raises(SerializationError):
        parse({"objects": {}})


def test_parse_duplicate_identity():
    source = {
        "objects": [
            {
                "identity": {
                    "id": "dup",
                    "type": "Definition",
                    "name": "A",
                },
                "structure": {},
            },
            {
                "identity": {
                    "id": "dup",
                    "type": "Definition",
                    "name": "B",
                },
                "structure": {},
            },
        ]
    }

    with pytest.raises(SerializationError):
        parse(source)


# =============================================================================
# Serialization
# =============================================================================


def test_serialize_returns_json():
    structure = make_structure()

    result = serialize(structure)

    assert isinstance(result, str)

    parsed = json.loads(result)

    assert "objects" in parsed


def test_serialize_preserves_relation():
    structure = make_structure()

    restored = parse(
        serialize(structure),
    )

    relations = restored.relations()

    assert len(relations) == 1

    relation = relations[0]

    assert relation.relation_type == "depends_on"

    assert relation.participants == (
        "obj-1",
        "obj-2",
    )

    assert isinstance(
        relation.participants,
        tuple,
    )


# =============================================================================
# Round-trip
# =============================================================================


def test_roundtrip_structural_equivalence():
    original = make_structure()

    restored = parse(
        serialize(original),
    )

    assert original.structurally_equivalent(restored)


def test_roundtrip_preserves_identity():
    original = make_structure()

    restored = parse(
        serialize(original),
    )

    assert (
        original.get("obj-1").identity
        ==
        restored.get("obj-1").identity
    )


def test_roundtrip_preserves_object_count():
    original = make_structure()

    restored = parse(
        serialize(original),
    )

    assert len(original) == len(restored)


# =============================================================================
# Empty structures
# =============================================================================


def test_empty_structure_roundtrip():
    structure = KnowledgeStructure([])

    restored = parse(
        serialize(structure),
    )

    assert len(restored) == 0


# =============================================================================
# Canonical behaviour
# =============================================================================


def test_serialization_is_deterministic():
    structure = make_structure()

    first = serialize(structure)
    second = serialize(structure)

    assert first == second


def test_parse_then_serialize_then_parse():
    original = make_structure()

    once = parse(
        serialize(original),
    )

    twice = parse(
        serialize(once),
    )

    assert once.structurally_equivalent(twice)

def test_serializer_handles_immutable_nested_values():
    obj = KnowledgeObject(
        identity=ObjectIdentity(
            id="obj-1",
            type="Example",
            name="Example",
        ),
        structure={
            "numbers": (1, 2, 3),
            "nested": {
                "letters": ("a", "b"),
            },
        },
    )

    structure = KnowledgeStructure([obj])

    restored = parse(
        serialize(structure)
    )

    restored_obj = restored.get("obj-1")

    assert restored_obj is not None

    assert restored_obj.structure["numbers"] == (1, 2, 3)

    assert restored_obj.structure["nested"]["letters"] == (
        "a",
        "b",
    )