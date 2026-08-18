"""
CKS Extension — Constraints-as-Data (pilot).

Status: EXTENSION, opt-in only (see ``ReferenceValidator.validate``'s
``include_structure_constraints`` parameter / ``validate(...,
include_structure_constraints=True)``). Never affects default
validation and never touches the global ``ConstraintRegistry``.

Rationale
---------
``ontology.py`` and ``contradiction.py`` already treat certain rules
(``TypeDefinition``/``TypeRule``, ``MutualExclusionRule``/
``FunctionalRelationRule``) as ordinary Knowledge Objects declared
inside the graph, read by a fixed, hand-written ``Constraint`` class.
That is "rules as data" for a handful of specific, pre-registered
constraint *shapes* -- but the set of shapes is still fixed at import
time by which ``Constraint`` subclasses exist in this package.

This module takes the next, deliberately small step: a graph may
declare an ``OntologyRule`` object that *selects* one of a handful of
existing constraint behaviours (``constraint_type``) and, where that
behaviour is parameterized, supplies the parameters -- without any new
Python code or process-wide registration. It is "constraints as data"
in the sense that *which* constraints run for a given structure can
now itself be discovered by reading the structure, rather than only
by what a caller passes to ``extra_constraints``.

This is explicitly a *pilot*: it selects among existing constraint
behaviours (see ``_BUILDERS`` below) rather than interpreting an
arbitrary rule language, and it complements -- does not replace --
the existing ``MutualExclusionRule``/``FunctionalRelationRule``
mechanism (see "Relationship to existing rule-object constraints"
below).

Object shape
------------
::

    {
      "identity": {
        "id": "rule-functional-orbit-v1",
        "type": "OntologyRule",
        "name": "Single-valued orbit relation"
      },
      "structure": {
        "constraint_type": "functional_relation",
        "target_relation_type": "orbit",
        "severity": "ERROR",
        "enabled": true,
        "parameters": {}
      }
    }

``constraint_type`` selects the underlying behaviour (see
``_BUILDERS``). ``target_relation_type`` is a convenience top-level
field for constraint types that need exactly one relation_type
(``functional_relation``); constraint types needing more than one
relation_type-shaped value (``mutual_exclusion``) read theirs from
``parameters`` instead, since a single ``target_relation_type`` field
can't hold a pair. ``enabled`` defaults to ``True`` -- only an explicit
``false`` disables a rule. ``severity`` is accepted but currently
informational only for pilot-supported types (each underlying
constraint already fixes its own diagnostic severity; a future
iteration could let a declared ``severity`` override it -- out of
scope for this pilot). Unknown ``constraint_type`` values are ignored
(see ``load_dynamic_constraints`` docstring for why silently, not
diagnostically).

Relationship to existing rule-object constraints
-------------------------------------------------
For ``mutual_exclusion``/``functional_relation``, this module
translates each valid ``OntologyRule`` into the exact same
``MutualExclusionRule``/``FunctionalRelationRule`` object shape
``contradiction.py`` already reads, and delegates to
``MutualExclusionConstraint``/``FunctionalRelationConstraint``
themselves (via a small evaluate-time augmented structure -- see
``_DelegatingConstraint``) rather than reimplementing their logic.
Authoring a ``MutualExclusionRule``/``FunctionalRelationRule`` object
directly continues to work exactly as before and is unaffected by
this module; ``OntologyRule`` is simply an additional, more uniform
way to declare the same thing (and to declare ``temporal_validity``/
``layering_rule`` opt-in, which have no rule-object shape of their
own since they take no per-declaration parameters).
"""

from __future__ import annotations

from collections.abc import Callable, Mapping

from ..core import KnowledgeObject, KnowledgeStructure, ObjectIdentity
from ..diagnostics import Diagnostic, DiagnosticSeverity
from ..validation import ValidationStage
from .base import Constraint
from .contradiction import (
    FUNCTIONAL_RELATION_RULE_TYPE,
    MUTUAL_EXCLUSION_RULE_TYPE,
    FunctionalRelationConstraint,
    MutualExclusionConstraint,
)
from .layering import LayeringRuleConstraint
from .temporal import TemporalValidityConstraint

# Canonical vocabulary for this extension.
ONTOLOGY_RULE_TYPE = "OntologyRule"

_CONSTRAINT_TYPE_KEY = "constraint_type"
_ENABLED_KEY = "enabled"
_TARGET_RELATION_TYPE_KEY = "target_relation_type"
_PARAMETERS_KEY = "parameters"

_DYNAMIC_LOAD_DIAGNOSTIC_ID = "CKS-EXT-DYNAMIC-CONSTRAINT-LOAD"


