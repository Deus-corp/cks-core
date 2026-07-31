"""
Unit tests for the RecordInference operator and its parse_operations
wire format ("record_inference"). See ADR-001 ("Reasoning Objects").
"""

from __future__ import annotations

import pytest

from cks.constraints.reasoning import INFERENCE_STEP_TYPE
from cks.core import KnowledgeObject, KnowledgeStructure, ObjectIdentity
from cks.evolution import (
    AddObject,
    RecordInference,
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
    premises: list[str] | None = None,
    conclusion: str = "c1",
    confidence: float = 0.5,
    name: str = "",
) -> KnowledgeObject:
    return KnowledgeObject(
        identity=ObjectIdentity(id=oid, type=INFERENCE_STEP_TYPE, name=name or oid),
        structure={
            "premises": premises or [],
            "conclusion": conclusion,
            "confidence": confidence,
        },
    )


def _make_structure() -> KnowledgeStructure:
    return KnowledgeStructure(
        [
            _make_obj("p1", name="Premise One"),
            _make_obj("p2", name="Premise Two"),
            _make_obj("c1", name="Conclusion"),
        ]
    )


# ===========================================================================
# Construction — validation at __init__ time
# ===========================================================================


class TestRecordInferenceConstruction:
    def test_obj_property(self):
        step = _make_inference_step("step-1")
        op = RecordInference(step)
        assert op.obj is step

    def test_rejects_wrong_identity_type(self):
        obj = KnowledgeObject(
            identity=ObjectIdentity(id="step-1", type="Claim", name="step-1"),
            structure={"conclusion": "c1"},
        )
        with pytest.raises(ValueError, match=INFERENCE_STEP_TYPE):
            RecordInference(obj)

    def test_rejects_missing_conclusion(self):
        obj = KnowledgeObject(
            identity=ObjectIdentity(
                id="step-1", type=INFERENCE_STEP_TYPE, name="step-1"
            ),
            structure={"premises": ["p1"]},
        )
        with pytest.raises(ValueError, match="conclusion"):
            RecordInference(obj)

    def test_rejects_empty_conclusion(self):
        obj = KnowledgeObject(
            identity=ObjectIdentity(
                id="step-1", type=INFERENCE_STEP_TYPE, name="step-1"
            ),
            structure={"conclusion": ""},
        )
        with pytest.raises(ValueError, match="conclusion"):
            RecordInference(obj)


# ===========================================================================
# RecordInference — apply-time behaviour
# ===========================================================================


class TestRecordInferenceApply:
    def test_records_step_with_existing_premises_and_conclusion(self):
        structure = _make_structure()
        step = _make_inference_step("step-1", premises=["p1", "p2"], conclusion="c1")
        result = RecordInference(step).apply(structure)

        recorded = result.get("step-1")
        assert recorded is not None
        assert recorded.structure["premises"] == ("p1", "p2")
        assert recorded.structure["conclusion"] == "c1"

    def test_rejects_unknown_premise_at_apply_time(self):
        structure = _make_structure()
        step = _make_inference_step("step-1", premises=["ghost"], conclusion="c1")
        with pytest.raises(ValueError, match="Premise 'ghost' does not exist"):
            RecordInference(step).apply(structure)

    def test_rejects_unknown_conclusion_at_apply_time(self):
        structure = _make_structure()
        step = _make_inference_step("step-1", premises=["p1"], conclusion="ghost")
        with pytest.raises(ValueError, match="Conclusion 'ghost' does not exist"):
            RecordInference(step).apply(structure)

    def test_rejects_duplicate_identity(self):
        structure = _make_structure()
        step = _make_inference_step("p1", conclusion="c1")  # collides with "p1"
        with pytest.raises(ValueError, match="already exists"):
            RecordInference(step).apply(structure)

    def test_total_object_count_increases_by_one(self):
        structure = _make_structure()
        step = _make_inference_step("step-1", premises=["p1"], conclusion="c1")
        result = RecordInference(step).apply(structure)
        assert len(result.objects) == len(structure.objects) + 1

    def test_is_callable(self):
        structure = _make_structure()
        step = _make_inference_step("step-1", premises=["p1"], conclusion="c1")
        result = RecordInference(step)(structure)
        assert result.get("step-1") is not None

    def test_contract_mentions_object_id(self):
        step = _make_inference_step("step-1", conclusion="c1")
        c = RecordInference(step).contract()
        assert "step-1" in c.description
        assert len(c.preconditions) == 2

    # -----------------------------------------------------------------
    # compose integration
    # -----------------------------------------------------------------

    def test_record_inference_can_reference_a_premise_added_in_the_same_batch(self):
        structure = _make_structure()
        new_premise = _make_obj("p3", name="Premise Three")
        step = _make_inference_step("step-1", premises=["p1", "p3"], conclusion="c1")
        ops = [AddObject(new_premise), RecordInference(step)]
        result = compose(structure, ops)
        assert result.get("p3") is not None
        assert result.get("step-1") is not None

    def test_record_inference_in_compose_batch_with_another_inference_step(self):
        structure = _make_structure()
        step_1 = _make_inference_step("step-1", premises=["p1"], conclusion="c1")
        step_2 = _make_inference_step(
            "step-2", premises=["step-1"], conclusion="c1", confidence=0.9
        )
        result = compose(structure, [RecordInference(step_1), RecordInference(step_2)])
        assert result.get("step-1") is not None
        # step-2 uses step-1 itself as a premise -- any existing object id
        # is a valid premise, InferenceStep included.
        assert result.get("step-2").structure["premises"] == ("step-1",)


