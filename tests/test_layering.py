"""
Tests for the optional LayeringRuleConstraint.

See ADR-004 ("Layering Rule Constraint").
"""

from cks.constraints.layering import LayeringRuleConstraint
from cks.core import (
    CanonicalRelation,
    KnowledgeObject,
    KnowledgeStructure,
    ObjectIdentity,
)
from cks.diagnostics import DiagnosticSeverity
from cks.validator import validate


def make_object(oid: str, otype: str = "Component", structure: dict | None = None) -> KnowledgeObject:
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


# ---------------------------------------------------------------------------
# LayeringRuleConstraint.evaluate()
# ---------------------------------------------------------------------------


def test_passes_for_correct_direction_runtime_depends_on_core():
    structure = KnowledgeStructure([
        make_object("cks-core"),
        make_object("cks-runtime"),
        make_relation("r1", ["cks-runtime", "cks-core"], "depends_on"),
    ])
    assert LayeringRuleConstraint().evaluate(structure) == []


def test_passes_for_correct_direction_mcp_depends_on_runtime():
    structure = KnowledgeStructure([
        make_object("cks-runtime"),
        make_object("cks-mcp"),
        make_relation("r1", ["cks-mcp", "cks-runtime"], "depends_on"),
    ])
    assert LayeringRuleConstraint().evaluate(structure) == []


def test_flags_reverse_direction_core_depends_on_runtime():
    structure = KnowledgeStructure([
        make_object("cks-core"),
        make_object("cks-runtime"),
        make_relation("r1", ["cks-core", "cks-runtime"], "depends_on"),
    ])
    diagnostics = LayeringRuleConstraint().evaluate(structure)

    assert len(diagnostics) == 1
    assert diagnostics[0].identity == "CKS-EXT-LAYERING-RULE"
    assert diagnostics[0].severity == DiagnosticSeverity.ERROR
    assert diagnostics[0].location == "r1"


def test_flags_skip_layer_violation_runtime_depends_on_mcp():
    # cks-runtime -> depends_on -> cks-mcp also points the wrong way
    # (runtime is a lower layer than mcp).
    structure = KnowledgeStructure([
        make_object("cks-runtime"),
        make_object("cks-mcp"),
        make_relation("r1", ["cks-runtime", "cks-mcp"], "depends_on"),
    ])
    diagnostics = LayeringRuleConstraint().evaluate(structure)
    assert len(diagnostics) == 1
    assert diagnostics[0].severity == DiagnosticSeverity.ERROR


def test_ignores_non_depends_on_relations():
    structure = KnowledgeStructure([
        make_object("cks-core"),
        make_object("cks-runtime"),
        make_relation("r1", ["cks-core", "cks-runtime"], "references"),
    ])
    assert LayeringRuleConstraint().evaluate(structure) == []


def test_ignores_relations_with_unrecognized_participants():
    structure = KnowledgeStructure([
        make_object("cks-core"),
        make_object("some-external-lib"),
        make_relation("r1", ["cks-core", "some-external-lib"], "depends_on"),
    ])
    assert LayeringRuleConstraint().evaluate(structure) == []


def test_passes_with_no_relations_at_all():
    structure = KnowledgeStructure([make_object("cks-core")])
    assert LayeringRuleConstraint().evaluate(structure) == []


def test_evaluates_multiple_relations_independently():
    structure = KnowledgeStructure([
        make_object("cks-core"),
        make_object("cks-runtime"),
        make_object("cks-mcp"),
        make_relation("ok-1", ["cks-runtime", "cks-core"], "depends_on"),
        make_relation("ok-2", ["cks-mcp", "cks-runtime"], "depends_on"),
        make_relation("bad-1", ["cks-core", "cks-mcp"], "depends_on"),
    ])
    diagnostics = LayeringRuleConstraint().evaluate(structure)

    assert len(diagnostics) == 1
    assert diagnostics[0].location == "bad-1"


# ---------------------------------------------------------------------------
# Opt-in through validate() / OPTIONAL_CONSTRAINTS_BY_NAME
# ---------------------------------------------------------------------------


def test_not_applied_by_default():
    structure = KnowledgeStructure([
        make_object("cks-core"),
        make_object("cks-runtime"),
        make_relation("r1", ["cks-core", "cks-runtime"], "depends_on"),
    ])
    result = validate(structure)
    assert result.is_valid


def test_fires_when_opted_in_by_name():
    from cks.constraints.builtin import OPTIONAL_CONSTRAINTS_BY_NAME

    structure = KnowledgeStructure([
        make_object("cks-core"),
        make_object("cks-runtime"),
        make_relation("r1", ["cks-core", "cks-runtime"], "depends_on"),
    ])
    constraint = OPTIONAL_CONSTRAINTS_BY_NAME["layering_rule"]

    result = validate(structure, extra_constraints=[constraint])

    assert not result.is_valid
    assert any(d.identity == "CKS-EXT-LAYERING-RULE" for d in result.diagnostics)


def test_registered_as_optional_not_builtin():
    from cks.constraints.builtin import BUILTIN_CONSTRAINTS, OPTIONAL_CONSTRAINTS

    builtin_identities = [c.identity for c in BUILTIN_CONSTRAINTS]
    optional_identities = [c.identity for c in OPTIONAL_CONSTRAINTS]

    assert "CKS-EXT-LAYERING-RULE" in optional_identities
    assert "CKS-EXT-LAYERING-RULE" not in builtin_identities