def _malformed(*, rule_id: str, message: str) -> Diagnostic:
    return Diagnostic(
        identity=_DYNAMIC_LOAD_DIAGNOSTIC_ID,
        severity=DiagnosticSeverity.ERROR,
        message=message,
        location=rule_id,
    )


class _DelegatingConstraint(Constraint):
    """Adapter: evaluate an existing rule-object-reading ``Constraint``
    (``target``) against ``structure`` augmented with a synthetic
    legacy rule object per well-formed ``OntologyRule`` this instance
    was built from.

    Only ever constructed by this module's builders -- never
    registered globally, never returned for a structure with no
    matching ``OntologyRule`` objects.

    Malformed source rules (missing a required parameter) never reach
    ``target``: they're translated into their own diagnostic here,
    at evaluate time, so one malformed ``OntologyRule`` cannot suppress
    the well-formed ones alongside it in the same structure.
    """

    stage = ValidationStage.SEMANTIC

    def __init__(
        self,
        *,
        identity: str,
        target: Constraint,
        synthesize: Callable[[KnowledgeObject], KnowledgeObject | Diagnostic],
        rule_objects: tuple[KnowledgeObject, ...],
    ) -> None:
        self.identity = identity
        self.description = (
            f"Structure-declared ({ONTOLOGY_RULE_TYPE}) constraint, "
            f"delegating to {type(target).__name__}."
        )
        self._target = target
        self._synthesize = synthesize
        self._rule_objects = rule_objects

    def evaluate(self, structure: KnowledgeStructure) -> list[Diagnostic]:
        synthetic_objects: list[KnowledgeObject] = []
        diagnostics: list[Diagnostic] = []

        for rule_obj in self._rule_objects:
            result = self._synthesize(rule_obj)
            if isinstance(result, Diagnostic):
                diagnostics.append(result)
            else:
                synthetic_objects.append(result)

        if synthetic_objects:
            augmented = KnowledgeStructure((*structure.objects, *synthetic_objects))
            diagnostics.extend(self._target.evaluate(augmented))

        return diagnostics


class _DirectConstraint(Constraint):
    """Adapter for a ``constraint_type`` whose underlying ``Constraint``
    takes no per-declaration parameters at all (``temporal_validity``,
    ``layering_rule``): simply runs ``target`` unmodified. Declaring
    one or more ``OntologyRule`` objects of this ``constraint_type``
    only ever *opts the behaviour in*; the objects carry no data this
    adapter needs to read beyond having found them.
    """

    stage = ValidationStage.SEMANTIC

    def __init__(self, *, identity: str, target: Constraint) -> None:
        self.identity = identity
        self.description = (
            f"Structure-declared ({ONTOLOGY_RULE_TYPE}) constraint, "
            f"delegating to {type(target).__name__}."
        )
        self._target = target

    def evaluate(self, structure: KnowledgeStructure) -> list[Diagnostic]:
        return self._target.evaluate(structure)


def _synth_id(rule_obj: KnowledgeObject, suffix: str) -> str:
    # Reserved prefix, extremely unlikely to collide with a real
    # authored id; even in the pathological case of a collision,
    # KnowledgeStructure's duplicate-id check will raise loudly at
    # evaluate time rather than silently merging two distinct objects.
    return f"__dynamic_synth__:{rule_obj.identity.id}:{suffix}"


def _synthesize_functional_relation(
    rule_obj: KnowledgeObject,
) -> KnowledgeObject | Diagnostic:
    relation_type = rule_obj.structure.get(_TARGET_RELATION_TYPE_KEY)
    if not relation_type:
        return _malformed(
            rule_id=rule_obj.identity.id,
            message=(
                f"OntologyRule '{rule_obj.identity.id}' has "
                f"constraint_type='functional_relation' but is missing "
                f"the required '{_TARGET_RELATION_TYPE_KEY}' field."
            ),
        )
    return KnowledgeObject(
        identity=ObjectIdentity(
            id=_synth_id(rule_obj, "functional_relation"),
            type=FUNCTIONAL_RELATION_RULE_TYPE,
            name=rule_obj.identity.name,
        ),
        structure={"relation_type": relation_type},
    )


def _synthesize_mutual_exclusion(
    rule_obj: KnowledgeObject,
) -> KnowledgeObject | Diagnostic:
    parameters = rule_obj.structure.get(_PARAMETERS_KEY) or {}
    if not isinstance(parameters, Mapping):
        parameters = {}
    type_a = parameters.get("relation_type_a")
    type_b = parameters.get("relation_type_b")
    missing = [
        name
        for name, value in (("relation_type_a", type_a), ("relation_type_b", type_b))
        if not value
    ]
    if missing:
        return _malformed(
            rule_id=rule_obj.identity.id,
            message=(
                f"OntologyRule '{rule_obj.identity.id}' has "
                f"constraint_type='mutual_exclusion' but is missing "
                f"required parameters: {missing}."
            ),
        )
    return KnowledgeObject(
        identity=ObjectIdentity(
            id=_synth_id(rule_obj, "mutual_exclusion"),
            type=MUTUAL_EXCLUSION_RULE_TYPE,
            name=rule_obj.identity.name,
        ),
        structure={"relation_type_a": type_a, "relation_type_b": type_b},
    )


