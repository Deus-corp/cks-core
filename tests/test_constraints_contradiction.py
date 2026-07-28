"""
Tests for the optional contradiction-detection constraints (mutual
exclusion between relation_types, and functional/single-valued
relation_types).
"""

from cks.constraints.contradiction import (
    FUNCTIONAL_RELATION_RULE_TYPE,
    MUTUAL_EXCLUSION_RULE_TYPE,
    FunctionalRelationConstraint,
    MutualExclusionConstraint,
)
from cks.core import (
    CanonicalRelation,
    KnowledgeObject,
    KnowledgeStructure,
    ObjectIdentity,
)


def make_object(oid: str, otype: str, name: str = "", structure: dict | None = None) -> KnowledgeObject:
    return KnowledgeObject(
        identity=ObjectIdentity(id=oid, type=otype, name=name or oid),
        structure=structure or {},
    )


def make_relation(oid: str, participants: list[str], relation_type: str) -> CanonicalRelation:
    return CanonicalRelation(
        identity=ObjectIdentity(id=oid, type="Relation", name=oid),
        participants=participants,
        relation_type=relation_type,
    )


def make_mutual_exclusion_rule(oid: str, relation_type_a: str, relation_type_b: str) -> KnowledgeObject:
    return make_object(
        oid,
        MUTUAL_EXCLUSION_RULE_TYPE,
        structure={"relation_type_a": relation_type_a, "relation_type_b": relation_type_b},
    )


def make_functional_relation_rule(oid: str, relation_type: str) -> KnowledgeObject:
    return make_object(
        oid, FUNCTIONAL_RELATION_RULE_TYPE, structure={"relation_type": relation_type}
    )


# ---------------------------------------------------------------------------
# MutualExclusionConstraint
# ---------------------------------------------------------------------------


def test_mutual_exclusion_passes_without_any_rule():
    structure = KnowledgeStructure([
        make_object("a", "Thing"),
        make_object("b", "Thing"),
        make_relation("r1", ["a", "b"], "supports"),
        make_relation("r2", ["a", "b"], "contradicts"),
    ])
    assert MutualExclusionConstraint().evaluate(structure) == []


def test_mutual_exclusion_flags_conflicting_relations():
    structure = KnowledgeStructure([
        make_mutual_exclusion_rule("rule-1", "supports", "contradicts"),
        make_object("a", "Claim"),
        make_object("b", "Claim"),
        make_relation("r1", ["a", "b"], "supports"),
        make_relation("r2", ["a", "b"], "contradicts"),
    ])
    diagnostics = MutualExclusionConstraint().evaluate(structure)
    assert len(diagnostics) == 1
    assert diagnostics[0].identity == "CKS-EXT-MUTUAL-EXCLUSION"
    assert diagnostics[0].location in ("r1", "r2")
    assert "r1" in diagnostics[0].message and "r2" in diagnostics[0].message


def test_mutual_exclusion_ignores_reversed_pair():
    """supports(a,b) and contradicts(b,a) are NOT the same ordered pair
    -- only an exact (source, target) match on both sides counts."""
    structure = KnowledgeStructure([
        make_mutual_exclusion_rule("rule-1", "supports", "contradicts"),
        make_object("a", "Claim"),
        make_object("b", "Claim"),
        make_relation("r1", ["a", "b"], "supports"),
        make_relation("r2", ["b", "a"], "contradicts"),
    ])
    assert MutualExclusionConstraint().evaluate(structure) == []


def test_mutual_exclusion_rule_order_is_symmetric():
    """Declaring the rule as (b, a) instead of (a, b) must catch the
    same violation -- the two relation_types are just an unordered
    pair from the rule's point of view."""
    structure = KnowledgeStructure([
        make_mutual_exclusion_rule("rule-1", "contradicts", "supports"),
        make_object("a", "Claim"),
        make_object("b", "Claim"),
        make_relation("r1", ["a", "b"], "supports"),
        make_relation("r2", ["a", "b"], "contradicts"),
    ])
    diagnostics = MutualExclusionConstraint().evaluate(structure)
    assert len(diagnostics) == 1


