"""
Tests for the optional reasoning-object constraints (InferenceStep
referential integrity, confidence bounds, and supersession chains).

See ADR-001 ("Reasoning Objects").
"""

from cks.constraints.reasoning import (
    INFERENCE_STEP_TYPE,
    ConfidenceBoundsConstraint,
    InferenceConfidenceConflictConstraint,
    InferenceReferentialIntegrityConstraint,
    SupersessionChainConstraint,
)
from cks.core import KnowledgeObject, KnowledgeStructure, ObjectIdentity
from cks.diagnostics import DiagnosticSeverity


def make_object(oid: str, otype: str, name: str = "", structure: dict | None = None) -> KnowledgeObject:
    return KnowledgeObject(
        identity=ObjectIdentity(id=oid, type=otype, name=name or oid),
        structure=structure or {},
    )


def make_inference_step(
    oid: str,
    *,
    premises: list[str] | None = None,
    conclusion: str | None = None,
    confidence: float | None = None,
    superseded_by: str | None = None,
) -> KnowledgeObject:
    structure: dict = {}
    if premises is not None:
        structure["premises"] = premises
    if conclusion is not None:
        structure["conclusion"] = conclusion
    if confidence is not None:
        structure["confidence"] = confidence
    if superseded_by is not None:
        structure["superseded_by"] = superseded_by
    return make_object(oid, INFERENCE_STEP_TYPE, structure=structure)


# ---------------------------------------------------------------------------
# InferenceReferentialIntegrityConstraint
# ---------------------------------------------------------------------------


def test_referential_integrity_passes_without_any_inference_step():
    structure = KnowledgeStructure([make_object("a", "Claim")])
    assert InferenceReferentialIntegrityConstraint().evaluate(structure) == []


def test_referential_integrity_passes_when_premises_and_conclusion_exist():
    structure = KnowledgeStructure([
        make_object("p1", "Claim"),
        make_object("p2", "Claim"),
        make_object("c1", "Claim"),
        make_inference_step("step-1", premises=["p1", "p2"], conclusion="c1"),
    ])
    assert InferenceReferentialIntegrityConstraint().evaluate(structure) == []


def test_referential_integrity_flags_unknown_premise():
    structure = KnowledgeStructure([
        make_object("c1", "Claim"),
        make_inference_step("step-1", premises=["missing"], conclusion="c1"),
    ])
    diagnostics = InferenceReferentialIntegrityConstraint().evaluate(structure)
    assert len(diagnostics) == 1
    assert diagnostics[0].identity == "CKS-EXT-INFERENCE-REFERENTIAL-INTEGRITY"
    assert diagnostics[0].location == "step-1"
    assert "missing" in diagnostics[0].message


def test_referential_integrity_flags_unknown_conclusion():
    structure = KnowledgeStructure([
        make_object("p1", "Claim"),
        make_inference_step("step-1", premises=["p1"], conclusion="missing"),
    ])
    diagnostics = InferenceReferentialIntegrityConstraint().evaluate(structure)
    assert len(diagnostics) == 1
    assert "missing" in diagnostics[0].message


def test_referential_integrity_accumulates_multiple_violations():
    structure = KnowledgeStructure([
        make_inference_step("step-1", premises=["p1", "p2"], conclusion="missing"),
    ])
    diagnostics = InferenceReferentialIntegrityConstraint().evaluate(structure)
    # p1, p2, and the conclusion are all unknown -- three diagnostics.
    assert len(diagnostics) == 3


def test_referential_integrity_ignores_non_inference_step_objects():
    structure = KnowledgeStructure([
        make_object("unrelated", "Thing", structure={"premises": ["missing"]}),
    ])
    assert InferenceReferentialIntegrityConstraint().evaluate(structure) == []


# ---------------------------------------------------------------------------
# ConfidenceBoundsConstraint
# ---------------------------------------------------------------------------


def test_confidence_bounds_passes_without_confidence_field():
    structure = KnowledgeStructure([
        make_inference_step("step-1", premises=[], conclusion="c1"),
    ])
    assert ConfidenceBoundsConstraint().evaluate(structure) == []


def test_confidence_bounds_passes_within_range():
    structure = KnowledgeStructure([
        make_inference_step("step-1", conclusion="c1", confidence=0.75),
    ])
    assert ConfidenceBoundsConstraint().evaluate(structure) == []


def test_confidence_bounds_accepts_boundary_values():
    structure = KnowledgeStructure([
        make_inference_step("step-1", conclusion="c1", confidence=0.0),
        make_inference_step("step-2", conclusion="c1", confidence=1.0),
    ])
    assert ConfidenceBoundsConstraint().evaluate(structure) == []


def test_confidence_bounds_flags_out_of_range_value():
    structure = KnowledgeStructure([
        make_inference_step("step-1", conclusion="c1", confidence=1.5),
    ])
    diagnostics = ConfidenceBoundsConstraint().evaluate(structure)
    assert len(diagnostics) == 1
    assert diagnostics[0].identity == "CKS-EXT-CONFIDENCE-BOUNDS"
    assert diagnostics[0].location == "step-1"


