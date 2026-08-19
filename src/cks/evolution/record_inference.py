"""
Reasoning — Inference Recording (ADR-001).
"""

from __future__ import annotations

from ..core import KnowledgeObject
from .base import OperatorContract, StructuralOperator


class RecordInference(StructuralOperator):
    """
    Record an InferenceStep: the reified account of an inference an
    agent already performed (premises, conclusion, confidence,
    justification -- see ADR-001, "Reasoning Objects").

    An InferenceStep is an ordinary KnowledgeObject whose
    ``identity.type`` is ``cks.constraints.reasoning.INFERENCE_STEP_TYPE``
    -- adding it is mechanically identical to ``AddObject``. This
    operator exists alongside ``AddObject`` only to give the
    premises/conclusion existence check the same *eager*, apply-time
    treatment ``AddRelation`` already gives its participants, rather
    than deferring the check entirely to the opt-in
    ``cks.constraints.reasoning`` extension at validation time.
    """

    def __init__(self, obj: KnowledgeObject) -> None:
        # Imported lazily to avoid cks.evolution depending on the
        # cks.constraints package at module-import time -- evolution's
        # operator modules otherwise only ever import from ..core.
        from ..constraints.reasoning import INFERENCE_STEP_TYPE

        if obj.identity.type != INFERENCE_STEP_TYPE:
            raise ValueError(
                f"RecordInference requires identity.type == "
                f"'{INFERENCE_STEP_TYPE}', got '{obj.identity.type}'."
            )
        if "conclusion" not in obj.structure or not obj.structure["conclusion"]:
            raise ValueError("InferenceStep requires a non-empty 'conclusion' field.")
        self._obj = obj

    @property
    def obj(self) -> KnowledgeObject:
        """The InferenceStep KnowledgeObject to be recorded."""
        return self._obj

    def _mutate(self, objects: dict[str, KnowledgeObject]) -> None:
        if self._obj.identity.id in objects:
            raise ValueError(f"Object '{self._obj.identity.id}' already exists.")
        for premise_id in self._obj.structure.get("premises") or ():
            if premise_id not in objects:
                raise ValueError(f"Premise '{premise_id}' does not exist.")
        conclusion_id = self._obj.structure["conclusion"]
        if conclusion_id not in objects:
            raise ValueError(f"Conclusion '{conclusion_id}' does not exist.")
        objects[self._obj.identity.id] = self._obj

    def contract(self) -> OperatorContract:
        return OperatorContract(
            description=f"Record InferenceStep '{self._obj.identity.id}'.",
            preconditions=(
                "Every id in 'premises' must already exist in the structure.",
                "The 'conclusion' id must already exist in the structure.",
            ),
            postconditions=("The InferenceStep object is present in the structure.",),
            invariant_obligations=(
                "Referential integrity of premises/conclusion is preserved.",
            ),
        )
