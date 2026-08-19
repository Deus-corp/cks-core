"""
Reasoning — Inference Conflict Resolution (ADR-001).
"""

from __future__ import annotations

from ..core import KnowledgeObject
from .base import OperatorContract, StructuralOperator


class ResolveInferenceConflict(StructuralOperator):
    """
    Resolve an InferenceConfidenceConflict (see
    ``cks.constraints.reasoning.InferenceConfidenceConflictConstraint``):
    supersede every other *active* InferenceStep concluding
    ``conclusion_id`` in favor of ``winner_id``.

    This is the write-side counterpart to
    ``cks.constraints.reasoning.rank_by_entrenchment``/``explain_inference``,
    which only rank and report a conflict -- neither writes
    ``superseded_by``. An arbiter (human or agent) that has already
    decided which InferenceStep should stand uses this operator to
    record that decision as a single atomic evolution, rather than
    hand-rolling one ``UpdateObject`` per losing step and risking
    missing one, mis-targeting the wrong conclusion, or superseding an
    already-retired step into a cycle.

    ``winner_id`` must itself already be an *active* InferenceStep
    concluding ``conclusion_id`` -- resolving a conflict in favor of a
    step that is itself superseded, or that concludes something else,
    would silently misrepresent the arbiter's decision, so both are
    checked eagerly (apply-time), the same treatment ``RecordInference``
    already gives premises/conclusion existence. Every *other* active
    InferenceStep found concluding ``conclusion_id`` is given
    ``superseded_by = winner_id``; a step already superseded (by an
    earlier, unrelated decision) is left untouched -- it no longer
    represents a live belief and is not part of the conflict being
    resolved here (same exclusion ``InferenceConfidenceConflictConstraint``
    itself applies when detecting the conflict in the first place).

    A no-op (zero objects changed) if ``winner_id`` is the only active
    step concluding ``conclusion_id`` -- there is no conflict left to
    resolve, which is a legitimate outcome if it was already resolved
    by an earlier call, not an error condition.

    Cannot itself introduce a ``superseded_by`` cycle
    (``SupersessionChainConstraint``): every edge this operator creates
    points at ``winner_id``, and ``winner_id`` is checked not to be
    superseded by anything at apply time -- so no chain this operator
    writes can loop back on itself within the same call. A *later*
    call targeting the same conclusion always names a still-active
    step as its own new winner, for the same reason, so a cycle can
    only arise across calls if a caller bypasses this operator entirely
    and hand-edits ``superseded_by`` back onto an already-superseded
    step via ``UpdateObject``.
    """

    def __init__(self, conclusion_id: str, winner_id: str) -> None:
        if not conclusion_id or not str(conclusion_id).strip():
            raise ValueError("conclusion_id must be a non-empty string.")
        if not winner_id or not str(winner_id).strip():
            raise ValueError("winner_id must be a non-empty string.")
        if conclusion_id == winner_id:
            raise ValueError("conclusion_id and winner_id must differ.")
        self._conclusion_id = conclusion_id
        self._winner_id = winner_id

    @property
    def conclusion_id(self) -> str:
        """The conclusion whose competing InferenceSteps are being resolved."""
        return self._conclusion_id

    @property
    def winner_id(self) -> str:
        """The id of the InferenceStep the arbiter chose to keep active."""
        return self._winner_id

    def _mutate(self, objects: dict[str, KnowledgeObject]) -> None:
        # Imported lazily, matching RecordInference's own convention of
        # not making cks.evolution depend on cks.constraints at
        # module-import time.
        from ..constraints.reasoning import INFERENCE_STEP_TYPE

        winner = objects.get(self._winner_id)
        if winner is None:
            raise ValueError(f"winner_id '{self._winner_id}' does not exist.")
        if winner.identity.type != INFERENCE_STEP_TYPE:
            raise ValueError(
                f"winner_id '{self._winner_id}' is not an InferenceStep "
                f"(type={winner.identity.type!r})."
            )
        if winner.structure.get("conclusion") != self._conclusion_id:
            raise ValueError(
                f"winner_id '{self._winner_id}' does not conclude "
                f"'{self._conclusion_id}' (concludes "
                f"{winner.structure.get('conclusion')!r})."
            )
        if winner.structure.get("superseded_by"):
            raise ValueError(
                f"winner_id '{self._winner_id}' is already superseded "
                f"by '{winner.structure.get('superseded_by')}' -- cannot "
                f"resolve a conflict in favor of an already-retired step."
            )

        for obj_id, obj in list(objects.items()):
            if obj_id == self._winner_id:
                continue
            if obj.identity.type != INFERENCE_STEP_TYPE:
                continue
            if obj.structure.get("conclusion") != self._conclusion_id:
                continue
            if obj.structure.get("superseded_by"):
                continue  # already resolved by an earlier decision
            new_structure = dict(obj.structure)
            new_structure["superseded_by"] = self._winner_id
            objects[obj_id] = KnowledgeObject(
                identity=obj.identity,
                structure=new_structure,
            )

    def contract(self) -> OperatorContract:
        return OperatorContract(
            description=(
                f"Resolve InferenceConfidenceConflict at conclusion "
                f"'{self._conclusion_id}' in favor of '{self._winner_id}'."
            ),
            preconditions=(
                (
                    "winner_id must reference an existing, active "
                    "(non-superseded) InferenceStep whose conclusion "
                    "matches conclusion_id."
                ),
            ),
            postconditions=(
                (
                    "Every other InferenceStep that was active and "
                    "concluded conclusion_id now has superseded_by == "
                    "winner_id."
                ),
                "winner_id's own structure is unchanged.",
            ),
            invariant_obligations=(
                (
                    "SupersessionChainConstraint's per-edge invariant (a "
                    "superseded_by target is itself an InferenceStep "
                    "targeting the same conclusion) holds by construction "
                    "for every edge this operator creates."
                ),
            ),
        )