def test_confidence_bounds_flags_negative_value():
    structure = KnowledgeStructure([
        make_inference_step("step-1", conclusion="c1", confidence=-0.1),
    ])
    assert len(ConfidenceBoundsConstraint().evaluate(structure)) == 1


def test_confidence_bounds_flags_non_numeric_value():
    structure = KnowledgeStructure([
        make_object(
            "step-1",
            INFERENCE_STEP_TYPE,
            structure={"conclusion": "c1", "confidence": "high"},
        ),
    ])
    diagnostics = ConfidenceBoundsConstraint().evaluate(structure)
    assert len(diagnostics) == 1
    assert "non-numeric" in diagnostics[0].message


def test_confidence_bounds_rejects_bool_as_numeric():
    """bool is a subclass of int/Real in Python -- confidence=True must
    not silently pass as 1.0."""
    structure = KnowledgeStructure([
        make_object(
            "step-1",
            INFERENCE_STEP_TYPE,
            structure={"conclusion": "c1", "confidence": True},
        ),
    ])
    diagnostics = ConfidenceBoundsConstraint().evaluate(structure)
    assert len(diagnostics) == 1
    assert "non-numeric" in diagnostics[0].message


# ---------------------------------------------------------------------------
# SupersessionChainConstraint
# ---------------------------------------------------------------------------


def test_supersession_passes_without_any_reference():
    structure = KnowledgeStructure([
        make_inference_step("step-1", conclusion="c1"),
    ])
    assert SupersessionChainConstraint().evaluate(structure) == []


def test_supersession_passes_when_successor_targets_same_conclusion():
    structure = KnowledgeStructure([
        make_inference_step("step-1", conclusion="c1", superseded_by="step-2"),
        make_inference_step("step-2", conclusion="c1"),
    ])
    assert SupersessionChainConstraint().evaluate(structure) == []


def test_supersession_flags_unknown_successor():
    structure = KnowledgeStructure([
        make_inference_step("step-1", conclusion="c1", superseded_by="missing"),
    ])
    diagnostics = SupersessionChainConstraint().evaluate(structure)
    assert len(diagnostics) == 1
    assert diagnostics[0].identity == "CKS-EXT-SUPERSESSION-CHAIN"
    assert "missing" in diagnostics[0].message


def test_supersession_flags_successor_of_wrong_type():
    structure = KnowledgeStructure([
        make_inference_step("step-1", conclusion="c1", superseded_by="not-a-step"),
        make_object("not-a-step", "Claim"),
    ])
    diagnostics = SupersessionChainConstraint().evaluate(structure)
    assert len(diagnostics) == 1
    assert "not an InferenceStep" in diagnostics[0].message


def test_supersession_flags_successor_with_different_conclusion():
    structure = KnowledgeStructure([
        make_inference_step("step-1", conclusion="c1", superseded_by="step-2"),
        make_inference_step("step-2", conclusion="c2"),
    ])
    diagnostics = SupersessionChainConstraint().evaluate(structure)
    assert len(diagnostics) == 1
    assert "different conclusion" in diagnostics[0].message


# ---------------------------------------------------------------------------
# InferenceConfidenceConflictConstraint
# ---------------------------------------------------------------------------


def test_confidence_conflict_passes_without_any_inference_step():
    structure = KnowledgeStructure([make_object("a", "Claim")])
    assert InferenceConfidenceConflictConstraint().evaluate(structure) == []


def test_confidence_conflict_passes_with_single_step():
    structure = KnowledgeStructure([
        make_inference_step("step-1", conclusion="c1", confidence=0.6),
    ])
    assert InferenceConfidenceConflictConstraint().evaluate(structure) == []


def test_confidence_conflict_passes_when_confidences_agree():
    structure = KnowledgeStructure([
        make_inference_step("step-1", conclusion="c1", confidence=0.6),
        make_inference_step("step-2", conclusion="c1", confidence=0.6),
    ])
    assert InferenceConfidenceConflictConstraint().evaluate(structure) == []


def test_confidence_conflict_flags_disagreeing_confidence_same_conclusion():
    structure = KnowledgeStructure([
        make_inference_step("step-1", conclusion="c1", confidence=0.9),
        make_inference_step("step-2", conclusion="c1", confidence=0.2),
    ])
    diagnostics = InferenceConfidenceConflictConstraint().evaluate(structure)
    assert len(diagnostics) == 1
    assert diagnostics[0].identity == "CKS-EXT-INFERENCE-CONFIDENCE-CONFLICT"
    assert diagnostics[0].severity == DiagnosticSeverity.WARNING
    assert "step-1" in diagnostics[0].message
    assert "step-2" in diagnostics[0].message


