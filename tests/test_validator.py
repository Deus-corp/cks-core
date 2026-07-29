"""Unit tests for the CKS validation pipeline."""

import json

import pytest

from cks.constraints.base import Constraint
from cks.core import (
    CanonicalRelation,
    KnowledgeObject,
    KnowledgeStructure,
    ObjectIdentity,
)
from cks.diagnostics import Diagnostic, DiagnosticSeverity
from cks.serialization import SerializationError, parse, serialize
from cks.validation import ValidationStage
from cks.validator import validate


def make_object(oid: str, otype: str = "Definition", name: str = "") -> KnowledgeObject:
    return KnowledgeObject(
        identity=ObjectIdentity(id=oid, type=otype, name=name or oid)
    )


def make_relation(
    oid: str,
    participants: list[str],
    relation_type: str = "depends_on",
) -> CanonicalRelation:
    return CanonicalRelation(
        identity=ObjectIdentity(id=oid, type="Relation", name=oid),
        participants=participants,
        relation_type=relation_type,
    )


def make_structure() -> KnowledgeStructure:
    return KnowledgeStructure([
        make_object("obj-1", "Definition", "Knowledge Object"),
        make_object("obj-2", "Theorem", "Representation Independence"),
        make_relation("rel-1", ["obj-1", "obj-2"]),
    ])


# ---------------------------------------------------------------------------
# T1 — Parse correctly deserializes a minimal valid KnowledgeStructure
# ---------------------------------------------------------------------------

def test_parse_minimal_valid_structure():
    json_str = json.dumps({
        "objects": [
            {
                "identity": {"id": "obj-1", "type": "Definition", "name": "Test"},
                "structure": {},
            }
        ]
    })
    structure = parse(json_str)
    assert len(structure.objects) == 1
    assert structure.objects[0].identity.id == "obj-1"


# ---------------------------------------------------------------------------
# T2 — serialize followed by parse is structurally equivalent
# ---------------------------------------------------------------------------

def test_serialize_parse_roundtrip():
    original = make_structure()
    json_str = serialize(original)
    restored = parse(json_str)
    orig_ids = {obj.identity.id for obj in original.objects}
    rest_ids = {obj.identity.id for obj in restored.objects}
    assert orig_ids == rest_ids


# ---------------------------------------------------------------------------
# T3 — validate returns is_valid=True for a valid structure
# ---------------------------------------------------------------------------

def test_valid_structure():
    result = validate(make_structure())
    assert result.is_valid is True


# ---------------------------------------------------------------------------
# T4 — validate returns is_valid=False for a structure with a missing required object
# ---------------------------------------------------------------------------

def test_missing_reference():
    structure = KnowledgeStructure([
        make_object("obj-1"),
        make_relation("rel-1", ["obj-1", "missing"]),
    ])
    result = validate(structure)
    assert not result.is_valid
    # Ошибка: dangling reference
    assert any(d.severity == DiagnosticSeverity.ERROR for d in result.diagnostics)


# ---------------------------------------------------------------------------
# T5 — validate returns is_valid=False for a structure with a dangling reference
# ---------------------------------------------------------------------------

def test_relation_without_existing_objects():
    structure = KnowledgeStructure([
        make_relation("rel", ["a", "b"]),
    ])
    result = validate(structure)
    assert not result.is_valid
    # Ошибки: dangling references (оба участника не существуют)
    assert any(d.severity == DiagnosticSeverity.ERROR for d in result.diagnostics)


# ---------------------------------------------------------------------------
# T6 — validate returns is_valid=False for a structure with a duplicate identity
# ---------------------------------------------------------------------------

def test_validate_duplicate_identity():
    with pytest.raises(ValueError):
        KnowledgeStructure([
            make_object("dup"),
            make_object("dup"),
        ])


# ---------------------------------------------------------------------------
# T7 — Determinism: repeated calls produce identical output
# ---------------------------------------------------------------------------

def test_validation_is_deterministic():
    structure = make_structure()
    result1 = validate(structure)
    result2 = validate(structure)
    assert result1.is_valid == result2.is_valid
    assert len(result1.diagnostics) == len(result2.diagnostics)


# ---------------------------------------------------------------------------
# T8 — Observational purity: input structure is not modified
# ---------------------------------------------------------------------------

def test_validation_does_not_modify_structure():
    structure = make_structure()
    before = tuple(obj.identity.id for obj in structure.objects)
    validate(structure)
    after = tuple(obj.identity.id for obj in structure.objects)
    assert before == after


