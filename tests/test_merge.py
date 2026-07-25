"""
Unit tests for KnowledgeStructure.merge() (three-way merge).

Previously this behaviour was only exercised indirectly through
cks-mcp's integration tests (test_merge_knowledge.py /
test_branch_merge.py). These tests cover the pure cks-core function
directly, in particular the referential-integrity guarantee (a
relation whose participant didn't survive the merge is dropped
rather than left dangling) and the resolutions/dropped_relations
parameters that guarantee depends on.
"""

import pytest
from cks.core import (
    CanonicalRelation,
    KnowledgeObject,
    KnowledgeStructure,
    MergeConflictError,
    ObjectIdentity,
)


def _obj(oid: str, otype: str = "Concept", **structure) -> KnowledgeObject:
    return KnowledgeObject(
        identity=ObjectIdentity(id=oid, type=otype, name=oid),
        structure=structure,
    )


def _rel(oid: str, participants: list[str], relation_type: str = "depends_on") -> CanonicalRelation:
    return CanonicalRelation(
        identity=ObjectIdentity(id=oid, type="Relation", name=oid),
        participants=participants,
        relation_type=relation_type,
    )


def test_merge_no_conflict_carries_over_unrelated_changes():
    base = KnowledgeStructure([_obj("a"), _obj("b")])
    branch_a = KnowledgeStructure([_obj("a", status="reviewed"), _obj("b")])
    branch_b = KnowledgeStructure([_obj("a"), _obj("b", status="draft")])

    merged = base.merge(branch_a, branch_b)

    assert merged.get("a").structure["status"] == "reviewed"
    assert merged.get("b").structure["status"] == "draft"


def test_merge_conflict_raises_without_resolution():
    base = KnowledgeStructure([_obj("a", status="draft")])
    branch_a = KnowledgeStructure([_obj("a", status="reviewed")])
    branch_b = KnowledgeStructure([_obj("a", status="rejected")])

    with pytest.raises(MergeConflictError) as excinfo:
        base.merge(branch_a, branch_b)

    assert excinfo.value.conflicts[0].object_id == "a"


def test_merge_resolution_drop_cascades_to_dependent_relation():
    base = KnowledgeStructure([_obj("A"), _obj("B", status="draft"), _rel("rel-AB", ["A", "B"])])
    branch_a = KnowledgeStructure(
        [_obj("A"), _obj("B", status="reviewed"), _rel("rel-AB", ["A", "B"])]
    )
    branch_b = KnowledgeStructure([_obj("A"), _rel("rel-AB", ["A", "B"])])  # B deleted

    dropped: list[str] = []
    merged = base.merge(branch_a, branch_b, resolutions={"B": None}, dropped_relations=dropped)

    assert merged.get("B") is None
    assert merged.get("rel-AB") is None
    assert dropped == ["rel-AB"]


def test_merge_resolution_keep_preserves_dependent_relation():
    base = KnowledgeStructure([_obj("A"), _obj("B", status="draft"), _rel("rel-AB", ["A", "B"])])
    branch_a = KnowledgeStructure(
        [_obj("A"), _obj("B", status="reviewed"), _rel("rel-AB", ["A", "B"])]
    )
    branch_b = KnowledgeStructure([_obj("A"), _rel("rel-AB", ["A", "B"])])  # B deleted

    dropped: list[str] = []
    merged = base.merge(branch_a, branch_b, resolutions={"B": "branch_a"}, dropped_relations=dropped)

    assert merged.get("B").structure["status"] == "reviewed"
    assert merged.get("rel-AB") is not None
    assert dropped == []


def test_merge_dropped_relations_defaults_to_none_and_is_optional():
    """dropped_relations is purely additive -- omitting it must not change behaviour."""
    base = KnowledgeStructure([_obj("A"), _obj("B"), _rel("rel-AB", ["A", "B"])])
    branch_a = KnowledgeStructure([_obj("A"), _obj("B", status="x"), _rel("rel-AB", ["A", "B"])])
    branch_b = KnowledgeStructure([_obj("A"), _rel("rel-AB", ["A", "B"])])

    merged = base.merge(branch_a, branch_b, resolutions={"B": None})
    assert merged.get("rel-AB") is None