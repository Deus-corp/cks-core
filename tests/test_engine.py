"""
Unit tests for the CKS Reference Engine.

Covers the orchestration behaviour defined in CKS-006.

The engine itself contains almost no business logic—it delegates to the
canonical subsystems. These tests therefore verify correct orchestration,
observable behaviour, and API consistency.
"""

from __future__ import annotations

from cks.core import (
    CanonicalRelation,
    KnowledgeObject,
    KnowledgeStructure,
    ObjectIdentity,
)
from cks.engine import ReferenceEngine

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
# Construction
# =============================================================================


def test_construct():
    engine = ReferenceEngine()

    structure = engine.construct(
        [
            make_object("obj"),
        ]
    )

    assert isinstance(structure, KnowledgeStructure)
    assert len(structure) == 1


# =============================================================================
# Serialization
# =============================================================================


def test_parse_and_serialize_roundtrip():
    engine = ReferenceEngine()

    original = make_structure()

    restored = engine.parse(
        engine.serialize(original),
    )

    assert original.structurally_equivalent(restored)


# =============================================================================
# Validation
# =============================================================================


def test_validate():
    engine = ReferenceEngine()

    result = engine.validate(
        make_structure(),
    )

    assert result.is_valid


def test_diagnose():
    engine = ReferenceEngine()

    diagnostics = engine.diagnose(
        make_structure(),
    )

    assert len(diagnostics.errors()) == 0


# =============================================================================
# Inspection
# =============================================================================


def test_inspect():
    engine = ReferenceEngine()

    summary = engine.inspect(
        make_structure(),
    )

    assert summary["object_count"] == 3
    assert summary["relation_count"] == 1

    assert "Definition" in summary["object_types"]

    assert "depends_on" in summary["relation_types"]


# =============================================================================
# Comparison
# =============================================================================


def test_compare_equivalent():
    engine = ReferenceEngine()

    left = make_structure()
    right = make_structure()

    comparison = engine.compare(
        left,
        right,
    )

    assert comparison["equivalent"]


def test_compare_not_equivalent():
    engine = ReferenceEngine()

    left = make_structure()

    right = KnowledgeStructure(
        [
            make_object("other"),
        ]
    )

    comparison = engine.compare(
        left,
        right,
    )

    assert not comparison["equivalent"]


# =============================================================================
# Extraction
# =============================================================================


def test_extract_existing():
    engine = ReferenceEngine()

    structure = make_structure()

    obj = engine.extract(
        structure,
        "obj-1",
    )

    assert obj is not None
    assert obj.identity.id == "obj-1"


def test_extract_missing():
    engine = ReferenceEngine()

    obj = engine.extract(
        make_structure(),
        "missing",
    )

    assert obj is None


# =============================================================================
# Projection
# =============================================================================


def test_project():
    engine = ReferenceEngine()

    projected = engine.project(
        make_structure(),
        [
            "obj-1",
            "obj-2",
        ],
    )

    assert len(projected) == 2


def test_project_ignores_missing():
    engine = ReferenceEngine()

    projected = engine.project(
        make_structure(),
        [
            "obj-1",
            "missing",
        ],
    )

    assert len(projected) == 1


# =============================================================================
# Representation
# =============================================================================


def test_repr():
    engine = ReferenceEngine()

    text = repr(engine)

    assert "ReferenceEngine" in text
    assert engine.VERSION in text


# =============================================================================
# Determinism
# =============================================================================


def test_engine_is_deterministic():
    engine = ReferenceEngine()

    structure = make_structure()

    left = engine.inspect(structure)
    right = engine.inspect(structure)

    assert left == right