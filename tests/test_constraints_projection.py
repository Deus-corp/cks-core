"""Unit tests for the EmbeddingProjectionIntegrityConstraint extension.

See src/cks/constraints/projection.py for rationale (CKS-001
"Documents as Structural Projections", extended to vector-space
projections). This constraint is deliberately NOT part of
BUILTIN_CONSTRAINTS, so a first class of tests confirms it stays
inert unless a caller opts in.
"""

import pytest

from cks.constraints.builtin import BUILTIN_CONSTRAINTS, OPTIONAL_CONSTRAINTS
from cks.constraints.projection import (
    EMBEDDING_PROJECTION_TYPE,
    REPRESENTS_RELATION,
    EmbeddingProjectionIntegrityConstraint,
)
from cks.constraints.registry import ConstraintRegistry
from cks.core import (
    CanonicalRelation,
    KnowledgeObject,
    KnowledgeStructure,
    ObjectIdentity,
)
from cks.validator import ReferenceValidator
from cks.validator import validate as default_validate


def make_object(oid: str, otype: str = "Definition", structure: dict | None = None) -> KnowledgeObject:
    return KnowledgeObject(
        identity=ObjectIdentity(id=oid, type=otype, name=oid),
        structure=structure or {},
    )


def make_relation(oid: str, participants: list[str], relation_type: str) -> CanonicalRelation:
    return CanonicalRelation(
        identity=ObjectIdentity(id=oid, type="Relation", name=oid),
        participants=participants,
        relation_type=relation_type,
    )


def projection_validator() -> ReferenceValidator:
    """A validator scoped to this test module: core constraints plus
    the opt-in projection constraint, without touching the process-wide
    global registry (so tests stay isolated and order-independent)."""
    registry = ConstraintRegistry()
    for constraint in (*BUILTIN_CONSTRAINTS, *OPTIONAL_CONSTRAINTS):
        registry.register(constraint)
    return ReferenceValidator(registry=registry)


# ---------------------------------------------------------------------------
# Opt-in behaviour
# ---------------------------------------------------------------------------


def test_not_registered_by_default():
    """The extension must not affect cks.validate() unless opted in."""
    assert EmbeddingProjectionIntegrityConstraint().identity not in [
        c.identity for c in BUILTIN_CONSTRAINTS
    ]
    assert EmbeddingProjectionIntegrityConstraint().identity in [
        c.identity for c in OPTIONAL_CONSTRAINTS
    ]


def test_default_validate_ignores_malformed_projection_objects():
    """Without opting in, a malformed EmbeddingProjection (missing
    store_ref, no provenance link) must NOT fail default validation --
    the default pipeline doesn't know this vocabulary exists."""
    bad_projection = make_object("proj-1", EMBEDDING_PROJECTION_TYPE, structure={})
    structure = KnowledgeStructure([bad_projection])

    result = default_validate(structure)

    assert result.is_valid is True


# ---------------------------------------------------------------------------
# Opted-in behaviour: valid cases
# ---------------------------------------------------------------------------


def test_valid_embedding_projection_passes():
    source = make_object("thm-1", "Theorem")
    projection = make_object(
        "proj-1",
        EMBEDDING_PROJECTION_TYPE,
        structure={"store_ref": "qdrant://thm-collection/proj-1", "model": "text-embed-v3"},
    )
    link = make_relation("rel-1", ["thm-1", "proj-1"], REPRESENTS_RELATION)
    structure = KnowledgeStructure([source, projection, link])

    result = projection_validator().validate(structure)

    assert result.is_valid is True
    assert result.diagnostics.error_count == 0


def test_structure_without_any_projection_is_unaffected():
    """Sanity check: ordinary structures with no EmbeddingProjection
    objects validate exactly as before under the opted-in registry too."""
    a = make_object("a", "Definition")
    b = make_object("b", "Theorem")
    rel = make_relation("rel-1", ["a", "b"], "depends_on")
    structure = KnowledgeStructure([a, b, rel])

    result = projection_validator().validate(structure)

    assert result.is_valid is True


