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

See ADR-002 ("Belief Revision Support") for the two extensions below,
built on top of ADR-001's vocabulary without changing any of the four
constraints above:

``StalePremiseConstraint``
    Flags an *active* `InferenceStep` whose ``premises`` directly cite
    the id of another `InferenceStep` that has itself already been
    superseded -- a meta-reasoning citation left pointing at an
    outdated derivation. A WARNING, matching
    `InferenceConfidenceConflictConstraint`'s tier: the cited step
    still exists and is still well-formed, so this is epistemically
    suspect, not structurally invalid. (Checking whether a premise
    shares a *conclusion*, rather than an id, with a superseded step
    turns out to be unreachable on valid data --
    `SupersessionChainConstraint` already guarantees every conclusion
    keeps at least one live supporting step, so there is nothing
    resembling a "fully retracted conclusion" to detect that way.)

``SupersessionChainConstraint`` cycle detection
    In addition to its three existing pairwise checks,
    `SupersessionChainConstraint` now also rejects a ``superseded_by``
    cycle (e.g. ``A.superseded_by == B``, ``B.superseded_by == A``),
    which no individual pairwise check catches on its own. This stays
    at the constraint's existing ERROR severity -- a cycle is a
    structural defect (no step in it ever resolves to a live belief),
    not a resolvable disagreement.