# ---------------------------------------------------------------------------
# T9 — Semantic and Behavioural Conformance (basic check)
# ---------------------------------------------------------------------------

def test_semantic_behavioural_conformance():
    s1 = make_structure()
    s2 = parse(serialize(s1))
    r1 = validate(s1)
    r2 = validate(s2)
    assert r1.is_valid == r2.is_valid
    assert len(r1.diagnostics) == len(r2.diagnostics)
    assert r1.evaluated_constraints == r2.evaluated_constraints


# ---------------------------------------------------------------------------
# Additional edge cases
# ---------------------------------------------------------------------------

def test_parse_invalid_json():
    with pytest.raises(SerializationError):
        parse("not json")


def test_parse_missing_objects_key():
    with pytest.raises(SerializationError):
        parse("{}")


def test_parse_duplicate_ids():
    data = {
        "objects": [
            {"identity": {"id": "dup", "type": "X", "name": "x"}, "structure": {}},
            {"identity": {"id": "dup", "type": "Y", "name": "y"}, "structure": {}},
        ]
    }
    with pytest.raises(SerializationError):
        parse(data)


def test_empty_structure_is_valid():
    result = validate(KnowledgeStructure([]))
    assert result.is_valid is True


def test_derivation_cycle():
    structure = KnowledgeStructure([
        make_object("a"),
        make_object("b"),
        make_object("c"),
        make_relation("d1", ["a", "b"], "derives"),
        make_relation("d2", ["b", "c"], "derives"),
        make_relation("d3", ["c", "a"], "derives"),
    ])
    result = validate(structure)
    assert not result.is_valid
    assert any("cycle" in d.message.lower() for d in result.diagnostics)


def test_serialize_preserves_canonical_relation():
    structure = make_structure()
    json_str = serialize(structure)
    restored = parse(json_str)
    orig_rels = structure.relations()
    rest_rels = restored.relations()
    assert len(orig_rels) == len(rest_rels)
    assert orig_rels[0].participants == rest_rels[0].participants


def test_diagnostics_info_warning_error():
    from cks.diagnostics import Diagnostic
    d_info = Diagnostic("TEST-INFO", DiagnosticSeverity.INFORMATION, "Info msg")
    d_warn = Diagnostic("TEST-WARN", DiagnosticSeverity.WARNING, "Warning msg")
    d_err = Diagnostic("TEST-ERR", DiagnosticSeverity.ERROR, "Error msg")
    assert d_info.severity == DiagnosticSeverity.INFORMATION
    assert d_warn.severity == DiagnosticSeverity.WARNING
    assert d_err.severity == DiagnosticSeverity.ERROR


# ============================================================================
# extra_constraints — scoped, per-call constraint opt-in
# ============================================================================
#
# extra_constraints lets a caller opt an OPTIONAL_CONSTRAINTS entry (or
# any other Constraint) in for a single validate() call without
# mutating the process-wide global registry.


def test_extra_constraints_applies_only_for_this_call():
    from cks.constraints.builtin import OPTIONAL_CONSTRAINTS

    structure = KnowledgeStructure([
        make_object("proj-1", otype="EmbeddingProjection"),
    ])

    with_extension = validate(structure, extra_constraints=OPTIONAL_CONSTRAINTS)
    assert not with_extension.is_valid
    assert "CKS-EXT-EMBEDDING-PROJECTION" in with_extension.evaluated_constraints

    without_extension = validate(structure)
    assert without_extension.is_valid
    assert "CKS-EXT-EMBEDDING-PROJECTION" not in without_extension.evaluated_constraints


def test_extra_constraints_does_not_mutate_global_registry():
    from cks.constraints import registry
    from cks.constraints.builtin import OPTIONAL_CONSTRAINTS

    structure = KnowledgeStructure([make_object("a")])
    validate(structure, extra_constraints=OPTIONAL_CONSTRAINTS)

    assert "CKS-EXT-EMBEDDING-PROJECTION" not in registry.names()


def test_extra_constraints_duplicate_identity_does_not_raise():
    """Re-passing a constraint identity already present must be a no-op,
    not a ValueError (unlike registry.register() on the same object)."""
    from cks.constraints.builtin import BUILTIN_CONSTRAINTS

    structure = KnowledgeStructure([make_object("a"), make_object("a2")])
    # BUILTIN_CONSTRAINTS are already in the default registry; passing
    # them again as extra_constraints must not crash.
    result = validate(structure, extra_constraints=BUILTIN_CONSTRAINTS)
    assert result.is_valid