# ---------------------------------------------------------------------------
# Opted-in behaviour: violations
# ---------------------------------------------------------------------------


def test_missing_represents_relation_is_rejected():
    projection = make_object(
        "proj-1", EMBEDDING_PROJECTION_TYPE, structure={"store_ref": "store://x"}
    )
    structure = KnowledgeStructure([projection])

    result = projection_validator().validate(structure)

    assert result.is_valid is False
    messages = [d.message for d in result.diagnostics]
    assert any("exactly one" in m for m in messages)


def test_dangling_source_reference_is_rejected():
    """A projection whose 'represents' relation points at a source
    object that does not exist -- the citation-hallucination case."""
    projection = make_object(
        "proj-1", EMBEDDING_PROJECTION_TYPE, structure={"store_ref": "store://x"}
    )
    link = make_relation("rel-1", ["ghost-source", "proj-1"], REPRESENTS_RELATION)
    structure = KnowledgeStructure([projection, link])

    result = projection_validator().validate(structure)

    assert result.is_valid is False
    messages = [d.message for d in result.diagnostics]
    assert any("unknown source object" in m for m in messages)
    # Independently also caught by the pre-existing structural constraint.
    assert any("references unknown object" in m for m in messages)


def test_duplicate_represents_relations_are_rejected():
    source = make_object("thm-1", "Theorem")
    projection = make_object(
        "proj-1", EMBEDDING_PROJECTION_TYPE, structure={"store_ref": "store://x"}
    )
    link_a = make_relation("rel-1", ["thm-1", "proj-1"], REPRESENTS_RELATION)
    link_b = make_relation("rel-2", ["thm-1", "proj-1"], REPRESENTS_RELATION)
    structure = KnowledgeStructure([source, projection, link_a, link_b])

    result = projection_validator().validate(structure)

    assert result.is_valid is False
    messages = [d.message for d in result.diagnostics]
    assert any("exactly one" in m and "found 2" in m for m in messages)


def test_missing_store_ref_is_rejected():
    source = make_object("thm-1", "Theorem")
    projection = make_object("proj-1", EMBEDDING_PROJECTION_TYPE, structure={})
    link = make_relation("rel-1", ["thm-1", "proj-1"], REPRESENTS_RELATION)
    structure = KnowledgeStructure([source, projection, link])

    result = projection_validator().validate(structure)

    assert result.is_valid is False
    messages = [d.message for d in result.diagnostics]
    assert any("store_ref" in m for m in messages)


@pytest.mark.parametrize("leaked_key", ["vector", "embedding"])
def test_inline_raw_vector_payload_is_rejected(leaked_key):
    """Raw vector data must never be smuggled into the canonical
    graph -- storage/optimization is explicitly out of scope for
    cks-core (CKS-001 Non-Goals)."""
    source = make_object("thm-1", "Theorem")
    projection = make_object(
        "proj-1",
        EMBEDDING_PROJECTION_TYPE,
        structure={"store_ref": "store://x", leaked_key: [0.1, 0.2, 0.3]},
    )
    link = make_relation("rel-1", ["thm-1", "proj-1"], REPRESENTS_RELATION)
    structure = KnowledgeStructure([source, projection, link])

    result = projection_validator().validate(structure)

    assert result.is_valid is False
    messages = [d.message for d in result.diagnostics]
    assert any("must not embed raw vector payloads" in m for m in messages)


def test_unrelated_relations_do_not_satisfy_represents():
    """A 'derives' relation between the same two objects must not be
    mistaken for a 'represents' link."""
    source = make_object("thm-1", "Theorem")
    projection = make_object(
        "proj-1", EMBEDDING_PROJECTION_TYPE, structure={"store_ref": "store://x"}
    )
    unrelated = make_relation("rel-1", ["thm-1", "proj-1"], "derives")
    structure = KnowledgeStructure([source, projection, unrelated])

    result = projection_validator().validate(structure)

    assert result.is_valid is False
    messages = [d.message for d in result.diagnostics]
    assert any("exactly one" in m and "found 0" in m for m in messages)