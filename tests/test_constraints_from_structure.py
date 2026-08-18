"""
Tests for the "Constraints-as-Data" pilot: ``OntologyRule`` objects
declared inside a KnowledgeStructure, loaded via
``cks.constraints.from_structure`` and opted in through
``include_structure_constraints=True``.
"""

from cks.constraints.from_structure import (
    ONTOLOGY_RULE_TYPE,
    load_dynamic_constraints,
)
from cks.constraints.registry import registry as _global_registry
from cks.core import (
    CanonicalRelation,
    KnowledgeObject,
    KnowledgeStructure,
    ObjectIdentity,
)
from cks.diagnostics import DiagnosticSeverity
from cks.engine import ReferenceEngine
from cks.validator import validate


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


def make_ontology_rule(
    oid: str,
    constraint_type: str,
    *,
    target_relation_type: str | None = None,
    parameters: dict | None = None,
    enabled: bool | None = None,
) -> KnowledgeObject:
    structure: dict = {"constraint_type": constraint_type}
    if target_relation_type is not None:
        structure["target_relation_type"] = target_relation_type
    if parameters is not None:
        structure["parameters"] = parameters
    if enabled is not None:
        structure["enabled"] = enabled
    return make_object(oid, ONTOLOGY_RULE_TYPE, structure=structure)


# ---------------------------------------------------------------------------
# Default validation does not load OntologyRule objects
# ---------------------------------------------------------------------------


def test_default_validate_ignores_ontology_rule():
    structure = KnowledgeStructure([
        make_object("earth", "Thing"),
        make_object("sun", "Thing"),
        make_object("mars", "Thing"),
        make_relation("r1", ["earth", "sun"], "orbits"),
        make_relation("r2", ["earth", "mars"], "orbits"),
        make_ontology_rule(
            "rule-1", "functional_relation", target_relation_type="orbits"
        ),
    ])
    result = validate(structure)
    assert result.is_valid


def test_default_engine_validate_ignores_ontology_rule():
    structure = KnowledgeStructure([
        make_object("earth", "Thing"),
        make_object("sun", "Thing"),
        make_object("mars", "Thing"),
        make_relation("r1", ["earth", "sun"], "orbits"),
        make_relation("r2", ["earth", "mars"], "orbits"),
        make_ontology_rule(
            "rule-1", "functional_relation", target_relation_type="orbits"
        ),
    ])
    result = ReferenceEngine().validate(structure)
    assert result.is_valid


# ---------------------------------------------------------------------------
# include_structure_constraints=True enforces a valid rule
# ---------------------------------------------------------------------------


def test_opt_in_enforces_functional_relation_rule():
    structure = KnowledgeStructure([
        make_object("earth", "Thing"),
        make_object("sun", "Thing"),
        make_object("mars", "Thing"),
        make_relation("r1", ["earth", "sun"], "orbits"),
        make_relation("r2", ["earth", "mars"], "orbits"),
        make_ontology_rule(
            "rule-1", "functional_relation", target_relation_type="orbits"
        ),
    ])
    result = validate(structure, include_structure_constraints=True)
    assert not result.is_valid
    assert any(
        "functional" in d.message.lower() or "orbits" in d.message.lower()
        for d in result.diagnostics
    )


def test_opt_in_passes_when_rule_is_satisfied():
    structure = KnowledgeStructure([
        make_object("earth", "Thing"),
        make_object("sun", "Thing"),
        make_relation("r1", ["earth", "sun"], "orbits"),
        make_ontology_rule(
            "rule-1", "functional_relation", target_relation_type="orbits"
        ),
    ])
    result = validate(structure, include_structure_constraints=True)
    assert result.is_valid


def test_opt_in_enforces_mutual_exclusion_rule():
    structure = KnowledgeStructure([
        make_object("earth", "Thing"),
        make_object("theoryx", "Thing"),
        make_relation("r1", ["earth", "theoryx"], "supports"),
        make_relation("r2", ["earth", "theoryx"], "contradicts"),
        make_ontology_rule(
            "rule-1",
            "mutual_exclusion",
            parameters={"relation_type_a": "supports", "relation_type_b": "contradicts"},
        ),
    ])
    result = validate(structure, include_structure_constraints=True)
    assert not result.is_valid


# ---------------------------------------------------------------------------
# A disabled rule is ignored
# ---------------------------------------------------------------------------


def test_disabled_rule_is_ignored():
    structure = KnowledgeStructure([
        make_object("earth", "Thing"),
        make_object("sun", "Thing"),
        make_object("mars", "Thing"),
        make_relation("r1", ["earth", "sun"], "orbits"),
        make_relation("r2", ["earth", "mars"], "orbits"),
        make_ontology_rule(
            "rule-1",
            "functional_relation",
            target_relation_type="orbits",
            enabled=False,
        ),
    ])
    result = validate(structure, include_structure_constraints=True)
    assert result.is_valid
    assert load_dynamic_constraints(structure) == ()


# ---------------------------------------------------------------------------
# Unknown constraint_type is handled gracefully
# ---------------------------------------------------------------------------


def test_unknown_constraint_type_is_ignored():
    structure = KnowledgeStructure([
        make_object("a", "Thing"),
        make_ontology_rule("rule-1", "some_future_constraint_type"),
    ])
    result = validate(structure, include_structure_constraints=True)
    assert result.is_valid
    assert load_dynamic_constraints(structure) == ()


# ---------------------------------------------------------------------------
# Malformed rule produces a clear diagnostic
# ---------------------------------------------------------------------------


def test_malformed_functional_relation_rule_produces_diagnostic():
    structure = KnowledgeStructure([
        make_object("a", "Thing"),
        make_ontology_rule("rule-1", "functional_relation"),  # missing target_relation_type
    ])
    result = validate(structure, include_structure_constraints=True)
    assert not result.is_valid
    assert any(
        d.severity == DiagnosticSeverity.ERROR and "rule-1" in (d.location or "")
        for d in result.diagnostics
    )


def test_malformed_mutual_exclusion_rule_produces_diagnostic():
    structure = KnowledgeStructure([
        make_object("a", "Thing"),
        make_ontology_rule(
            "rule-1", "mutual_exclusion", parameters={"relation_type_a": "supports"}
        ),
    ])
    result = validate(structure, include_structure_constraints=True)
    assert not result.is_valid
    assert any("rule-1" in (d.location or "") for d in result.diagnostics)


# ---------------------------------------------------------------------------
# Existing built-in constraints still work when dynamic constraints enabled
# ---------------------------------------------------------------------------


def test_builtin_constraints_still_run_when_opted_in():
    dangling_relation = KnowledgeStructure([
        make_object("a", "Thing"),
        make_relation("r1", ["a", "missing"], "orbits"),
    ])
    result = validate(dangling_relation, include_structure_constraints=True)
    assert not result.is_valid


# ---------------------------------------------------------------------------
# The global registry is not changed by dynamic validation calls
# ---------------------------------------------------------------------------


def test_global_registry_unaffected_by_dynamic_validation():
    before = set(_global_registry.names())
    structure = KnowledgeStructure([
        make_object("earth", "Thing"),
        make_object("sun", "Thing"),
        make_object("mars", "Thing"),
        make_relation("r1", ["earth", "sun"], "orbits"),
        make_relation("r2", ["earth", "mars"], "orbits"),
        make_ontology_rule(
            "rule-1", "functional_relation", target_relation_type="orbits"
        ),
    ])
    validate(structure, include_structure_constraints=True)
    after = set(_global_registry.names())
    assert before == after
