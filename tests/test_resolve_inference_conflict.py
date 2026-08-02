"""
Unit tests for the ResolveInferenceConflict operator and its
parse_operations wire format ("resolve_inference_conflict"). See
ADR-001 ("Reasoning Objects") / ADR-002 ("Belief Revision Support"),
and cks.constraints.reasoning.InferenceConfidenceConflictConstraint,
which this operator's write-side complements.
"""

from __future__ import annotations

import pytest

from cks.constraints.reasoning import INFERENCE_STEP_TYPE
from cks.core import KnowledgeObject, KnowledgeStructure, ObjectIdentity
from cks.evolution import (
    ResolveInferenceConflict,
    compose,
    parse_operations,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_obj(oid: str, otype: str = "Claim", name: str = "") -> KnowledgeObject:
    return KnowledgeObject(
        identity=ObjectIdentity(id=oid, type=otype, name=name or oid)
    )


def _make_inference_step(
    oid: str,
    *,
    conclusion: str = "c1",
    confidence: float = 0.5,
    superseded_by: str | None = None,
    name: str = "",
) -> KnowledgeObject:
    structure = {"premises": [], "conclusion": conclusion, "confidence": confidence}
    if superseded_by is not None:
        structure["superseded_by"] = superseded_by
    return KnowledgeObject(
        identity=ObjectIdentity(id=oid, type=INFERENCE_STEP_TYPE, name=name or oid),
        structure=structure,
    )


def _make_structure(*extra: KnowledgeObject) -> KnowledgeStructure:
    return KnowledgeStructure([_make_obj("c1", name="Conclusion"), *extra])


# ===========================================================================
# Construction — validation at __init__ time
# ===========================================================================


class TestResolveInferenceConflictConstruction:
    def test_valid_construction(self) -> None:
        op = ResolveInferenceConflict("c1", "step-a")
        assert op.conclusion_id == "c1"
        assert op.winner_id == "step-a"

    @pytest.mark.parametrize("bad", ["", "   ", None])
    def test_rejects_empty_conclusion_id(self, bad) -> None:
        with pytest.raises(ValueError, match="conclusion_id"):
            ResolveInferenceConflict(bad, "step-a")

    @pytest.mark.parametrize("bad", ["", "   ", None])
    def test_rejects_empty_winner_id(self, bad) -> None:
        with pytest.raises(ValueError, match="winner_id"):
            ResolveInferenceConflict("c1", bad)

    def test_rejects_conclusion_equal_to_winner(self) -> None:
        with pytest.raises(ValueError, match="must differ"):
            ResolveInferenceConflict("same-id", "same-id")


# ===========================================================================
# Apply-time behaviour
# ===========================================================================


class TestResolveInferenceConflictApply:
    def test_supersedes_the_other_active_step(self) -> None:
        winner = _make_inference_step("step-a", confidence=0.9)
        loser = _make_inference_step("step-b", confidence=0.4)
        structure = _make_structure(winner, loser)

        result = ResolveInferenceConflict("c1", "step-a").apply(structure)

        assert result.get("step-a").structure.get("superseded_by") is None
        assert result.get("step-b").structure.get("superseded_by") == "step-a"

    def test_supersedes_multiple_losers(self) -> None:
        winner = _make_inference_step("step-a", confidence=0.9)
        loser_1 = _make_inference_step("step-b", confidence=0.4)
        loser_2 = _make_inference_step("step-c", confidence=0.3)
        structure = _make_structure(winner, loser_1, loser_2)

        result = ResolveInferenceConflict("c1", "step-a").apply(structure)

        assert result.get("step-b").structure.get("superseded_by") == "step-a"
        assert result.get("step-c").structure.get("superseded_by") == "step-a"

    def test_ignores_steps_concluding_something_else(self) -> None:
        winner = _make_inference_step("step-a", conclusion="c1", confidence=0.9)
        unrelated = _make_inference_step("step-x", conclusion="other", confidence=0.9)
        structure = KnowledgeStructure(
            [
                _make_obj("c1", name="Conclusion"),
                _make_obj("other", name="Other conclusion"),
                winner,
                unrelated,
            ]
        )

        result = ResolveInferenceConflict("c1", "step-a").apply(structure)

        assert result.get("step-x").structure.get("superseded_by") is None

    def test_leaves_already_superseded_steps_untouched(self) -> None:
        winner = _make_inference_step("step-a", confidence=0.9)
        already_retired = _make_inference_step(
            "step-b", confidence=0.2, superseded_by="step-z"
        )
        structure = _make_structure(winner, already_retired)

        result = ResolveInferenceConflict("c1", "step-a").apply(structure)

        # Untouched -- still points at its original supersessor, not
        # rewritten to the new winner.
        assert result.get("step-b").structure.get("superseded_by") == "step-z"

    def test_ignores_non_inference_step_objects(self) -> None:
        winner = _make_inference_step("step-a", confidence=0.9)
        plain = _make_obj("plain-1", otype="Note")
        structure = _make_structure(winner, plain)

        result = ResolveInferenceConflict("c1", "step-a").apply(structure)

        assert result.get("plain-1").structure == {}

    def test_noop_when_winner_is_the_only_active_step(self) -> None:
        winner = _make_inference_step("step-a", confidence=0.9)
        structure = _make_structure(winner)

        result = ResolveInferenceConflict("c1", "step-a").apply(structure)

        assert result.get("step-a").structure.get("superseded_by") is None

    def test_rejects_missing_winner(self) -> None:
        structure = _make_structure(_make_inference_step("step-b", confidence=0.4))
        with pytest.raises(ValueError, match="does not exist"):
            ResolveInferenceConflict("c1", "step-a").apply(structure)

    def test_rejects_winner_that_is_not_an_inference_step(self) -> None:
        not_a_step = _make_obj("step-a", otype="Claim")
        structure = _make_structure(not_a_step)
        with pytest.raises(ValueError, match="not an InferenceStep"):
            ResolveInferenceConflict("c1", "step-a").apply(structure)

    def test_rejects_winner_concluding_something_else(self) -> None:
        winner = _make_inference_step("step-a", conclusion="other", confidence=0.9)
        structure = KnowledgeStructure(
            [
                _make_obj("c1", name="Conclusion"),
                _make_obj("other", name="Other conclusion"),
                winner,
            ]
        )
        with pytest.raises(ValueError, match="does not conclude"):
            ResolveInferenceConflict("c1", "step-a").apply(structure)

    def test_rejects_already_superseded_winner(self) -> None:
        winner = _make_inference_step(
            "step-a", confidence=0.9, superseded_by="step-z"
        )
        structure = _make_structure(winner)
        with pytest.raises(ValueError, match="already superseded"):
            ResolveInferenceConflict("c1", "step-a").apply(structure)

    def test_returns_new_structure_instance(self) -> None:
        winner = _make_inference_step("step-a", confidence=0.9)
        loser = _make_inference_step("step-b", confidence=0.4)
        structure = _make_structure(winner, loser)

        result = ResolveInferenceConflict("c1", "step-a").apply(structure)

        assert result is not structure
        assert loser.structure.get("superseded_by") is None  # original untouched

    def test_callable_shorthand_matches_apply(self) -> None:
        winner = _make_inference_step("step-a", confidence=0.9)
        loser = _make_inference_step("step-b", confidence=0.4)
        structure = _make_structure(winner, loser)

        result = ResolveInferenceConflict("c1", "step-a")(structure)

        assert result.get("step-b").structure.get("superseded_by") == "step-a"

    def test_contract_reports_conclusion_and_winner(self) -> None:
        contract = ResolveInferenceConflict("c1", "step-a").contract()
        assert "c1" in contract.description
        assert "step-a" in contract.description

    def test_composes_with_other_operators(self) -> None:
        from cks.evolution import AddObject

        winner = _make_inference_step("step-a", confidence=0.9)
        loser = _make_inference_step("step-b", confidence=0.4)
        base = _make_structure(winner, loser)

        result = compose(
            base,
            [
                AddObject(_make_obj("note-1", otype="Note")),
                ResolveInferenceConflict("c1", "step-a"),
            ],
        )

        assert result.get("step-b").structure.get("superseded_by") == "step-a"
        assert result.get("note-1") is not None


# ===========================================================================
# parse_operations wire format
# ===========================================================================


class TestParseResolveInferenceConflict:
    def test_parses_valid_operation(self) -> None:
        ops = parse_operations(
            [
                {
                    "type": "resolve_inference_conflict",
                    "conclusion_id": "c1",
                    "winner_id": "step-a",
                }
            ]
        )
        assert len(ops) == 1
        assert isinstance(ops[0], ResolveInferenceConflict)
        assert ops[0].conclusion_id == "c1"
        assert ops[0].winner_id == "step-a"

    def test_missing_conclusion_id_raises(self) -> None:
        with pytest.raises(ValueError, match="conclusion_id"):
            parse_operations(
                [{"type": "resolve_inference_conflict", "winner_id": "step-a"}]
            )

    def test_missing_winner_id_raises(self) -> None:
        with pytest.raises(ValueError, match="winner_id"):
            parse_operations(
                [{"type": "resolve_inference_conflict", "conclusion_id": "c1"}]
            )

    def test_invalid_fields_propagate_operation_index(self) -> None:
        with pytest.raises(ValueError, match=r"Operation #0"):
            parse_operations(
                [
                    {
                        "type": "resolve_inference_conflict",
                        "conclusion_id": "same",
                        "winner_id": "same",
                    }
                ]
            )