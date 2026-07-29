"""
Integration tests for the canonical public API.

This module verifies that the public interface exported by the
CKS package behaves consistently and exposes the expected
implementation-independent operations.

Only the public package namespace (`import cks`) is used here.
"""

from __future__ import annotations

import cks
from cks.core import (
    CanonicalRelation,
    KnowledgeObject,
    KnowledgeStructure,
    ObjectIdentity,
)
from cks.evolution import AddObject

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
# Public API
# =============================================================================


def test_public_construct():
    structure = cks.construct(
        [
            make_object("obj"),
        ]
    )

    assert isinstance(structure, KnowledgeStructure)


def test_public_parse_and_serialize():
    original = make_structure()

    restored = cks.parse(
        cks.serialize(original),
    )

    assert original.structurally_equivalent(restored)


def test_public_validate():
    result = cks.validate(
        make_structure(),
    )

    assert result.is_valid


def test_public_diagnose():
    diagnostics = cks.diagnose(
        make_structure(),
    )

    assert len(diagnostics.errors()) == 0


def test_public_inspect():
    summary = cks.inspect(
        make_structure(),
    )

    assert summary["object_count"] == 3
    assert summary["relation_count"] == 1


def test_public_compare():
    left = make_structure()
    right = make_structure()

    comparison = cks.compare(
        left,
        right,
    )

    assert comparison["equivalent"]


def test_public_extract():
    structure = make_structure()

    obj = cks.extract(
        structure,
        "obj-1",
    )

    assert obj is not None
    assert obj.identity.id == "obj-1"


def test_public_project():
    projected = cks.project(
        make_structure(),
        [
            "obj-1",
        ],
    )

    assert len(projected) == 1


# =============================================================================
# Public exports
# =============================================================================


def test_public_symbols_exist():
    assert callable(cks.construct)
    assert callable(cks.parse)
    assert callable(cks.serialize)

    assert callable(cks.validate)
    assert callable(cks.diagnose)

    assert callable(cks.inspect)
    assert callable(cks.compare)
    assert callable(cks.extract)
    assert callable(cks.project)

    assert callable(cks.evolve)


def test_reference_engine_exported():
    engine = cks.ReferenceEngine()

    assert isinstance(
        engine,
        cks.ReferenceEngine,
    )


def test_serialization_error_exported():
    assert issubclass(
        cks.SerializationError,
        Exception,
    )


# =============================================================================
# Observational purity
# =============================================================================


def test_public_api_is_observationally_pure():
    structure = make_structure()

    before = tuple(
        obj.identity.id
        for obj in structure
    )

    cks.validate(structure)

    after = tuple(
        obj.identity.id
        for obj in structure
    )

    assert before == after


# =============================================================================
# Determinism
# =============================================================================


def test_public_api_is_deterministic():
    structure = make_structure()

    left = cks.inspect(structure)
    right = cks.inspect(structure)

    assert left == right


def test_public_evolve():
    obj = KnowledgeObject(
        ObjectIdentity("A", "Type", "A"),
        {},
    )
    structure = cks.construct([obj])

    obj2 = KnowledgeObject(
        ObjectIdentity("B", "Type", "B"),
        {},
    )
    evolved = cks.evolve(structure, operators=[AddObject(obj2)])

    assert structure is not evolved
    assert len(structure.objects) == 1
    assert len(evolved.objects) == 2
    assert evolved.get("B") is not None