# ===========================================================================
# parse_operations — record_inference wire format
# ===========================================================================


class TestParseRecordInference:
    def test_parse_record_inference(self):
        ops = parse_operations(
            [
                {
                    "type": "record_inference",
                    "identity": {
                        "id": "step-1",
                        "type": INFERENCE_STEP_TYPE,
                        "name": "step-1",
                    },
                    "structure": {
                        "premises": ["p1", "p2"],
                        "conclusion": "c1",
                        "confidence": 0.8,
                    },
                }
            ]
        )
        assert len(ops) == 1
        assert isinstance(ops[0], RecordInference)
        assert ops[0].obj.structure["conclusion"] == "c1"

    def test_parse_missing_identity_raises(self):
        with pytest.raises(ValueError, match="missing 'identity'"):
            parse_operations(
                [{"type": "record_inference", "structure": {"conclusion": "c1"}}]
            )

    def test_parse_wrong_identity_type_raises(self):
        with pytest.raises(ValueError, match=INFERENCE_STEP_TYPE):
            parse_operations(
                [
                    {
                        "type": "record_inference",
                        "identity": {"id": "step-1", "type": "Claim", "name": "x"},
                        "structure": {"conclusion": "c1"},
                    }
                ]
            )

    def test_parse_missing_conclusion_raises(self):
        with pytest.raises(ValueError, match="conclusion"):
            parse_operations(
                [
                    {
                        "type": "record_inference",
                        "identity": {
                            "id": "step-1",
                            "type": INFERENCE_STEP_TYPE,
                            "name": "x",
                        },
                        "structure": {"premises": ["p1"]},
                    }
                ]
            )

    def test_parse_record_inference_then_apply(self):
        structure = _make_structure()
        ops = parse_operations(
            [
                {
                    "type": "record_inference",
                    "identity": {
                        "id": "step-1",
                        "type": INFERENCE_STEP_TYPE,
                        "name": "step-1",
                    },
                    "structure": {"premises": ["p1", "p2"], "conclusion": "c1"},
                }
            ]
        )
        result = compose(structure, ops)
        assert result.get("step-1") is not None

    def test_parse_mixed_operations_including_record_inference(self):
        structure = _make_structure()
        ops = parse_operations(
            [
                {
                    "type": "add_object",
                    "identity": {"id": "p3", "type": "Claim", "name": "Premise Three"},
                    "structure": {},
                },
                {
                    "type": "record_inference",
                    "identity": {
                        "id": "step-1",
                        "type": INFERENCE_STEP_TYPE,
                        "name": "step-1",
                    },
                    "structure": {"premises": ["p1", "p3"], "conclusion": "c1"},
                },
            ]
        )
        result = compose(structure, ops)
        assert result.get("p3") is not None
        assert result.get("step-1") is not None
