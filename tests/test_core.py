"""
Unit tests for the canonical core model.

Covers the immutable semantic objects defined by CKS-001.

This module tests only the core object model. Validation,
serialization and engine behaviour are tested separately.
"""

from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from cks.core import (
    CanonicalRelation,
    KnowledgeObject,
    KnowledgeStructure,
    ObjectIdentity,
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
# ObjectIdentity
# =============================================================================


def test_object_identity_is_immutable():
    identity = ObjectIdentity(
        id="obj",
        type="Definition",
        name="Example",
    )

    with pytest.raises(FrozenInstanceError):
        identity.id = "other"


# =============================================================================
# KnowledgeObject
# =============================================================================


def test_knowledge_object_is_immutable():
    obj = make_object("obj")

    with pytest.raises(FrozenInstanceError):
        obj.identity = ObjectIdentity(
            id="new",
            type="Definition",
            name="New",
        )


# =============================================================================
# CanonicalRelation
# =============================================================================


def test_relation_properties():
    relation = make_relation(
        "rel",
        ["a", "b"],
        "depends_on",
    )

    assert relation.participants == ("a", "b")
    assert isinstance(relation.participants, tuple)
    assert relation.relation_type == "depends_on"


def test_relation_rejects_bare_string_participants():
    """
    Regression test: participants is Iterable[str], and a bare str is
    technically iterable-of-characters -- so tuple(participants) used
    to silently accept "earth" and split it into
    ('e', 'a', 'r', 't', 'h') instead of raising. This is almost never
    what a caller who forgot to wrap a single id in a list intended,
    and it produced a relation with five bogus one-character
    "participants" with no error anywhere. cks.evolution.parse_operations
    (the path evolve_knowledge routes through) had no independent check
    of its own and relied entirely on this constructor.
    """
    with pytest.raises(ValueError, match="not a bare str"):
        make_relation("rel", "earth", "orbits")  # type: ignore[arg-type]


def test_relation_rejects_bare_bytes_participants():
    with pytest.raises(ValueError, match="not a bare bytes"):
        make_relation("rel", b"earth", "orbits")  # type: ignore[arg-type]


def test_relation_rejects_fewer_than_two_participants():
    with pytest.raises(ValueError, match="at least two participants"):
        make_relation("rel", ["only-one"], "orbits")


def test_relation_rejects_non_string_participant():
    with pytest.raises(ValueError, match="must all be strings"):
        make_relation("rel", ["earth", 42], "orbits")  # type: ignore[list-item]


def test_relation_accepts_non_list_iterable_of_strings():
    """A generator (not a list) of at least two strings is still
    accepted -- the fix targets bare str/bytes specifically, not every
    non-list iterable."""
    relation = CanonicalRelation(
        identity=ObjectIdentity(id="rel", type="Relation", name="rel"),
        participants=(p for p in ["earth", "sun"]),
        relation_type="orbits",
    )
    assert relation.participants == ("earth", "sun")


# =============================================================================
# KnowledgeStructure
# =============================================================================


def test_structure_length():
    structure = make_structure()

    assert len(structure) == 3


def test_structure_iteration():
    structure = make_structure()

    identities = [
        obj.identity.id
        for obj in structure
    ]

    assert identities == [
        "obj-1",
        "obj-2",
        "rel-1",
    ]


def test_structure_contains():
    structure = make_structure()

    assert "obj-1" in structure
    assert "obj-2" in structure
    assert "rel-1" in structure

    assert "missing" not in structure


def test_structure_get():
    structure = make_structure()

    obj = structure.get("obj-1")

    assert obj is not None
    assert obj.identity.id == "obj-1"

    assert structure.get("missing") is None


def test_structure_relations():
    structure = make_structure()

    relations = structure.relations()

    assert len(relations) == 1
    assert relations[0].identity.id == "rel-1"


def test_duplicate_identity_raises():
    with pytest.raises(ValueError):
        KnowledgeStructure(
            [
                make_object("dup"),
                make_object("dup"),
            ]
        )


# =============================================================================
# Structural equivalence
# =============================================================================


def test_structurally_equivalent():
    left = make_structure()
    right = make_structure()

    assert left.structurally_equivalent(right)


def test_not_structurally_equivalent():
    left = make_structure()

    right = KnowledgeStructure(
        [
            make_object("obj-1"),
            make_object("obj-3"),
        ]
    )

    assert not left.structurally_equivalent(right)


# =============================================================================
# Identity equivalence
# =============================================================================
#
# identity_equivalent() had no direct test coverage anywhere in the
# suite before this. That gap is exactly how a change to
# KnowledgeStructure._identity_hash's internal construction (caching
# each KnowledgeObject's id hash instead of recomputing it from
# scratch on every KnowledgeStructure.__init__ call) could have
# silently changed its observable behaviour without any test noticing.


def test_identity_equivalent_same_ids_different_content():
    """Same ids, different (non-id) content -> identity-equivalent but not structurally equivalent."""
    left = KnowledgeStructure(
        [make_object("obj-1", name="Alpha")],
    )
    right = KnowledgeStructure(
        [make_object("obj-1", name="Beta")],
    )

    assert left.identity_equivalent(right)
    assert not left.structurally_equivalent(right)


def test_identity_equivalent_different_ids():
    left = KnowledgeStructure([make_object("obj-1")])
    right = KnowledgeStructure([make_object("obj-2")])

    assert not left.identity_equivalent(right)


def test_identity_equivalent_is_order_independent():
    """Same id set, inserted in a different order -> still identity-equivalent."""
    left = KnowledgeStructure(
        [make_object("obj-1"), make_object("obj-2"), make_object("obj-3")],
    )
    right = KnowledgeStructure(
        [make_object("obj-3"), make_object("obj-1"), make_object("obj-2")],
    )

    assert left.identity_equivalent(right)


def test_identity_equivalent_reflexive_for_relations():
    """Relations (which bypass KnowledgeObject.__post_init__ via their own __init__) must also be covered."""
    left = make_structure()
    right = make_structure()

    assert left.identity_equivalent(right)


# =============================================================================
# Representation
# =============================================================================


def test_repr():
    structure = make_structure()

    text = repr(structure)

    assert "KnowledgeStructure" in text
    assert "objects=3" in text
    assert "relations=1" in text


def test_knowledge_object_structure_is_immutable():
    obj = KnowledgeObject(
        identity=ObjectIdentity(
            "obj",
            "Concept",
            "Object",
        ),
        structure={"a": 1},
    )

    with pytest.raises(TypeError):
        obj.structure["b"] = 2

def test_relation_structure_is_immutable():
    relation = CanonicalRelation(
        identity=ObjectIdentity(
            "r",
            "CanonicalRelation",
            "R",
        ),
        participants=["a", "b"],
        relation_type="depends_on",
    )

    with pytest.raises(TypeError):
        relation.structure["x"] = 1

def test_nested_structure_is_deeply_immutable():
    obj = KnowledgeObject(
        identity=ObjectIdentity(
            "obj",
            "Thing",
            "Thing",
        ),
        structure={
            "nested": {
                "value": 1,
            },
        },
    )

    with pytest.raises(TypeError):
        obj.structure["nested"]["x"] = 2

def test_nested_lists_are_converted_to_tuples():
    obj = KnowledgeObject(
        identity=ObjectIdentity(
            "obj",
            "Thing",
            "Thing",
        ),
        structure={
            "nested": {
                "items": [1, 2, 3],
            },
        },
    )

    assert obj.structure["nested"]["items"] == (1, 2, 3)

def test_sets_are_converted_to_frozensets():
    obj = KnowledgeObject(
        identity=ObjectIdentity(
            "obj",
            "Thing",
            "Thing",
        ),
        structure={
            "tags": {"a", "b"},
        },
    )

    assert isinstance(
        obj.structure["tags"],
        frozenset,
    )


# ============================================================================
# Copy / Deepcopy Semantics (regression for MappingProxyType)
# ============================================================================

def test_knowledge_object_deepcopy_does_not_raise():
    from copy import deepcopy
    obj = KnowledgeObject(
        identity=ObjectIdentity("obj", "Thing", "Thing"),
        structure={"nested": {"a": [1, 2, {"b": 3}]}},
    )
    copied = deepcopy(obj)
    assert copied is obj


def test_knowledge_object_copy_returns_self():
    from copy import copy
    obj = KnowledgeObject(
        identity=ObjectIdentity("obj", "Thing", "Thing"),
        structure={"a": 1},
    )
    assert copy(obj) is obj


def test_knowledge_structure_deepcopy_does_not_raise():
    from copy import deepcopy
    obj = KnowledgeObject(
        identity=ObjectIdentity("obj-1", "Thing", "Thing"),
        structure={"content": "hello"},
    )
    structure = KnowledgeStructure([obj])
    copied = deepcopy(structure)
    assert copied is structure
    assert copied == structure


def test_knowledge_object_deepcopy_inside_container_does_not_raise():
    from copy import deepcopy
    obj = KnowledgeObject(
        identity=ObjectIdentity("obj", "Thing", "Thing"),
        structure={"content": "hello"},
    )
    container = {"session_like": {"knowledge_structure": obj}}
    copied = deepcopy(container)
    assert copied["session_like"]["knowledge_structure"] is obj


# ============================================================================
# Merkle Hashing & Structural Diff (v1.7.0)
# ============================================================================

def test_knowledge_object_has_stable_hash():
    """KnowledgeObject._hash must be a 32-byte value computed once."""
    obj = KnowledgeObject(
        identity=ObjectIdentity("obj", "Thing", "Thing"),
        structure={"a": 1},
    )
    assert isinstance(obj._hash, bytes)
    assert len(obj._hash) == 32

def test_knowledge_object_hash_deterministic():
    """Same identity + structure must yield the same hash."""
    obj1 = KnowledgeObject(
        identity=ObjectIdentity("obj", "Thing", "Thing"),
        structure={"a": 1, "b": 2},
    )
    obj2 = KnowledgeObject(
        identity=ObjectIdentity("obj", "Thing", "Thing"),
        structure={"b": 2, "a": 1},  # другой порядок ключей
    )
    assert obj1._hash == obj2._hash

def test_knowledge_object_hash_differs_for_different_structure():
    obj1 = KnowledgeObject(
        identity=ObjectIdentity("obj", "Thing", "Thing"),
        structure={"a": 1},
    )
    obj2 = KnowledgeObject(
        identity=ObjectIdentity("obj", "Thing", "Thing"),
        structure={"a": 2},
    )
    assert obj1._hash != obj2._hash

def test_knowledge_object_has_stable_id_hash():
    """
    KnowledgeObject._id_hash caches the canonical hash of just
    identity.id, computed once in __post_init__, so
    KnowledgeStructure.__init__ can build _identity_hash without
    recomputing a SHA-256 leaf hash per id on every construction.
    """
    obj = KnowledgeObject(
        identity=ObjectIdentity("obj", "Thing", "Thing"),
        structure={"a": 1},
    )
    assert isinstance(obj._id_hash, bytes)
    assert len(obj._id_hash) == 32

def test_knowledge_object_id_hash_depends_only_on_id():
    """_id_hash must be the same for two objects sharing an id, even
    when their type/name/structure differ -- and different for
    different ids, even with everything else identical."""
    same_id_a = KnowledgeObject(identity=ObjectIdentity("obj", "TypeA", "Alpha"), structure={"x": 1})
    same_id_b = KnowledgeObject(identity=ObjectIdentity("obj", "TypeB", "Beta"), structure={"y": 2})
    assert same_id_a._id_hash == same_id_b._id_hash

    different_id = KnowledgeObject(identity=ObjectIdentity("other", "TypeA", "Alpha"), structure={"x": 1})
    assert same_id_a._id_hash != different_id._id_hash

def test_canonical_relation_has_id_hash():
    """CanonicalRelation.__init__ bypasses KnowledgeObject.__post_init__
    entirely (it sets fields via object.__setattr__ directly), so it
    must set _id_hash itself -- otherwise every KnowledgeStructure
    containing a relation would raise AttributeError on construction."""
    relation = make_relation("rel-1", ["obj-1", "obj-2"])
    assert isinstance(relation._id_hash, bytes)
    assert len(relation._id_hash) == 32

def test_knowledge_structure_root_hash_deterministic():
    """Merkle root must be independent of insertion order."""
    a = KnowledgeObject(ObjectIdentity("a", "T", "A"), structure={})
    b = KnowledgeObject(ObjectIdentity("b", "T", "B"), structure={})
    s1 = KnowledgeStructure([a, b])
    s2 = KnowledgeStructure([b, a])
    assert s1.root_hash == s2.root_hash
    assert s1.structurally_equivalent(s2)

def test_knowledge_structure_root_hash_different_content():
    a = KnowledgeObject(ObjectIdentity("a", "T", "A"), structure={})
    b = KnowledgeObject(ObjectIdentity("b", "T", "B"), structure={})
    s1 = KnowledgeStructure([a, b])
    s2 = KnowledgeStructure([a])
    assert s1.root_hash != s2.root_hash
    assert not s1.structurally_equivalent(s2)

def test_knowledge_structure_is_hashable():
    """KnowledgeStructure now implements __hash__ based on root hash."""
    a = KnowledgeObject(ObjectIdentity("a", "T", "A"), structure={})
    b = KnowledgeObject(ObjectIdentity("b", "T", "B"), structure={})
    s1 = KnowledgeStructure([a, b])
    s2 = KnowledgeStructure([b, a])
    s3 = KnowledgeStructure([a])
    assert hash(s1) == hash(s2)
    assert hash(s1) != hash(s3)
    # Must be usable as dictionary key
    d = {s1: "test"}
    assert d[s2] == "test"

def test_diff_identity():
    """diff of identical structures must return empty list."""
    left = make_structure()
    right = make_structure()
    ops = left.diff(right)
    assert ops == []

def test_diff_add_object():
    """Adding an object must produce exactly one AddObject operator."""
    left = make_structure()
    new_obj = make_object("obj-3")
    right = KnowledgeStructure(list(left.objects) + [new_obj])
    ops = left.diff(right)
    assert len(ops) == 1
    from cks.evolution import AddObject
    assert isinstance(ops[0], AddObject)

def test_diff_remove_object():
    """Removing an object must produce RemoveObject (and cascade relations)."""
    left = make_structure()
    # Remove obj-1, which will cascade-delete rel-1 (participants: obj-1, obj-2)
    right = KnowledgeStructure([obj for obj in left.objects if obj.identity.id != "obj-1"])
    ops = left.diff(right)
    from cks.evolution import RemoveObject
    assert any(isinstance(op, RemoveObject) for op in ops)

def test_diff_modified_object_preserves_relations():
    """Modifying an object must cascade-remove and re-add its dependent relations."""
    left = make_structure()
    # Modify obj-1: change structure
    modified_obj = KnowledgeObject(
        identity=ObjectIdentity("obj-1", "Definition", "obj-1"),
        structure={"key": "new_value"},
    )
    right_objects = [modified_obj] + [obj for obj in left.objects if obj.identity.id != "obj-1"]
    right = KnowledgeStructure(right_objects)

    ops = left.diff(right)
    from cks.evolution import compose
    result = compose(left, ops)

    assert result.structurally_equivalent(right)
    # rel-1 must survive the modification
    assert "rel-1" in result


# =============================================================================
# query_subgraph
# =============================================================================
#
# Chain graph used by most tests below:
#
#     A --r1-- B --r2-- C --r3-- D        (E isolated, no relations)
#
# Plus a separate 3-way hyperedge graph (F, G, H via r_hyper) for tests
# that specifically need a non-binary relation, and a star graph (hub
# plus N leaves) for the budget/ranking tests, where degree centrality
# and distance alone can't distinguish leaves from each other.


def _make_chain_structure() -> KnowledgeStructure:
    return KnowledgeStructure(
        [
            make_object("A"),
            make_object("B"),
            make_object("C"),
            make_object("D"),
            make_object("E"),
            make_relation("r1", ["A", "B"]),
            make_relation("r2", ["B", "C"]),
            make_relation("r3", ["C", "D"]),
        ]
    )


def _make_hyperedge_structure() -> KnowledgeStructure:
    return KnowledgeStructure(
        [
            make_object("F"),
            make_object("G"),
            make_object("H"),
            make_relation("r_hyper", ["F", "G", "H"], relation_type="triad"),
        ]
    )


def _make_star_structure(leaf_count: int = 10) -> KnowledgeStructure:
    objects = [make_object("hub", otype="Hub")]
    objects += [make_object(f"leaf{i}") for i in range(leaf_count)]
    objects.append(make_object("vip", otype="Architecture"))
    relations = [
        make_relation(f"r{i}", ["hub", f"leaf{i}"]) for i in range(leaf_count)
    ]
    relations.append(make_relation("r_vip", ["hub", "vip"]))
    return KnowledgeStructure(objects + relations)


def test_query_subgraph_unknown_seed_returns_empty():
    structure = _make_chain_structure()
    result = structure.query_subgraph("does-not-exist", depth=2)
    assert len(result.structure) == 0
    assert result.total_found_nodes == 0
    assert result.returned_nodes == 0
    assert result.is_truncated is False
    assert result.truncation_reason is None
    assert result.suggested_next_seed is None


def test_query_subgraph_depth_zero_returns_only_seed():
    structure = _make_chain_structure()
    result = structure.query_subgraph("A", depth=0)
    ids = {obj.identity.id for obj in result.structure.objects}
    assert ids == {"A"}


def test_query_subgraph_depth_one_stops_at_one_hop():
    structure = _make_chain_structure()
    result = structure.query_subgraph("A", depth=1)
    ids = {obj.identity.id for obj in result.structure.objects}
    assert ids == {"A", "B", "r1"}


def test_query_subgraph_depth_two_reaches_further():
    structure = _make_chain_structure()
    result = structure.query_subgraph("A", depth=2)
    ids = {obj.identity.id for obj in result.structure.objects}
    assert ids == {"A", "B", "C", "r1", "r2"}
    assert result.total_found_nodes == 3  # A, B, C
    assert result.returned_nodes == 3
    assert result.is_truncated is False


def test_query_subgraph_isolated_node_returns_only_itself():
    structure = _make_chain_structure()
    result = structure.query_subgraph("E", depth=5)
    ids = {obj.identity.id for obj in result.structure.objects}
    assert ids == {"E"}


def test_query_subgraph_multiple_seeds():
    structure = _make_chain_structure()
    result = structure.query_subgraph({"A", "D"}, depth=1)
    ids = {obj.identity.id for obj in result.structure.objects}
    # A reaches B and D reaches C in one hop each, so the visited set
    # is {A, B, C, D}. r2 (B--C) is then included too even though it
    # was never itself traversed: both its endpoints survived, and
    # query_subgraph applies the standard vertex-induced-subgraph rule
    # (every relation whose participants all survived is kept) rather
    # than only relations actually crossed by BFS.
    assert ids == {"A", "B", "C", "D", "r1", "r2", "r3"}


def test_query_subgraph_traverses_hyperedge():
    """A relation with 3+ participants must expose every OTHER
    participant as a one-hop neighbor of any one of them."""
    structure = _make_hyperedge_structure()
    result = structure.query_subgraph("F", depth=1)
    ids = {obj.identity.id for obj in result.structure.objects}
    assert ids == {"F", "G", "H", "r_hyper"}


def test_query_subgraph_result_has_no_dangling_relations():
    structure = _make_chain_structure()
    result = structure.query_subgraph("A", depth=1)
    returned_ids = {obj.identity.id for obj in result.structure.objects}
    for relation in result.structure.relations():
        assert set(relation.participants) <= returned_ids


def test_query_subgraph_root_hash_is_stable_and_order_independent():
    structure = _make_chain_structure()
    first = structure.query_subgraph("A", depth=2)
    second = structure.query_subgraph({"A"}, depth=2)
    assert first.structure.root_hash == second.structure.root_hash


def test_query_subgraph_include_relation_types_filters_traversal_and_output():
    structure = KnowledgeStructure(
        [
            make_object("A"),
            make_object("B"),
            make_object("C"),
            make_relation("r1", ["A", "B"], relation_type="depends_on"),
            make_relation("r2", ["A", "C"], relation_type="mentions"),
        ]
    )
    result = structure.query_subgraph("A", depth=1, include_relation_types={"depends_on"})
    ids = {obj.identity.id for obj in result.structure.objects}
    # "mentions" neither connects C nor appears in the output.
    assert ids == {"A", "B", "r1"}


def test_query_subgraph_include_object_types_filters_discovered_not_seeds():
    structure = KnowledgeStructure(
        [
            make_object("A", otype="Seed"),
            make_object("B", otype="Excluded"),
            make_relation("r1", ["A", "B"]),
        ]
    )
    result = structure.query_subgraph(
        "A", depth=1, include_object_types={"Seed"}
    )
    ids = {obj.identity.id for obj in result.structure.objects}
    # B's type is excluded from *discovery*, and its relation to A
    # then has a missing participant, so both are dropped -- but the
    # seed itself is exempt from the object-type filter.
    assert ids == {"A"}


def test_query_subgraph_not_truncated_when_budget_is_generous():
    structure = _make_chain_structure()
    result = structure.query_subgraph("A", depth=2, max_objects=50)
    assert result.is_truncated is False
    assert result.truncation_reason is None
    assert result.suggested_next_seed is None


def test_query_subgraph_max_objects_truncates_and_reports_metadata():
    structure = _make_star_structure(leaf_count=10)
    result = structure.query_subgraph("hub", depth=1, max_objects=4)
    ids = {
        obj.identity.id
        for obj in result.structure.objects
        if not isinstance(obj, CanonicalRelation)
    }
    assert "hub" in ids  # seed always kept
    assert len(ids) == 4
    assert result.total_found_nodes == 12  # hub (seed) + 10 leaves + vip
    assert result.returned_nodes == 4
    assert result.is_truncated is True
    assert result.truncation_reason == "max_objects_exceeded"
    assert result.suggested_next_seed is not None
    assert result.suggested_next_seed not in ids


def test_query_subgraph_max_tokens_truncates():
    from cks.core import _estimate_subgraph_tokens

    structure = _make_star_structure(leaf_count=10)
    # Every leaf costs the same estimated tokens; a tight budget must
    # still keep the seed and stop taking further leaves once spent.
    budget = (
        _estimate_subgraph_tokens(structure.get("hub"))
        + _estimate_subgraph_tokens(structure.get("leaf0"))
    )
    result = structure.query_subgraph("hub", depth=1, max_tokens=budget)
    ids = {
        obj.identity.id
        for obj in result.structure.objects
        if not isinstance(obj, CanonicalRelation)
    }
    assert "hub" in ids
    assert result.is_truncated is True
    assert result.truncation_reason == "max_tokens_exceeded"


def test_query_subgraph_type_weights_prioritizes_candidates():
    structure = _make_star_structure(leaf_count=10)
    result = structure.query_subgraph(
        "hub",
        depth=1,
        max_objects=4,
        type_weights={"Architecture": 5.0},
    )
    ids = {obj.identity.id for obj in result.structure.objects}
    # "vip" has the same degree as every leaf but a much higher type
    # weight, so it must win a slot over at least one leaf.
    assert "vip" in ids


def test_query_subgraph_seeds_are_never_dropped_by_budget():
    structure = _make_chain_structure()
    result = structure.query_subgraph({"A", "D"}, depth=0, max_objects=1)
    ids = {obj.identity.id for obj in result.structure.objects}
    assert ids == {"A", "D"}


def test_query_subgraph_top_level_function_matches_method():
    import cks

    structure = _make_chain_structure()
    via_function = cks.query_subgraph(structure, "A", depth=2)
    via_method = structure.query_subgraph("A", depth=2)
    assert via_function.structure.root_hash == via_method.structure.root_hash
    assert via_function.total_found_nodes == via_method.total_found_nodes