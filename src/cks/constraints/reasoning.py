"""
CKS Extension Constraints — Reasoning Objects.

Status: EXTENSION, not part of the normative CKS-001..CKS-008 core
specifications. Not registered by default (see OPTIONAL_CONSTRAINTS in
`builtin.py`); callers must opt in explicitly.

Rationale
---------
See ADR-001 ("Reasoning Objects") in `docs/adr/`. An inference step —
the record of *why* an object or relation was asserted, as opposed to
`verify_source`'s record of *where a fact came from* — is represented
as an ordinary Knowledge Object declared inside the graph, exactly the
same way `contradiction.py` represents `MutualExclusionRule` and
`FunctionalRelationRule`: reserved vocabulary, not external
configuration.

An ``InferenceStep`` is a KnowledgeObject whose ``identity.type ==
INFERENCE_STEP_TYPE``, with ``structure``:

    {
        "premises": [<object_id>, ...],
        "conclusion": <object_id>,
        "operator": "deductive" | "inductive" | "abductive" | "heuristic",
        "confidence": 0.0,
        "justification": "<short free text>",
        "alternatives_considered": ["<short free text>", ...],
        "superseded_by": <object_id> | None,
    }

Not a CanonicalRelation: ``participants`` is a flat, arity-based list
with no role labels (`contradiction.py` already only reasons about
ordered 2-participant pairs for the same reason), so N premises + 1
conclusion + metadata would either lose the premise/conclusion
distinction or invent an unwritten positional convention. A typed
object with named structure fields keeps both first-class.

Three constraints are provided, each independently opt-in:

``InferenceReferentialIntegrityConstraint``
    Every id listed in an ``InferenceStep``'s ``premises``/
    ``conclusion`` must reference an object that exists in the
    structure -- the same referential-integrity concern
    `NoDanglingRelationConstraint` enforces for relation participants,
    scoped to this extension's vocabulary.

``ConfidenceBoundsConstraint``
    An ``InferenceStep``'s ``confidence`` field, when present, must be
    a real number in the closed interval [0, 1].

``SupersessionChainConstraint``
    If an ``InferenceStep`` names a successor via ``superseded_by``,
    that successor must itself be an ``InferenceStep`` targeting the
    same ``conclusion`` -- otherwise a revision chain could silently
    point at an unrelated or nonexistent object.

``InferenceConfidenceConflictConstraint``
    ADR-001 names this the natural next step for `detect_contradictions`:
    unlike `contradiction.py`, which flags two relations that are
    jointly nonsensical, this flags two *agreeing* `InferenceStep`s --
    same ``conclusion`` -- whose ``confidence`` values disagree. This
    is deliberately a WARNING, not an ERROR: two independent inference
    paths reaching the same conclusion with different confidence is a
    resolvable belief conflict to surface for review, not a structural
    invalidity like a dangling reference or an out-of-range confidence
    value. Only *active* steps are compared -- a step named by another
    step's ``superseded_by`` has already been explicitly revised, so it
    no longer represents a live, disagreeing belief and is excluded
    from the comparison (that relationship is `SupersessionChainConstraint`'s
    concern, not this one's).

A structure with no ``InferenceStep`` objects is entirely unaffected
by any of the four, matching every other extension's convention in
this package.
"""

from __future__ import annotations

from collections.abc import Iterator
from numbers import Real

from ..core import KnowledgeObject, KnowledgeStructure
from ..diagnostics import Diagnostic, DiagnosticSeverity
from ..validation import ValidationStage
from .base import Constraint

# Canonical vocabulary for this extension.
INFERENCE_STEP_TYPE = "InferenceStep"

# Structural content keys.
_PREMISES_KEY = "premises"
_CONCLUSION_KEY = "conclusion"
_CONFIDENCE_KEY = "confidence"
_SUPERSEDED_BY_KEY = "superseded_by"