def test_confidence_conflict_ignores_different_conclusions():
    structure = KnowledgeStructure([
        make_inference_step("step-1", conclusion="c1", confidence=0.9),
        make_inference_step("step-2", conclusion="c2", confidence=0.2),
    ])
    assert InferenceConfidenceConflictConstraint().evaluate(structure) == []


def test_confidence_conflict_excludes_superseded_step_from_comparison():
    """step-1 disagrees with step-2, but step-1 has been explicitly
    revised by step-2 (same conclusion) -- that's a resolved revision,
    not a live conflict, so only non-superseded steps are compared."""
    structure = KnowledgeStructure([
        make_inference_step(
            "step-1", conclusion="c1", confidence=0.2, superseded_by="step-2"
        ),
        make_inference_step("step-2", conclusion="c1", confidence=0.9),
    ])
    assert InferenceConfidenceConflictConstraint().evaluate(structure) == []


def test_confidence_conflict_still_flags_among_remaining_active_steps():
    """step-1 is superseded by step-2 and drops out, but step-3 (also
    active, same conclusion) still disagrees with step-2."""
    structure = KnowledgeStructure([
        make_inference_step(
            "step-1", conclusion="c1", confidence=0.1, superseded_by="step-2"
        ),
        make_inference_step("step-2", conclusion="c1", confidence=0.9),
        make_inference_step("step-3", conclusion="c1", confidence=0.4),
    ])
    diagnostics = InferenceConfidenceConflictConstraint().evaluate(structure)
    assert len(diagnostics) == 1
    assert "step-1" not in diagnostics[0].message
    assert "step-2" in diagnostics[0].message
    assert "step-3" in diagnostics[0].message


def test_confidence_conflict_ignores_steps_missing_confidence_or_conclusion():
    structure = KnowledgeStructure([
        make_inference_step("step-1", conclusion="c1"),  # no confidence
        make_inference_step("step-2", confidence=0.5),  # no conclusion
    ])
    assert InferenceConfidenceConflictConstraint().evaluate(structure) == []


def test_confidence_conflict_ignores_invalid_confidence_values():
    """Out-of-range/non-numeric confidence is ConfidenceBoundsConstraint's
    concern; this constraint only compares already-valid values."""
    structure = KnowledgeStructure([
        make_inference_step("step-1", conclusion="c1", confidence=0.5),
        make_object(
            "step-2",
            INFERENCE_STEP_TYPE,
            structure={"conclusion": "c1", "confidence": "high"},
        ),
        make_inference_step("step-3", conclusion="c1", confidence=1.7),
    ])
    assert InferenceConfidenceConflictConstraint().evaluate(structure) == []


def test_confidence_conflict_groups_more_than_two_distinct_values():
    structure = KnowledgeStructure([
        make_inference_step("step-1", conclusion="c1", confidence=0.9),
        make_inference_step("step-2", conclusion="c1", confidence=0.5),
        make_inference_step("step-3", conclusion="c1", confidence=0.1),
    ])
    diagnostics = InferenceConfidenceConflictConstraint().evaluate(structure)
    assert len(diagnostics) == 1
    for step_id in ("step-1", "step-2", "step-3"):
        assert step_id in diagnostics[0].message


# ---------------------------------------------------------------------------
# Opt-in behaviour via the full validator
# ---------------------------------------------------------------------------


def test_reasoning_constraints_are_inert_without_opt_in():
    from cks.validator import validate

    structure = KnowledgeStructure([
        make_inference_step("step-1", premises=["missing"], conclusion="also-missing"),
    ])
    result = validate(structure)
    assert result.is_valid


def test_reasoning_constraints_fire_when_opted_in():
    from cks.constraints.builtin import OPTIONAL_CONSTRAINTS_BY_NAME
    from cks.validator import validate

    structure = KnowledgeStructure([
        make_inference_step("step-1", premises=["missing"], conclusion="c1"),
    ])
    constraint = OPTIONAL_CONSTRAINTS_BY_NAME["inference_referential_integrity"]
    result = validate(structure, extra_constraints=[constraint])
    assert not result.is_valid
    assert any(
        d.identity == "CKS-EXT-INFERENCE-REFERENTIAL-INTEGRITY"
        for d in result.diagnostics
    )


def test_all_four_reasoning_constraints_registered_as_optional():
    from cks.constraints.builtin import BUILTIN_CONSTRAINTS, OPTIONAL_CONSTRAINTS

    builtin_identities = [c.identity for c in BUILTIN_CONSTRAINTS]
    optional_identities = [c.identity for c in OPTIONAL_CONSTRAINTS]

    for identity in (
        "CKS-EXT-INFERENCE-REFERENTIAL-INTEGRITY",
        "CKS-EXT-CONFIDENCE-BOUNDS",
        "CKS-EXT-SUPERSESSION-CHAIN",
        "CKS-EXT-INFERENCE-CONFIDENCE-CONFLICT",
    ):
        assert identity not in builtin_identities
        assert identity in optional_identities
