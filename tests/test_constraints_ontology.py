"""
Tests for the optional ontology constraints (type hierarchy and
relation type checking).
"""

import pytest
from cks.core import KnowledgeObject, KnowledgeStructure, ObjectIdentity
from cks.constraints.ontology import (
    TypeHierarchy,
    TypeHierarchyCycleConstraint,
    RelationTypeConstraint,
    TYPE_DEFINITION_TYPE,
    TYPE_RULE_TYPE,
)
from cks.constraints.base import Constraint


def make_object(oid: str, otype: str, name: str = "", structure: dict | None = None) -> KnowledgeObject:
    return KnowledgeObject(
        identity=ObjectIdentity(id=oid, type=otype, name=name or oid),
        structure=structure or {},
    )


def make_relation(oid: str, participants: list[str], relation_type: str) -> KnowledgeObject:
    from cks.core import CanonicalRelation
    return CanonicalRelation(
        identity=ObjectIdentity(id=oid, type="Relation", name=oid),
        participants=participants,
        relation_type=relation_type,
    )


# ----------------------------------------------------------------------
# TypeHierarchy
# ----------------------------------------------------------------------

def test_empty_structure_has_empty_hierarchy():
    structure = KnowledgeStructure([make_object("a", "Thing")])
    h = TypeHierarchy(structure)
    assert not h.is_subtype("Thing", "Anything")


def test_direct_parent():
    structure = KnowledgeStructure([
        make_object("td1", TYPE_DEFINITION_TYPE, structure={"type_name": "Planet", "parent_type": "CelestialBody"}),
        make_object("td2", TYPE_DEFINITION_TYPE, structure={"type_name": "CelestialBody"}),
    ])
    h = TypeHierarchy(structure)
    assert h.is_subtype("Planet", "CelestialBody")
    assert h.is_subtype("CelestialBody", "CelestialBody")
    assert not h.is_subtype("CelestialBody", "Planet")


def test_transitive_subtype():
    structure = KnowledgeStructure([
        make_object("td1", TYPE_DEFINITION_TYPE, structure={"type_name": "Planet", "parent_type": "CelestialBody"}),
        make_object("td2", TYPE_DEFINITION_TYPE, structure={"type_name": "CelestialBody", "parent_type": "AstronomicalObject"}),
        make_object("td3", TYPE_DEFINITION_TYPE, structure={"type_name": "AstronomicalObject"}),
    ])
    h = TypeHierarchy(structure)
    assert h.is_subtype("Planet", "AstronomicalObject")


def test_cycle_is_not_infinite():
    """TypeHierarchy.is_subtype must terminate even on a cycle."""
    structure = KnowledgeStructure([
        make_object("td1", TYPE_DEFINITION_TYPE, structure={"type_name": "A", "parent_type": "B"}),
        make_object("td2", TYPE_DEFINITION_TYPE, structure={"type_name": "B", "parent_type": "A"}),
    ])
    h = TypeHierarchy(structure)
    # Must not loop forever.
    assert not h.is_subtype("A", "C")


def test_cyclic_types_detects_cycle():
    structure = KnowledgeStructure([
        make_object("td1", TYPE_DEFINITION_TYPE, structure={"type_name": "A", "parent_type": "B"}),
        make_object("td2", TYPE_DEFINITION_TYPE, structure={"type_name": "B", "parent_type": "A"}),
    ])
    h = TypeHierarchy(structure)
    cyclic = h.cyclic_types()
    assert "A" in cyclic
    assert "B" in cyclic


def test_cyclic_types_reports_no_false_positives():
    structure = KnowledgeStructure([
        make_object("td1", TYPE_DEFINITION_TYPE, structure={"type_name": "A", "parent_type": "B"}),
        make_object("td2", TYPE_DEFINITION_TYPE, structure={"type_name": "B"}),
        make_object("td3", TYPE_DEFINITION_TYPE, structure={"type_name": "C", "parent_type": "B"}),
    ])
    h = TypeHierarchy(structure)
    assert h.cyclic_types() == {}


# ----------------------------------------------------------------------
# TypeHierarchyCycleConstraint
# ----------------------------------------------------------------------

def test_cycle_constraint_fires_on_cycle():
    structure = KnowledgeStructure([
        make_object("td1", TYPE_DEFINITION_TYPE, structure={"type_name": "A", "parent_type": "B"}),
        make_object("td2", TYPE_DEFINITION_TYPE, structure={"type_name": "B", "parent_type": "A"}),
    ])
    diags = TypeHierarchyCycleConstraint().evaluate(structure)
    assert len(diags) == 2
    assert all(d.severity.value == "error" for d in diags)


def test_cycle_constraint_does_not_fire_without_cycle():
    structure = KnowledgeStructure([
        make_object("td1", TYPE_DEFINITION_TYPE, structure={"type_name": "A", "parent_type": "B"}),
        make_object("td2", TYPE_DEFINITION_TYPE, structure={"type_name": "B"}),
    ])
    diags = TypeHierarchyCycleConstraint().evaluate(structure)
    assert diags == []


# ----------------------------------------------------------------------
# RelationTypeConstraint
# ----------------------------------------------------------------------