def _error(*, identity: str, message: str, location: str | None = None) -> Diagnostic:
    return Diagnostic(
        identity=identity,
        severity=DiagnosticSeverity.ERROR,
        message=message,
        location=location,
    )


def _inference_steps(structure: KnowledgeStructure) -> Iterator[KnowledgeObject]:
    return (
        obj for obj in structure.objects if obj.identity.type == INFERENCE_STEP_TYPE
    )


class InferenceReferentialIntegrityConstraint(Constraint):
    """Every premise/conclusion id an InferenceStep references shall
    exist in the structure."""

    identity = "CKS-EXT-INFERENCE-REFERENTIAL-INTEGRITY"
    stage = ValidationStage.SEMANTIC
    description = (
        "An InferenceStep's premises and conclusion must reference "
        "objects that exist in the structure."
    )

    def evaluate(self, structure: KnowledgeStructure) -> list[Diagnostic]:
        diagnostics: list[Diagnostic] = []

        for step in _inference_steps(structure):
            premises = step.structure.get(_PREMISES_KEY) or ()
            conclusion = step.structure.get(_CONCLUSION_KEY)

            for premise_id in premises:
                if structure.get(premise_id) is None:
                    diagnostics.append(
                        _error(
                            identity=self.identity,
                            message=(
                                f"InferenceStep '{step.identity.id}' "
                                f"references unknown premise "
                                f"'{premise_id}'."
                            ),
                            location=step.identity.id,
                        )
                    )

            if conclusion is not None and structure.get(conclusion) is None:
                diagnostics.append(
                    _error(
                        identity=self.identity,
                        message=(
                            f"InferenceStep '{step.identity.id}' "
                            f"references unknown conclusion "
                            f"'{conclusion}'."
                        ),
                        location=step.identity.id,
                    )
                )

        return diagnostics


class ConfidenceBoundsConstraint(Constraint):
    """An InferenceStep's confidence, when present, shall be a real
    number in [0, 1]."""

    identity = "CKS-EXT-CONFIDENCE-BOUNDS"
    stage = ValidationStage.SEMANTIC
    description = "An InferenceStep's confidence must lie within [0, 1]."

    def evaluate(self, structure: KnowledgeStructure) -> list[Diagnostic]:
        diagnostics: list[Diagnostic] = []

        for step in _inference_steps(structure):
            if _CONFIDENCE_KEY not in step.structure:
                continue
            confidence = step.structure.get(_CONFIDENCE_KEY)

            if isinstance(confidence, bool) or not isinstance(confidence, Real):
                diagnostics.append(
                    _error(
                        identity=self.identity,
                        message=(
                            f"InferenceStep '{step.identity.id}' has a "
                            f"non-numeric confidence value "
                            f"({confidence!r})."
                        ),
                        location=step.identity.id,
                    )
                )
            elif not (0.0 <= float(confidence) <= 1.0):
                diagnostics.append(
                    _error(
                        identity=self.identity,
                        message=(
                            f"InferenceStep '{step.identity.id}' has "
                            f"confidence {confidence!r}, outside [0, 1]."
                        ),
                        location=step.identity.id,
                    )
                )

        return diagnostics


