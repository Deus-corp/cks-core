"""
CKS Extension Constraints — Contradiction Detection.

Status: EXTENSION, not part of the normative CKS-001..CKS-008 core
specifications. Not registered by default (see OPTIONAL_CONSTRAINTS in
`builtin.py`); callers must opt in explicitly.

Rationale
---------
`ontology.py` (this package) lets a graph declare which types a
relation is allowed to connect, but says nothing about relations that
are each individually well-typed and yet jointly nonsensical: nothing
stops a graph from asserting both "Earth supports TheoryX" and "Earth
contradicts TheoryX", or "Pluto orbits Sun" and, moments later,
"Pluto orbits Neptune", if a planet is only meant to orbit one star.
Structural validation (CKS-001/CKS-005) and the ontology extension
both pass such a graph -- every relation individually references real
objects of allowed types. The contradiction only becomes visible when
two relations are read *together*.

Following the same approach as `ontology.py` -- and, before it,
`projection.py`/`verification.py` -- this treats the rules for what
counts as a contradiction as ordinary Knowledge Objects declared
inside the graph, rather than external configuration. Two declaration
shapes are supported, matching two different kinds of contradiction:

``MutualExclusionRule``
    Declares that two relation_types must never both connect the same
    ordered pair of participants (``structure = {"relation_type_a":
    "supports", "relation_type_b": "contradicts"}``). If both a
    ``supports`` and a ``contradicts`` relation exist from the same
    source to the same target, that is flagged. Only 2-participant
    relations are considered, and only the exact ordered (source,
    target) pair -- the same reasoning `RelationTypeConstraint` uses,
    for the same reason: arity and directionality are established
    elsewhere (`CanonicalRelation.participants`), not redefined here.

``FunctionalRelationRule``
    Declares that a relation_type is *functional*: a given source may
    have at most one target for it (``structure = {"relation_type":
    "orbits"}``). If the same source has two or more distinct targets
    via that relation_type, that is flagged -- e.g. "Earth orbits Sun"
    and "Earth orbits Mars" both asserted, when orbiting is meant to
    be single-valued.

Multiple declarations of either kind accumulate (set union) rather
than the "last one wins" rule `RelationTypeConstraint` uses for
`TypeRule` -- there is no conflicting parameter to arbitrate between
two `MutualExclusionRule`/`FunctionalRelationRule` objects the way
there can be between two `TypeRule` objects for the same
relation_type, so every declaration simply adds to the set of pairs/
relation_types being checked.

A structure with no ``MutualExclusionRule``/``FunctionalRelationRule``
objects is entirely unaffected by either constraint below -- the same
additive-by-default property every other extension in this package
has.
"""

from __future__ import annotations

from ..core import KnowledgeStructure
from ..diagnostics import Diagnostic, DiagnosticSeverity
from ..validation import ValidationStage
from .base import Constraint

# Canonical vocabulary for this extension.
MUTUAL_EXCLUSION_RULE_TYPE = "MutualExclusionRule"
FUNCTIONAL_RELATION_RULE_TYPE = "FunctionalRelationRule"

# Structural content keys.
_RELATION_TYPE_A_KEY = "relation_type_a"
_RELATION_TYPE_B_KEY = "relation_type_b"
_RELATION_TYPE_KEY = "relation_type"


def _error(*, identity: str, message: str, location: str | None = None) -> Diagnostic:
    return Diagnostic(
        identity=identity,
        severity=DiagnosticSeverity.ERROR,
        message=message,
        location=location,
    )