def test_relation_type_constraint_allows_valid_relation():
    structure = KnowledgeStructure([
        make_object("planet", "Planet"),
        make_object("star", "Star"),
        make_relation("r1", ["planet", "star"], "orbits"),
        make_object("td", TYPE_DEFINITION_TYPE, structure={"type_name": "Planet", "parent_type": "CelestialBody"}),
        make_object("td2", TYPE_DEFINITION_TYPE, structure={"type_name": "Star", "parent_type": "CelestialBody"}),
        make_object("rule", TYPE_RULE_TYPE, structure={
            "relation_type": "orbits",
            "allowed_source_types": ["CelestialBody"],
            "allowed_target_types": ["CelestialBody"],
        }),
    ])
    diags = RelationTypeConstraint().evaluate(structure)
    assert diags == []


def test_relation_type_constraint_rejects_invalid_source():
    structure = KnowledgeStructure([
        make_object("planet", "Planet"),
        make_object("recipe", "Recipe"),
        make_relation("r1", ["planet", "recipe"], "orbits"),
        make_object("rule", TYPE_RULE_TYPE, structure={
            "relation_type": "orbits",
            "allowed_source_types": ["CelestialBody"],
            "allowed_target_types": ["CelestialBody"],
        }),
    ])
    diags = RelationTypeConstraint().evaluate(structure)
    assert "source" in diags[0].message.lower()
    assert "source" in diags[0].message.lower()


def test_relation_type_constraint_rejects_invalid_target():
    structure = KnowledgeStructure([
        make_object("star", "Star"),
        make_object("recipe", "Recipe"),
        make_relation("r1", ["star", "recipe"], "orbits"),
        make_object("rule", TYPE_RULE_TYPE, structure={
            "relation_type": "orbits",
            "allowed_source_types": ["CelestialBody"],
            "allowed_target_types": ["CelestialBody"],
        }),
    ])
    diags = RelationTypeConstraint().evaluate(structure)
    assert len(diags) == 2
    assert "target" in diags[1].message.lower()


def test_no_rules_means_no_constraint():
    structure = KnowledgeStructure([
        make_object("planet", "Planet"),
        make_object("recipe", "Recipe"),
        make_relation("r1", ["planet", "recipe"], "orbits"),
    ])
    diags = RelationTypeConstraint().evaluate(structure)
    assert diags == []


def test_rules_without_type_definitions_still_work():
    """If no TypeDefinitions exist, only exact type match is possible."""
    structure = KnowledgeStructure([
        make_object("planet", "Planet"),
        make_object("star", "Star"),
        make_relation("r1", ["planet", "star"], "orbits"),
        make_object("rule", TYPE_RULE_TYPE, structure={
            "relation_type": "orbits",
            "allowed_source_types": ["Planet"],
            "allowed_target_types": ["Star"],
        }),
    ])
    diags = RelationTypeConstraint().evaluate(structure)
    assert diags == []


def test_constraints_are_inert_without_opt_in():
    """Constraints should not fire unless explicitly registered."""
    from cks.validator import validate
    structure = KnowledgeStructure([
        make_object("a", "A"),
        make_object("b", "B"),
        make_relation("r1", ["a", "b"], "orbits"),
        make_object("rule", TYPE_RULE_TYPE, structure={
            "relation_type": "orbits",
            "allowed_source_types": ["CelestialBody"],
        }),
    ])
    result = validate(structure)  # без extra_constraints
    assert result.is_valid  # не должно быть ошибок без опт-ина


def test_constraints_fire_when_opted_in():
    """При опт-ине ограничения должны срабатывать."""
    from cks.validator import validate
    from cks.constraints.builtin import OPTIONAL_CONSTRAINTS_BY_NAME
    structure = KnowledgeStructure([
        make_object("a", "A"),
        make_object("b", "B"),
        make_relation("r1", ["a", "b"], "orbits"),
        make_object("rule", TYPE_RULE_TYPE, structure={
            "relation_type": "orbits",
            "allowed_source_types": ["CelestialBody"],
        }),
    ])
    constraint = OPTIONAL_CONSTRAINTS_BY_NAME["relation_type"]
    result = validate(structure, extra_constraints=[constraint])
    assert not result.is_valid
    assert any(d.identity == "CKS-EXT-RELATION-TYPE" for d in result.diagnostics)


def test_only_one_rule_per_relation_type():
    """Если объявлено несколько правил для одного relation_type,
    последнее (по порядку в structure) должно выигрывать."""
    structure = KnowledgeStructure([
        make_object("planet", "Planet"),
        make_object("star", "Star"),
        make_relation("r1", ["planet", "star"], "orbits"),
        make_object("rule1", TYPE_RULE_TYPE, structure={
            "relation_type": "orbits",
            "allowed_source_types": ["CelestialBody"],
        }),
        make_object("rule2", TYPE_RULE_TYPE, structure={
            "relation_type": "orbits",
            "allowed_source_types": ["Planet"],
        }),
    ])
    diags = RelationTypeConstraint().evaluate(structure)
    # Второе правило разрешает Planet, так что диагностик быть не должно.
    assert diags == []


def test_relation_type_constraint_ignores_non_two_participant_relations():
    """Связи с числом участников, отличным от 2, должны игнорироваться."""
    from cks.core import CanonicalRelation
    structure = KnowledgeStructure([
        make_object("a", "A"),
        make_object("b", "B"),
        make_object("c", "C"),
        CanonicalRelation(
            identity=ObjectIdentity(id="r1", type="Relation", name="r1"),
            participants=["a", "b", "c"],
            relation_type="orbits",
        ),
        make_object("rule", TYPE_RULE_TYPE, structure={
            "relation_type": "orbits",
            "allowed_source_types": ["CelestialBody"],
        }),
    ])
    diags = RelationTypeConstraint().evaluate(structure)
    assert diags == []  # не должно быть ошибок для тройной связи