class SupersessionChainConstraint(Constraint):
    """An InferenceStep's superseded_by, when present, shall name
    another InferenceStep targeting the same conclusion."""

    identity = "CKS-EXT-SUPERSESSION-CHAIN"
    stage = ValidationStage.SEMANTIC
    description = (
        "An InferenceStep's superseded_by must name an InferenceStep "
        "that targets the same conclusion."
    )

    def evaluate(self, structure: KnowledgeStructure) -> list[Diagnostic]:
        diagnostics: list[Diagnostic] = []

        for step in _inference_steps(structure):
            successor_id = step.structure.get(_SUPERSEDED_BY_KEY)
            if not successor_id:
                continue

            successor = structure.get(successor_id)
            conclusion = step.structure.get(_CONCLUSION_KEY)

            if successor is None:
                diagnostics.append(
                    _error(
                        identity=self.identity,
                        message=(
                            f"InferenceStep '{step.identity.id}' is "
                            f"superseded_by unknown object "
                            f"'{successor_id}'."
                        ),
                        location=step.identity.id,
                    )
                )
            elif successor.identity.type != INFERENCE_STEP_TYPE:
                diagnostics.append(
                    _error(
                        identity=self.identity,
                        message=(
                            f"InferenceStep '{step.identity.id}' is "
                            f"superseded_by '{successor_id}', which is "
                            f"not an InferenceStep."
                        ),
                        location=step.identity.id,
                    )
                )
            elif successor.structure.get(_CONCLUSION_KEY) != conclusion:
                diagnostics.append(
                    _error(
                        identity=self.identity,
                        message=(
                            f"InferenceStep '{step.identity.id}' is "
                            f"superseded_by '{successor_id}', which "
                            f"targets a different conclusion."
                        ),
                        location=step.identity.id,
                    )
                )

        return diagnostics


class InferenceConfidenceConflictConstraint(Constraint):
    """Two or more *active* (non-superseded) InferenceSteps that share
    a ``conclusion`` shall not carry disagreeing ``confidence`` values.

    A WARNING, not an ERROR (see module docstring): this is a
    resolvable belief conflict between agreeing inference paths, not a
    structural invalidity.
    """

    identity = "CKS-EXT-INFERENCE-CONFIDENCE-CONFLICT"
    stage = ValidationStage.SEMANTIC
    description = (
        "Active InferenceSteps sharing a conclusion must not carry "
        "disagreeing confidence values."
    )

    def evaluate(self, structure: KnowledgeStructure) -> list[Diagnostic]:
        # conclusion_id -> confidence_value -> [step_id, ...]
        by_conclusion: dict[str, dict[float, list[str]]] = {}

        for step in _inference_steps(structure):
            # A step already named by another step's superseded_by has
            # been explicitly revised -- it no longer represents a
            # live belief, so it is excluded from this comparison.
            if step.structure.get(_SUPERSEDED_BY_KEY):
                continue

            conclusion = step.structure.get(_CONCLUSION_KEY)
            if conclusion is None:
                continue

            confidence = step.structure.get(_CONFIDENCE_KEY)
            # Non-numeric/out-of-range confidence is
            # ConfidenceBoundsConstraint's concern, not this one's --
            # only compare values that are themselves valid.
            if isinstance(confidence, bool) or not isinstance(confidence, Real):
                continue
            if not (0.0 <= float(confidence) <= 1.0):
                continue

            by_conclusion.setdefault(conclusion, {}).setdefault(
                float(confidence), []
            ).append(step.identity.id)

        diagnostics: list[Diagnostic] = []
        for conclusion in sorted(by_conclusion):
            values = by_conclusion[conclusion]
            if len(values) <= 1:
                continue  # every active step agrees on confidence

            all_step_ids = sorted(
                step_id for ids in values.values() for step_id in ids
            )
            breakdown = ", ".join(
                f"{value!r}: {sorted(ids)}" for value, ids in sorted(values.items())
            )
            diagnostics.append(
                Diagnostic(
                    identity=self.identity,
                    severity=DiagnosticSeverity.WARNING,
                    message=(
                        f"{len(all_step_ids)} active InferenceStep(s) reach "
                        f"conclusion '{conclusion}' with disagreeing "
                        f"confidence values ({breakdown}). This is a "
                        f"resolvable belief conflict, not a structural "
                        f"error -- consider a RecordInference with "
                        f"'superseded_by' to reconcile it."
                    ),
                    location=all_step_ids[0],
                )
            )
        return diagnostics


__all__ = [
    "INFERENCE_STEP_TYPE",
    "ConfidenceBoundsConstraint",
    "InferenceConfidenceConflictConstraint",
    "InferenceReferentialIntegrityConstraint",
    "SupersessionChainConstraint",
]