"""
Tests for the optional reasoning-object constraints (InferenceStep
referential integrity, confidence bounds, supersession chains, and
belief revision support).

See ADR-001 ("Reasoning Objects") and ADR-002 ("Belief Revision
Support").
"""

from cks.constraints.reasoning import (
    INFERENCE_STEP_TYPE,
    ConfidenceBoundsConstraint,
    InferenceConfidenceConflictConstraint,
    InferenceReferentialIntegrityConstraint,
    StalePremiseConstraint,
    SupersessionChainConstraint,
    rank_by_entrenchment,
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


def test_supersession_passes_for_a_terminating_chain():
    """A -> B -> C, C not superseded: a normal, non-cyclic revision
    chain, however long, must not be flagged."""
    structure = KnowledgeStructure([
        make_inference_step("a", conclusion="c1", superseded_by="b"),
        make_inference_step("b", conclusion="c1", superseded_by="c"),
        make_inference_step("c", conclusion="c1"),
    ])
    assert SupersessionChainConstraint().evaluate(structure) == []


def test_supersession_flags_direct_two_cycle():
    structure = KnowledgeStructure([
        make_inference_step("a", conclusion="c1", superseded_by="b"),
        make_inference_step("b", conclusion="c1", superseded_by="a"),
    ])
    diagnostics = SupersessionChainConstraint().evaluate(structure)
    cycle_diagnostics = [d for d in diagnostics if "cycle" in d.message.lower()]
    assert len(cycle_diagnostics) == 1
    assert "a" in cycle_diagnostics[0].message
    assert "b" in cycle_diagnostics[0].message


def test_supersession_flags_longer_cycle_exactly_once():
    """A -> B -> C -> A: one cycle, one diagnostic, regardless of
    which member the scan reaches first."""
    structure = KnowledgeStructure([
        make_inference_step("a", conclusion="c1", superseded_by="b"),
        make_inference_step("b", conclusion="c1", superseded_by="c"),
        make_inference_step("c", conclusion="c1", superseded_by="a"),
    ])
    diagnostics = SupersessionChainConstraint().evaluate(structure)
    cycle_diagnostics = [d for d in diagnostics if "cycle" in d.message.lower()]
    assert len(cycle_diagnostics) == 1
    for step_id in ("a", "b", "c"):
        assert step_id in cycle_diagnostics[0].message


def test_supersession_cycle_detection_does_not_duplicate_pairwise_errors():
    """A self-cycle where the successor otherwise passes every
    pairwise check (exists, is an InferenceStep, same conclusion)
    should add exactly the cycle diagnostic -- no duplicate pairwise
    errors for the same link."""
    structure = KnowledgeStructure([
        make_inference_step("a", conclusion="c1", superseded_by="a"),
    ])
    diagnostics = SupersessionChainConstraint().evaluate(structure)
    assert len(diagnostics) == 1
    assert "cycle" in diagnostics[0].message.lower()


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
# StalePremiseConstraint
# ---------------------------------------------------------------------------


def test_stale_premise_passes_without_any_inference_step():
    structure = KnowledgeStructure([make_object("a", "Claim")])
    assert StalePremiseConstraint().evaluate(structure) == []


def test_stale_premise_passes_when_premise_is_an_ordinary_object():
    """The premise id names a Claim, not an InferenceStep -- out of
    scope for this constraint regardless of anything else about it."""
    structure = KnowledgeStructure([
        make_object("p1", "Claim"),
        make_inference_step("step-1", premises=["p1"], conclusion="c1"),
    ])
    assert StalePremiseConstraint().evaluate(structure) == []


def test_stale_premise_passes_when_cited_step_is_still_active():
    structure = KnowledgeStructure([
        make_inference_step("base", premises=[], conclusion="p1"),
        make_inference_step("dependent", premises=["base"], conclusion="c1"),
    ])
    assert StalePremiseConstraint().evaluate(structure) == []


def test_stale_premise_flags_premise_citing_a_superseded_inference_step():
    structure = KnowledgeStructure([
        make_inference_step(
            "base", premises=[], conclusion="p1", superseded_by="revised"
        ),
        make_inference_step("revised", premises=[], conclusion="p1"),
        make_inference_step("dependent", premises=["base"], conclusion="c1"),
    ])
    diagnostics = StalePremiseConstraint().evaluate(structure)
    assert len(diagnostics) == 1
    assert diagnostics[0].identity == "CKS-EXT-STALE-PREMISE"
    assert diagnostics[0].severity == DiagnosticSeverity.WARNING
    assert diagnostics[0].location == "dependent"
    assert "base" in diagnostics[0].message
    assert "revised" in diagnostics[0].message


def test_stale_premise_ignores_a_superseded_dependent():
    """`dependent` itself has already been revised away -- its own
    premises no longer matter going forward, so a stale citation under
    an already-superseded step is not flagged."""
    structure = KnowledgeStructure([
        make_inference_step(
            "base", premises=[], conclusion="p1", superseded_by="revised"
        ),
        make_inference_step("revised", premises=[], conclusion="p1"),
        make_inference_step(
            "dependent",
            premises=["base"],
            conclusion="c1",
            superseded_by="dependent-2",
        ),
        make_inference_step("dependent-2", premises=[], conclusion="c1"),
    ])
    assert StalePremiseConstraint().evaluate(structure) == []


def test_stale_premise_accumulates_multiple_stale_citations():
    structure = KnowledgeStructure([
        make_inference_step("a", premises=[], conclusion="p1", superseded_by="a2"),
        make_inference_step("a2", premises=[], conclusion="p1"),
        make_inference_step("b", premises=[], conclusion="p2", superseded_by="b2"),
        make_inference_step("b2", premises=[], conclusion="p2"),
        make_inference_step("dependent", premises=["a", "b"], conclusion="c1"),
    ])
    diagnostics = StalePremiseConstraint().evaluate(structure)
    assert len(diagnostics) == 2


# ---------------------------------------------------------------------------
# rank_by_entrenchment
# ---------------------------------------------------------------------------


def test_rank_by_entrenchment_returns_empty_for_unknown_conclusion():
    structure = KnowledgeStructure([
        make_inference_step("step-1", conclusion="c1", confidence=0.5),
    ])
    assert rank_by_entrenchment(structure, "missing") == []


def test_rank_by_entrenchment_orders_by_confidence_descending():
    structure = KnowledgeStructure([
        make_inference_step("low", conclusion="c1", confidence=0.2),
        make_inference_step("high", conclusion="c1", confidence=0.9),
        make_inference_step("mid", conclusion="c1", confidence=0.5),
    ])
    ranked = rank_by_entrenchment(structure, "c1")
    assert [step.identity.id for step in ranked] == ["high", "mid", "low"]


def test_rank_by_entrenchment_excludes_superseded_steps():
    structure = KnowledgeStructure([
        make_inference_step(
            "old", conclusion="c1", confidence=0.9, superseded_by="new"
        ),
        make_inference_step("new", conclusion="c1", confidence=0.4),
    ])
    ranked = rank_by_entrenchment(structure, "c1")
    assert [step.identity.id for step in ranked] == ["new"]


def test_rank_by_entrenchment_sorts_invalid_confidence_last_not_dropped():
    structure = KnowledgeStructure([
        make_inference_step("valid", conclusion="c1", confidence=0.3),
        make_object(
            "no-confidence",
            INFERENCE_STEP_TYPE,
            structure={"conclusion": "c1"},
        ),
    ])
    ranked = rank_by_entrenchment(structure, "c1")
    assert [step.identity.id for step in ranked] == ["valid", "no-confidence"]


def test_rank_by_entrenchment_stable_tiebreak_on_equal_confidence():
    structure = KnowledgeStructure([
        make_inference_step("first", conclusion="c1", confidence=0.5),
        make_inference_step("second", conclusion="c1", confidence=0.5),
    ])
    ranked = rank_by_entrenchment(structure, "c1")
    assert [step.identity.id for step in ranked] == ["first", "second"]


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


def test_all_five_reasoning_constraints_registered_as_optional():
    from cks.constraints.builtin import BUILTIN_CONSTRAINTS, OPTIONAL_CONSTRAINTS

    builtin_identities = [c.identity for c in BUILTIN_CONSTRAINTS]
    optional_identities = [c.identity for c in OPTIONAL_CONSTRAINTS]

    for identity in (
        "CKS-EXT-INFERENCE-REFERENTIAL-INTEGRITY",
        "CKS-EXT-CONFIDENCE-BOUNDS",
        "CKS-EXT-SUPERSESSION-CHAIN",
        "CKS-EXT-INFERENCE-CONFIDENCE-CONFLICT",
        "CKS-EXT-STALE-PREMISE",
    ):
        assert identity not in builtin_identities
        assert identity in optional_identities


def test_stale_premise_registered_by_name():
    from cks.constraints.builtin import OPTIONAL_CONSTRAINTS_BY_NAME

    assert (
        OPTIONAL_CONSTRAINTS_BY_NAME["stale_premise"].identity
        == "CKS-EXT-STALE-PREMISE"
    )