def _build_functional_relation(
    rule_objects: tuple[KnowledgeObject, ...],
) -> Constraint:
    return _DelegatingConstraint(
        identity="CKS-EXT-DYNAMIC-FUNCTIONAL-RELATION",
        target=FunctionalRelationConstraint(),
        synthesize=_synthesize_functional_relation,
        rule_objects=rule_objects,
    )


def _build_mutual_exclusion(rule_objects: tuple[KnowledgeObject, ...]) -> Constraint:
    return _DelegatingConstraint(
        identity="CKS-EXT-DYNAMIC-MUTUAL-EXCLUSION",
        target=MutualExclusionConstraint(),
        synthesize=_synthesize_mutual_exclusion,
        rule_objects=rule_objects,
    )


def _build_temporal_validity(_rule_objects: tuple[KnowledgeObject, ...]) -> Constraint:
    return _DirectConstraint(
        identity="CKS-EXT-DYNAMIC-TEMPORAL-VALIDITY",
        target=TemporalValidityConstraint(),
    )


def _build_layering_rule(_rule_objects: tuple[KnowledgeObject, ...]) -> Constraint:
    return _DirectConstraint(
        identity="CKS-EXT-DYNAMIC-LAYERING-RULE",
        target=LayeringRuleConstraint(),
    )


# constraint_type -> builder(rule_objects_of_that_type) -> Constraint.
# Every OntologyRule sharing a constraint_type is grouped and handed
# to its builder together (one Constraint instance per constraint_type
# present in a structure, not one per OntologyRule object) so that,
# e.g., two functional_relation declarations for two different
# relation_types don't each independently re-scan/re-report the
# other's synthetic object.
_BUILDERS: dict[str, Callable[[tuple[KnowledgeObject, ...]], Constraint]] = {
    "functional_relation": _build_functional_relation,
    "mutual_exclusion": _build_mutual_exclusion,
    "temporal_validity": _build_temporal_validity,
    "layering_rule": _build_layering_rule,
}


def load_dynamic_constraints(structure: KnowledgeStructure) -> tuple[Constraint, ...]:
    """Scan ``structure`` for ``OntologyRule`` objects and return the
    ``Constraint`` instances they declare, one per distinct
    (recognized) ``constraint_type`` present.

    Pure and deterministic: never mutates ``structure`` or any global
    state (including ``cks.constraints.registry.registry``), and
    returns the same result every time for the same input. Returned
    constraints are meant to be passed as ``extra_constraints`` for a
    single validation call, never registered globally.

    An ``OntologyRule`` object is considered when ``identity.type ==
    "OntologyRule"`` and ``structure.enabled`` is not literally
    ``False`` (missing, ``True``, or any other truthy value all
    count as enabled).

    An unrecognized ``constraint_type`` (including a missing one) is
    silently ignored, not diagnosed -- the same "no surprise, no
    crash" choice ``RelationTypeConstraint`` and
    ``TypeHierarchyCycleConstraint`` already make for objects they
    don't recognize the shape of, and consistent with an
    ``OntologyRule`` object simply being irrelevant to *this* loader
    if it's meant for a different consumer/loader entirely.
    Malformed-but-recognized rules (a known ``constraint_type``
    missing a required parameter) are different: they *do* surface a
    diagnostic, produced lazily inside the returned ``Constraint``'s
    ``evaluate`` (see ``_DelegatingConstraint``) rather than here, so
    that this loader itself stays a simple, non-raising scan.
    """
    grouped: dict[str, list[KnowledgeObject]] = {}
    for obj in structure.objects:
        if obj.identity.type != ONTOLOGY_RULE_TYPE:
            continue
        if obj.structure.get(_ENABLED_KEY) is False:
            continue
        constraint_type = obj.structure.get(_CONSTRAINT_TYPE_KEY)
        if constraint_type not in _BUILDERS:
            continue
        grouped.setdefault(constraint_type, []).append(obj)

    constraints = [
        _BUILDERS[constraint_type](tuple(rule_objects))
        for constraint_type, rule_objects in grouped.items()
    ]
    # Sorted by identity for a deterministic return order regardless
    # of dict iteration order (stable across Python versions in
    # practice, but this makes the guarantee explicit and independent
    # of that implementation detail).
    return tuple(sorted(constraints, key=lambda c: c.identity))


__all__ = [
    "ONTOLOGY_RULE_TYPE",
    "load_dynamic_constraints",
]