def test_structural_semantic_constraint_validate_accept_extra_constraints():
    from cks.constraints.builtin import OPTIONAL_CONSTRAINTS
    from cks.validator import (
        evaluate_constraints,
        semantic_validate,
        structural_validate,
    )

    structure = KnowledgeStructure([
        make_object("proj-1", otype="EmbeddingProjection"),
    ])

    # The extension constraint runs at SEMANTIC stage.
    assert structural_validate(structure, extra_constraints=OPTIONAL_CONSTRAINTS) == []
    semantic_diagnostics = semantic_validate(structure, extra_constraints=OPTIONAL_CONSTRAINTS)
    assert any(d.identity == "CKS-EXT-EMBEDDING-PROJECTION" for d in semantic_diagnostics)

    constraint_diagnostics = evaluate_constraints(structure, extra_constraints=OPTIONAL_CONSTRAINTS)
    # EmbeddingProjectionIntegrityConstraint.stage is SEMANTIC, not
    # CONSTRAINTS, so the dedicated CONSTRAINTS-stage evaluator
    # correctly does not see it here (same stage-filtering fix that
    # previously stopped constraint_validate() from double-counting
    # structural/semantic diagnostics).
    assert not any(d.identity == "CKS-EXT-EMBEDDING-PROJECTION" for d in constraint_diagnostics)


# ---------------------------------------------------------------------------
# min_severity — INFORMATION-severity diagnostics must count at the
# strictest threshold
# ---------------------------------------------------------------------------
#
# Regression tests: ReferenceValidator.validate() used to exclude every
# INFORMATION-severity diagnostic from the is_valid check unconditionally,
# regardless of min_severity:
#
#     valid = all(
#         d.severity.priority < min_severity.priority
#         for d in diagnostics
#         if d.severity != DiagnosticSeverity.INFORMATION
#     )
#
# The CLI documents --min-severity information as the strictest,
# most-inclusive setting ("Minimum severity to consider a structure
# invalid"), but with that filter in place it was indistinguishable from
# 'warning': an INFORMATION diagnostic could never invalidate a structure
# no matter what min_severity was requested. No built-in constraint
# currently emits INFORMATION severity, which is exactly why this gap
# was invisible to the existing test suite -- these tests use a minimal
# synthetic constraint to exercise it directly.

class _InfoOnlyConstraint(Constraint):
    """A Constraint stub that always emits exactly one INFORMATION
    diagnostic, to exercise the min_severity threshold in isolation."""

    identity = "TEST-INFO-ONLY"
    stage = ValidationStage.SEMANTIC
    description = "Always emits one INFORMATION diagnostic."

    def evaluate(self, structure):
        return [
            Diagnostic(
                identity=self.identity,
                severity=DiagnosticSeverity.INFORMATION,
                message="just a note",
                location=None,
            )
        ]


def test_min_severity_information_invalidates_on_information_diagnostic():
    structure = KnowledgeStructure([make_object("a")])

    result = validate(
        structure,
        min_severity=DiagnosticSeverity.INFORMATION,
        extra_constraints=[_InfoOnlyConstraint()],
    )

    assert result.is_valid is False


def test_min_severity_warning_and_error_unaffected_by_information_diagnostic():
    """The fix must not change behaviour at the two thresholds that
    already worked correctly -- INFORMATION's priority (0) is below
    both WARNING (1) and ERROR (2) either way."""
    structure = KnowledgeStructure([make_object("a")])

    for min_severity in (DiagnosticSeverity.WARNING, DiagnosticSeverity.ERROR):
        result = validate(
            structure,
            min_severity=min_severity,
            extra_constraints=[_InfoOnlyConstraint()],
        )
        assert result.is_valid is True


def test_min_severity_does_not_filter_which_diagnostics_are_reported():
    """min_severity only gates is_valid -- the INFORMATION diagnostic
    itself must still show up in the report at every threshold."""
    structure = KnowledgeStructure([make_object("a")])

    for min_severity in (
        DiagnosticSeverity.ERROR,
        DiagnosticSeverity.WARNING,
        DiagnosticSeverity.INFORMATION,
    ):
        result = validate(
            structure,
            min_severity=min_severity,
            extra_constraints=[_InfoOnlyConstraint()],
        )
        assert any(d.identity == "TEST-INFO-ONLY" for d in result.diagnostics)