def test_mutual_exclusion_ignores_self_referential_rule():
    structure = KnowledgeStructure([
        make_mutual_exclusion_rule("rule-1", "supports", "supports"),
        make_object("a", "Claim"),
        make_object("b", "Claim"),
        make_relation("r1", ["a", "b"], "supports"),
    ])
    assert MutualExclusionConstraint().evaluate(structure) == []


def test_mutual_exclusion_ignores_non_binary_relations():
    structure = KnowledgeStructure([
        make_mutual_exclusion_rule("rule-1", "supports", "contradicts"),
        make_object("a", "Claim"),
        make_object("b", "Claim"),
        make_object("c", "Claim"),
        make_relation("r1", ["a", "b", "c"], "supports"),
    ])
    assert MutualExclusionConstraint().evaluate(structure) == []


def test_mutual_exclusion_multiple_rules_accumulate():
    structure = KnowledgeStructure([
        make_mutual_exclusion_rule("rule-1", "supports", "contradicts"),
        make_mutual_exclusion_rule("rule-2", "orbits", "does_not_orbit"),
        make_object("a", "Claim"),
        make_object("b", "Claim"),
        make_relation("r1", ["a", "b"], "supports"),
        make_relation("r2", ["a", "b"], "contradicts"),
        make_relation("r3", ["a", "b"], "orbits"),
        make_relation("r4", ["a", "b"], "does_not_orbit"),
    ])
    diagnostics = MutualExclusionConstraint().evaluate(structure)
    assert len(diagnostics) == 2


# ---------------------------------------------------------------------------
# FunctionalRelationConstraint
# ---------------------------------------------------------------------------


def test_functional_relation_passes_without_any_rule():
    structure = KnowledgeStructure([
        make_object("earth", "Planet"),
        make_object("sun", "Star"),
        make_object("mars_placeholder", "Star"),
        make_relation("r1", ["earth", "sun"], "orbits"),
        make_relation("r2", ["earth", "mars_placeholder"], "orbits"),
    ])
    assert FunctionalRelationConstraint().evaluate(structure) == []


def test_functional_relation_passes_single_target():
    structure = KnowledgeStructure([
        make_functional_relation_rule("rule-1", "orbits"),
        make_object("earth", "Planet"),
        make_object("sun", "Star"),
        make_relation("r1", ["earth", "sun"], "orbits"),
    ])
    assert FunctionalRelationConstraint().evaluate(structure) == []


def test_functional_relation_flags_multiple_targets():
    structure = KnowledgeStructure([
        make_functional_relation_rule("rule-1", "orbits"),
        make_object("earth", "Planet"),
        make_object("sun", "Star"),
        make_object("mars", "Planet"),
        make_relation("r1", ["earth", "sun"], "orbits"),
        make_relation("r2", ["earth", "mars"], "orbits"),
    ])
    diagnostics = FunctionalRelationConstraint().evaluate(structure)
    assert len(diagnostics) == 1
    assert diagnostics[0].identity == "CKS-EXT-FUNCTIONAL-RELATION"
    assert "earth" in diagnostics[0].message
    assert "2" in diagnostics[0].message


def test_functional_relation_ignores_unrelated_relation_types():
    structure = KnowledgeStructure([
        make_functional_relation_rule("rule-1", "orbits"),
        make_object("earth", "Planet"),
        make_object("mars", "Planet"),
        make_object("moon1", "Moon"),
        make_object("moon2", "Moon"),
        make_relation("r1", ["earth", "moon1"], "has_moon"),
        make_relation("r2", ["earth", "moon2"], "has_moon"),
    ])
    assert FunctionalRelationConstraint().evaluate(structure) == []


