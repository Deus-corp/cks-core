"""
CKS Extension Constraints — Type Ontology.

Status: EXTENSION, not part of the normative CKS-001..CKS-008 core
specifications. Not registered by default (see OPTIONAL_CONSTRAINTS
in `builtin.py`); callers must opt in explicitly.

Rationale
---------
`ObjectIdentity.type` (CKS-001) is an unconstrained string. That is
correct as a baseline -- CKS is representation- and domain-agnostic,
so the Core Specification cannot bake in any particular taxonomy --
but it also means nothing today stops a relation such as ``orbits``
from connecting a ``Planet`` to a ``Recipe``. Two graphs can disagree
silently about what a type name even means, and no constraint
currently catches it.

This module treats a type taxonomy the same way `projection.py` and
`verification.py` treat embeddings and provenance: as ordinary
Knowledge Objects, declared inside the graph itself, rather than as
external configuration bolted onto the validator. Per CKS-001
("Canonical operations belong to knowledge itself"), a declaration
such as "Planet is a kind of CelestialBody" or "an `orbits` relation
only connects CelestialBody instances" is itself knowledge, and is
validated the same way everything else is: by constraints reading the
structure.

Two Knowledge Object types carry these declarations:

``TypeDefinition``
    Declares that one type name is a subtype of another
    (``structure = {"type_name": "Planet", "parent_type":
    "CelestialBody"}``). ``parent_type`` is optional; a
    ``TypeDefinition`` without one simply introduces a root type name.

``TypeRule``
    Declares which object types a given ``relation_type`` may connect
    (``structure = {"relation_type": "orbits", "allowed_source_types":
    ["Planet", "Moon"], "allowed_target_types": ["Star", "Planet"]}``).
    Either list may be omitted, leaving that side unconstrained.

A structure with no ``TypeDefinition``/``TypeRule`` objects is
entirely unaffected by either constraint below -- the same
additive-by-default property `EmbeddingProjectionIntegrityConstraint`
and `VerificationRecordIntegrityConstraint` already have.
"""

from __future__ import annotations

from typing import Any, Mapping

from ..core import KnowledgeStructure
from ..diagnostics import Diagnostic, DiagnosticSeverity
from ..validation import ValidationStage
from .base import Constraint

# Canonical vocabulary for this extension.
TYPE_DEFINITION_TYPE = "TypeDefinition"
TYPE_RULE_TYPE = "TypeRule"

# Structural content keys.
_TYPE_NAME_KEY = "type_name"
_PARENT_TYPE_KEY = "parent_type"
_RELATION_TYPE_KEY = "relation_type"
_ALLOWED_SOURCE_TYPES_KEY = "allowed_source_types"
_ALLOWED_TARGET_TYPES_KEY = "allowed_target_types"


def _error(*, identity: str, message: str, location: str | None = None) -> Diagnostic:
    return Diagnostic(
        identity=identity,
        severity=DiagnosticSeverity.ERROR,
        message=message,
        location=location,
    )


class TypeHierarchy:
    """An is-a hierarchy of object type names, built from every
    ``TypeDefinition`` object in a Knowledge Structure.

    This is a plain helper, not a `Constraint` -- it is shared by both
    constraints below and may also be used directly by callers (e.g.
    an MCP tool) that want to reason about declared subtyping without
    running full validation.
    """

    def __init__(self, structure: KnowledgeStructure) -> None:
        self._parent: dict[str, str] = {}
        # type_name -> id of the TypeDefinition object that declared it,
        # kept for diagnostic locations elsewhere in this module.
        self._declared_by: dict[str, str] = {}

        for obj in structure.objects:
            if obj.identity.type != TYPE_DEFINITION_TYPE:
                continue
            type_name = obj.structure.get(_TYPE_NAME_KEY)
            if not type_name:
                continue
            self._declared_by.setdefault(type_name, obj.identity.id)
            parent_type = obj.structure.get(_PARENT_TYPE_KEY)
            if parent_type:
                self._parent[type_name] = parent_type

    def is_subtype(self, candidate: str, ancestor: str) -> bool:
        """True if ``candidate`` equals ``ancestor``, or descends from
        it through declared ``parent_type`` links.

        Cycle-safe: a cyclic declaration (reported separately by
        `TypeHierarchyCycleConstraint`) simply stops matching once a
        type already seen in this walk is encountered again, rather
        than looping forever.
        """
        seen: set[str] = set()
        current: str | None = candidate
        while current is not None:
            if current == ancestor:
                return True
            if current in seen:
                return False
            seen.add(current)
            current = self._parent.get(current)
        return False

    def cyclic_types(self) -> dict[str, str]:
        """Return ``{type_name: declaring_object_id}`` for every type
        name that lies *on* a ``parent_type`` cycle.

        Since each type name has at most one ``parent_type``, the
        declarations form a functional graph: every node has
        out-degree <= 1. A single forward walk per undiscovered node
        is therefore enough to find every cycle -- if a walk revisits
        a node already seen *in that same walk*, everything from the
        first occurrence of that node onward is the cycle. A walk
        that instead reaches a node already resolved by an earlier
        walk is merely a tail leading into already-known territory,
        not a new cycle, so it is left unflagged.
        """
        cyclic: dict[str, str] = {}
        resolved: set[str] = set()

        for start in self._parent:
            if start in resolved:
                continue
            path: list[str] = []
            position: dict[str, int] = {}
            current: str | None = start
            while current is not None and current not in resolved:
                if current in position:
                    for name in path[position[current]:]:
                        cyclic[name] = self._declared_by.get(name, name)
                    break
                position[current] = len(path)
                path.append(current)
                current = self._parent.get(current)
            resolved.update(path)

        return cyclic