class MutualExclusionConstraint(Constraint):
    """Two relation_types declared mutually exclusive by a
    ``MutualExclusionRule`` shall not both connect the same ordered
    pair of participants."""

    identity = "CKS-EXT-MUTUAL-EXCLUSION"
    stage = ValidationStage.SEMANTIC
    description = (
        "Relation types declared mutually exclusive must not both "
        "connect the same ordered pair of participants."
    )

    def evaluate(self, structure: KnowledgeStructure) -> list[Diagnostic]:
        pairs: set[tuple[str, str]] = set()
        for obj in structure.objects:
            if obj.identity.type != MUTUAL_EXCLUSION_RULE_TYPE:
                continue
            type_a = obj.structure.get(_RELATION_TYPE_A_KEY)
            type_b = obj.structure.get(_RELATION_TYPE_B_KEY)
            if not type_a or not type_b or type_a == type_b:
                continue
            pairs.add(tuple(sorted((type_a, type_b))))

        if not pairs:
            return []

        by_relation_type: dict[str, dict[tuple[str, str], str]] = {}
        for relation in structure.relations():
            if len(relation.participants) != 2:
                continue
            source_id, target_id = relation.participants
            by_relation_type.setdefault(relation.relation_type, {})[
                (source_id, target_id)
            ] = relation.identity.id

        diagnostics: list[Diagnostic] = []
        for type_a, type_b in sorted(pairs):
            map_a = by_relation_type.get(type_a, {})
            map_b = by_relation_type.get(type_b, {})
            for participants in sorted(set(map_a) & set(map_b)):
                source_id, target_id = participants
                relation_a_id = map_a[participants]
                relation_b_id = map_b[participants]
                diagnostics.append(
                    _error(
                        identity=self.identity,
                        message=(
                            f"Relation '{relation_a_id}' (type '{type_a}') "
                            f"and relation '{relation_b_id}' (type "
                            f"'{type_b}') both connect '{source_id}' to "
                            f"'{target_id}', but a MutualExclusionRule "
                            f"declares these relation_types mutually "
                            f"exclusive."
                        ),
                        location=relation_a_id,
                    )
                )
        return diagnostics


class FunctionalRelationConstraint(Constraint):
    """A relation_type declared functional by a
    ``FunctionalRelationRule`` shall connect each source to at most
    one target."""

    identity = "CKS-EXT-FUNCTIONAL-RELATION"
    stage = ValidationStage.SEMANTIC
    description = (
        "A relation_type declared functional must connect each source "
        "to at most one target."
    )

    def evaluate(self, structure: KnowledgeStructure) -> list[Diagnostic]:
        functional_types: set[str] = set()
        for obj in structure.objects:
            if obj.identity.type != FUNCTIONAL_RELATION_RULE_TYPE:
                continue
            relation_type = obj.structure.get(_RELATION_TYPE_KEY)
            if relation_type:
                functional_types.add(relation_type)

        if not functional_types:
            return []

        # relation_type -> source_id -> {target_id: relation_id}
        targets_by_source: dict[str, dict[str, dict[str, str]]] = {}
        for relation in structure.relations():
            if relation.relation_type not in functional_types:
                continue
            if len(relation.participants) != 2:
                continue
            source_id, target_id = relation.participants
            bucket = targets_by_source.setdefault(
                relation.relation_type, {}
            ).setdefault(source_id, {})
            bucket[target_id] = relation.identity.id

        diagnostics: list[Diagnostic] = []
        for relation_type in sorted(targets_by_source):
            sources = targets_by_source[relation_type]
            for source_id in sorted(sources):
                targets = sources[source_id]
                if len(targets) <= 1:
                    continue
                target_ids = sorted(targets)
                first_relation_id = min(targets.values())
                diagnostics.append(
                    _error(
                        identity=self.identity,
                        message=(
                            f"Source '{source_id}' has {len(targets)} "
                            f"distinct targets via functional relation_type "
                            f"'{relation_type}': {target_ids}. A "
                            f"FunctionalRelationRule declares this "
                            f"relation_type single-valued per source."
                        ),
                        location=first_relation_id,
                    )
                )
        return diagnostics


__all__ = [
    "FUNCTIONAL_RELATION_RULE_TYPE",
    "MUTUAL_EXCLUSION_RULE_TYPE",
    "FunctionalRelationConstraint",
    "MutualExclusionConstraint",
]