def test_functional_relation_ignores_non_binary_relations():
    structure = KnowledgeStructure([
        make_functional_relation_rule("rule-1", "orbits"),
        make_object("earth", "Planet"),
        make_object("sun", "Star"),
        make_object("moon", "Moon"),
        make_relation("r1", ["earth", "sun", "moon"], "orbits"),
    ])
    assert FunctionalRelationConstraint().evaluate(structure) == []


def test_functional_relation_multiple_rules_accumulate():
    structure = KnowledgeStructure([
        make_functional_relation_rule("rule-1", "orbits"),
        make_functional_relation_rule("rule-2", "capital_of"),
        make_object("earth", "Planet"),
        make_object("sun", "Star"),
        make_object("mars", "Planet"),
        make_object("france", "Country"),
        make_object("paris", "City"),
        make_object("lyon", "City"),
        make_relation("r1", ["earth", "sun"], "orbits"),
        make_relation("r2", ["earth", "mars"], "orbits"),
        make_relation("r3", ["france", "paris"], "capital_of"),
        make_relation("r4", ["france", "lyon"], "capital_of"),
    ])
    diagnostics = FunctionalRelationConstraint().evaluate(structure)
    assert len(diagnostics) == 2


def test_functional_relation_distinguishes_source_from_target():
    """Two different sources sharing one target is not a violation --
    only multiple *targets* for the same source counts."""
    structure = KnowledgeStructure([
        make_functional_relation_rule("rule-1", "orbits"),
        make_object("earth", "Planet"),
        make_object("mars", "Planet"),
        make_object("sun", "Star"),
        make_relation("r1", ["earth", "sun"], "orbits"),
        make_relation("r2", ["mars", "sun"], "orbits"),
    ])
    assert FunctionalRelationConstraint().evaluate(structure) == []


# ---------------------------------------------------------------------------
# Opt-in behaviour via the full validator
# ---------------------------------------------------------------------------


def test_constraints_are_inert_without_opt_in():
    from cks.validator import validate

    structure = KnowledgeStructure([
        make_mutual_exclusion_rule("rule-1", "supports", "contradicts"),
        make_functional_relation_rule("rule-2", "orbits"),
        make_object("earth", "Planet"),
        make_object("sun", "Star"),
        make_object("mars", "Planet"),
        make_relation("r1", ["earth", "sun"], "orbits"),
        make_relation("r2", ["earth", "mars"], "orbits"),
    ])
    result = validate(structure)
    assert result.is_valid


def test_constraints_fire_when_opted_in():
    from cks.constraints.builtin import OPTIONAL_CONSTRAINTS_BY_NAME
    from cks.validator import validate

    structure = KnowledgeStructure([
        make_functional_relation_rule("rule-1", "orbits"),
        make_object("earth", "Planet"),
        make_object("sun", "Star"),
        make_object("mars", "Planet"),
        make_relation("r1", ["earth", "sun"], "orbits"),
        make_relation("r2", ["earth", "mars"], "orbits"),
    ])
    constraint = OPTIONAL_CONSTRAINTS_BY_NAME["functional_relation"]
    result = validate(structure, extra_constraints=[constraint])
    assert not result.is_valid
    assert any(d.identity == "CKS-EXT-FUNCTIONAL-RELATION" for d in result.diagnostics)


def test_both_contradiction_constraints_registered_as_optional():
    from cks.constraints.builtin import BUILTIN_CONSTRAINTS, OPTIONAL_CONSTRAINTS

    builtin_identities = [c.identity for c in BUILTIN_CONSTRAINTS]
    optional_identities = [c.identity for c in OPTIONAL_CONSTRAINTS]

    assert "CKS-EXT-MUTUAL-EXCLUSION" not in builtin_identities
    assert "CKS-EXT-FUNCTIONAL-RELATION" not in builtin_identities
    assert "CKS-EXT-MUTUAL-EXCLUSION" in optional_identities
    assert "CKS-EXT-FUNCTIONAL-RELATION" in optional_identities