class TypeHierarchyCycleConstraint(Constraint):
    """A ``TypeDefinition``'s ``parent_type`` chain shall not form a
    cycle (e.g. Planet is-a Moon is-a Planet)."""

    identity = "CKS-EXT-TYPE-HIERARCHY-CYCLE"
    stage = ValidationStage.SEMANTIC
    description = (
        "TypeDefinition parent_type declarations must not form a cycle."
    )

    def evaluate(self, structure: KnowledgeStructure) -> list[Diagnostic]:
        hierarchy = TypeHierarchy(structure)
        cyclic = hierarchy.cyclic_types()
        return [
            _error(
                identity=self.identity,
                message=(
                    f"Type '{type_name}' participates in a TypeDefinition "
                    f"parent_type cycle."
                ),
                location=object_id,
            )
            for type_name, object_id in sorted(cyclic.items())
        ]


class RelationTypeConstraint(Constraint):
    """Every relation whose ``relation_type`` has a declared
    ``TypeRule`` shall connect objects whose types (or declared
    subtypes, per `TypeHierarchy`) are allowed by that rule.

    Only 2-participant relations are checked; arity itself is the
    concern of other constraints (e.g. `DerivationArityConstraint`),
    and dangling references are the concern of
    `NoDanglingRelationConstraint`. If more than one `TypeRule` object
    declares the same `relation_type`, the last one encountered (in
    structure order) wins -- this mirrors how a caller would expect a
    single logical rule per relation_type, and a structure asserting
    two different rules for one relation_type is a modelling error the
    author should resolve, not something this constraint tries to
    reconcile silently.
    """

    identity = "CKS-EXT-RELATION-TYPE"
    stage = ValidationStage.SEMANTIC
    description = (
        "Relations must connect objects of types allowed by any "
        "declared TypeRule for their relation_type."
    )

    def evaluate(self, structure: KnowledgeStructure) -> list[Diagnostic]:
        rules: dict[str, Mapping[str, Any]] = {}
        for obj in structure.objects:
            if obj.identity.type != TYPE_RULE_TYPE:
                continue
            relation_type = obj.structure.get(_RELATION_TYPE_KEY)
            if not relation_type:
                continue
            rules[relation_type] = obj.structure

        if not rules:
            return []

        hierarchy = TypeHierarchy(structure)
        objects_by_id = {obj.identity.id: obj for obj in structure.objects}
        diagnostics: list[Diagnostic] = []

        for relation in structure.relations():
            rule = rules.get(relation.relation_type)
            if rule is None:
                continue
            if len(relation.participants) != 2:
                continue

            source_id, target_id = relation.participants
            source_obj = objects_by_id.get(source_id)
            target_obj = objects_by_id.get(target_id)
            # Dangling participants are NoDanglingRelationConstraint's
            # job (STRUCTURAL stage); this constraint only reasons
            # about endpoints that actually resolve.
            if source_obj is None or target_obj is None:
                continue

            allowed_source = rule.get(_ALLOWED_SOURCE_TYPES_KEY)
            if allowed_source and not any(
                hierarchy.is_subtype(source_obj.identity.type, allowed)
                for allowed in allowed_source
            ):
                diagnostics.append(
                    _error(
                        identity=self.identity,
                        message=(
                            f"Relation '{relation.identity.id}' of type "
                            f"'{relation.relation_type}' has source "
                            f"'{source_id}' of type "
                            f"'{source_obj.identity.type}', which is not "
                            f"one of the allowed source types "
                            f"{list(allowed_source)} (or a declared "
                            f"subtype)."
                        ),
                        location=relation.identity.id,
                    )
                )

            allowed_target = rule.get(_ALLOWED_TARGET_TYPES_KEY)
            if allowed_target and not any(
                hierarchy.is_subtype(target_obj.identity.type, allowed)
                for allowed in allowed_target
            ):
                diagnostics.append(
                    _error(
                        identity=self.identity,
                        message=(
                            f"Relation '{relation.identity.id}' of type "
                            f"'{relation.relation_type}' has target "
                            f"'{target_id}' of type "
                            f"'{target_obj.identity.type}', which is not "
                            f"one of the allowed target types "
                            f"{list(allowed_target)} (or a declared "
                            f"subtype)."
                        ),
                        location=relation.identity.id,
                    )
                )

        return diagnostics


__all__ = [
    "TypeHierarchy",
    "TypeHierarchyCycleConstraint",
    "RelationTypeConstraint",
    "TYPE_DEFINITION_TYPE",
    "TYPE_RULE_TYPE",
]