``rank_by_entrenchment``
    A pure query function, not a `Constraint` -- it produces no
    `Diagnostic` and never mutates the structure. Ranks the active
    `InferenceStep`s sharing a conclusion by confidence, for a caller
    (e.g. `cks-mcp`'s `explain_knowledge`/`suggest_evolution`)
    resolving an `InferenceConfidenceConflictConstraint` WARNING to
    hand an agent a concrete starting point instead of re-deriving a
    ranking from raw ``confidence`` values inline each time. Ranking
    is not a decision: nothing here writes ``superseded_by``.

A structure with no ``InferenceStep`` objects is entirely unaffected
by any of the above, matching every other extension's convention in
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


def _find_supersession_cycle(
    structure: KnowledgeStructure, start: KnowledgeObject
) -> list[str] | None:
    """Walk ``start``'s ``superseded_by`` chain forward. Returns the
    ids forming a cycle, in order, if ``start`` is reachable from
    itself; otherwise ``None``.

    Bounded by the number of InferenceStep objects in the structure,
    so a dangling or wrong-type ``superseded_by`` -- already flagged
    by this constraint's own pairwise checks -- simply stops the walk
    (returns ``None``) rather than raising or looping unboundedly.
    Only reports a cycle that ``start`` itself is part of; a step that
    merely chains *into* a cycle without returning to itself is left
    to be caught when the cycle's own members are visited.
    """
    max_hops = sum(1 for _ in _inference_steps(structure)) + 1
    path = [start.identity.id]
    current = start

    for _ in range(max_hops):
        successor_id = current.structure.get(_SUPERSEDED_BY_KEY)
        if not successor_id:
            return None
        if successor_id == start.identity.id:
            return [*path, successor_id]

        successor = structure.get(successor_id)
        if successor is None or successor.identity.type != INFERENCE_STEP_TYPE:
            return None
        if successor.identity.id in path:
            # Walks into a cycle that doesn't include `start` -- that
            # cycle is reported when one of its own members is visited
            # as `start` by the caller's loop, not from here.
            return None

        path.append(successor.identity.id)
        current = successor

    return None


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

        diagnostics.extend(self._detect_cycles(structure))
        return diagnostics

    def _detect_cycles(self, structure: KnowledgeStructure) -> list[Diagnostic]:
        """One ERROR per distinct superseded_by cycle (ADR-002), each
        reported once regardless of which member of the cycle is
        iterated to first."""
        diagnostics: list[Diagnostic] = []
        reported: set[str] = set()

        for step in _inference_steps(structure):
            if step.identity.id in reported:
                continue
            cycle = _find_supersession_cycle(structure, step)
            if cycle is None:
                continue
            reported.update(cycle)
            diagnostics.append(
                _error(
                    identity=self.identity,
                    message=(
                        "Supersession cycle detected: "
                        f"{' -> '.join(cycle)}."
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


class StalePremiseConstraint(Constraint):
    """An active InferenceStep's premises shall not directly cite
    another InferenceStep that has itself already been superseded.

    A WARNING, not an ERROR: the cited step still exists and is still
    a well-formed InferenceStep -- it has simply been revised since,
    so a step still listing it as a premise is citing an outdated
    piece of reasoning and is worth a second look, not a structural
    invalidity.

    Note this checks a premise that is itself an InferenceStep id
    (meta-reasoning: citing a specific derivation as support for a
    further one), not a premise that merely shares a *conclusion*
    with a superseded step. The latter can't actually happen on valid
    data: ``SupersessionChainConstraint`` already requires a
    successor to target the same conclusion, so any conclusion with
    at least one InferenceStep always keeps at least one live
    (non-superseded) step supporting it -- the chain has to terminate
    somewhere, and cycles/dangling successors are already ERRORs of
    their own. What *can* go stale on otherwise-valid data is a direct
    citation of a step's own id, which is exactly what this checks.
    """

    identity = "CKS-EXT-STALE-PREMISE"
    stage = ValidationStage.SEMANTIC
    description = (
        "An active InferenceStep's premises must not directly cite "
        "another InferenceStep that has itself already been "
        "superseded."
    )

    def evaluate(self, structure: KnowledgeStructure) -> list[Diagnostic]:
        diagnostics: list[Diagnostic] = []

        for step in _inference_steps(structure):
            # A superseded step's own staleness is
            # SupersessionChainConstraint's concern, not this one's --
            # only active steps still depend on their premises going
            # forward.
            if step.structure.get(_SUPERSEDED_BY_KEY):
                continue

            premises = step.structure.get(_PREMISES_KEY) or ()
            for premise_id in premises:
                premise_obj = structure.get(premise_id)
                if premise_obj is None or premise_obj.identity.type != INFERENCE_STEP_TYPE:
                    continue  # not an InferenceStep citation -- out of scope

                successor_id = premise_obj.structure.get(_SUPERSEDED_BY_KEY)
                if not successor_id:
                    continue  # cited step is still active

                diagnostics.append(
                    Diagnostic(
                        identity=self.identity,
                        severity=DiagnosticSeverity.WARNING,
                        message=(
                            f"InferenceStep '{step.identity.id}' cites "
                            f"'{premise_id}' as a premise, but "
                            f"'{premise_id}' has itself been "
                            f"superseded_by '{successor_id}' -- "
                            f"consider citing the current step instead."
                        ),
                        location=step.identity.id,
                    )
                )

        return diagnostics


def rank_by_entrenchment(
    structure: KnowledgeStructure, conclusion_id: str
) -> list[KnowledgeObject]:
    """Active (non-superseded) InferenceSteps concluding
    ``conclusion_id``, ordered highest-entrenchment first: confidence
    descending, then declared structure order as a stable tiebreak.

    A pure query, not a Constraint (see ADR-002) -- produces no
    Diagnostic and never mutates the structure. Exists so a caller
    resolving an ``InferenceConfidenceConflictConstraint`` WARNING has
    a concrete starting point instead of re-deriving a ranking from
    raw ``confidence`` values inline each time. Ranking is not a
    decision: callers still choose which step, if any, to supersede
    the others with -- nothing here writes ``superseded_by``.

    Steps with a missing, non-numeric, or out-of-range ``confidence``
    (``ConfidenceBoundsConstraint``'s concern) sort last, in structure
    order among themselves, rather than being dropped -- silently
    excluding them could otherwise hide a live belief from the
    ranking entirely. Returns ``[]`` if fewer than one active step
    concludes ``conclusion_id``.
    """

    def _valid_confidence(step: KnowledgeObject) -> float | None:
        confidence = step.structure.get(_CONFIDENCE_KEY)
        if isinstance(confidence, bool) or not isinstance(confidence, Real):
            return None
        value = float(confidence)
        return value if 0.0 <= value <= 1.0 else None

    def _sort_key(step: KnowledgeObject) -> tuple[int, float]:
        confidence = _valid_confidence(step)
        if confidence is None:
            return (1, 0.0)
        return (0, -confidence)

    active = [
        step
        for step in _inference_steps(structure)
        if step.structure.get(_CONCLUSION_KEY) == conclusion_id
        and not step.structure.get(_SUPERSEDED_BY_KEY)
    ]
    return sorted(active, key=_sort_key)


__all__ = [
    "INFERENCE_STEP_TYPE",
    "ConfidenceBoundsConstraint",
    "InferenceConfidenceConflictConstraint",
    "InferenceReferentialIntegrityConstraint",
    "StalePremiseConstraint",
    "SupersessionChainConstraint",
    "rank_by_entrenchment",
]