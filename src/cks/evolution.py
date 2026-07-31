"""
CKS Evolution — Canonical Structure Evolution (CKS‑004).

This module implements the Primitive Structural Extensions (PSE)
defined in CKS‑004: Knowledge Object Extension and Canonical Relation
Extension.  It also provides a generic StructuralOperator abstraction
and a composition function for building complex evolutions.

All operators are observationally pure and preserve the invariants
required by CKS‑001 and CKS‑005.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

from .core import (
    CanonicalRelation,
    KnowledgeObject,
    KnowledgeStructure,
)

# ---------------------------------------------------------------------------
# Structural Operator Contract
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class OperatorContract:
    """Formal contract for a StructuralOperator (CKS‑004, Section 7)."""

    description: str
    preconditions: tuple[str, ...]
    postconditions: tuple[str, ...]
    invariant_obligations: tuple[str, ...]


# ---------------------------------------------------------------------------
# Abstract Structural Operator
# ---------------------------------------------------------------------------


class StructuralOperator(ABC):
    """Abstract base class for all admissible structural evolutions."""

    def apply(self, structure: KnowledgeStructure) -> KnowledgeStructure:
        """Apply the operator, returning a *new* KnowledgeStructure."""
        objects = {obj.identity.id: obj for obj in structure.objects}
        self._mutate(objects)
        return KnowledgeStructure(objects.values())

    @abstractmethod
    def _mutate(self, objects: dict[str, KnowledgeObject]) -> None:
        """
        Apply this operator's edit in place to a working ``{id: object}``
        dict.

        This is each operator's one true implementation: ``apply()``
        above is a thin wrapper — build a dict from the structure,
        mutate it, wrap the result back into a KnowledgeStructure.
        ``compose()`` instead shares a single dict across a whole batch
        of operators and only builds the final KnowledgeStructure once
        at the end.

        This matters because constructing a KnowledgeStructure is
        O(n): it rebuilds the id index and rolls two sorted Merkle-
        style hashes over every object. Calling ``apply()`` N times in
        a row (the previous implementation of ``compose()``) paid that
        O(n) cost on every single operator, making an N-operator batch
        over an n-object structure cost O(n·N) even though most
        operators only ever touch one or two objects. Routing through
        this shared dict makes ``compose()`` itself O(n) overall,
        independent of N.
        """
        ...

    @abstractmethod
    def contract(self) -> OperatorContract:
        """Return the operator's formal contract."""
        ...

    def __call__(self, structure: KnowledgeStructure) -> KnowledgeStructure:
        return self.apply(structure)


# ---------------------------------------------------------------------------
# Genesis – Knowledge Object Extension
# ---------------------------------------------------------------------------


class AddObject(StructuralOperator):
    """Introduce a new KnowledgeObject into the structure."""

    def __init__(self, obj: KnowledgeObject) -> None:
        self._obj = obj

    @property
    def obj(self) -> KnowledgeObject:
        """The KnowledgeObject to be added."""
        return self._obj

    def _mutate(self, objects: dict[str, KnowledgeObject]) -> None:
        if self._obj.identity.id in objects:
            raise ValueError(f"Object '{self._obj.identity.id}' already exists.")
        objects[self._obj.identity.id] = self._obj

    def contract(self) -> OperatorContract:
        return OperatorContract(
            description=f"Add KnowledgeObject '{self._obj.identity.id}'.",
            preconditions=(
                "The object's identity must be unique within the structure.",
            ),
            postconditions=("The object is present in the structure.",),
            invariant_obligations=("Object identity uniqueness is preserved.",),
        )


# ---------------------------------------------------------------------------
# Genesis – Canonical Relation Extension
# ---------------------------------------------------------------------------


class AddRelation(StructuralOperator):
    """Introduce a new CanonicalRelation between existing objects."""

    def __init__(self, relation: CanonicalRelation) -> None:
        self._relation = relation

    @property
    def relation(self) -> CanonicalRelation:
        """The CanonicalRelation to be added."""
        return self._relation

    def _mutate(self, objects: dict[str, KnowledgeObject]) -> None:
        if self._relation.identity.id in objects:
            raise ValueError(f"Relation '{self._relation.identity.id}' already exists.")
        # Ensure every participant exists
        for pid in self._relation.participants:
            if pid not in objects:
                raise ValueError(f"Participant '{pid}' does not exist.")
        objects[self._relation.identity.id] = self._relation

    def contract(self) -> OperatorContract:
        return OperatorContract(
            description=f"Add CanonicalRelation '{self._relation.identity.id}'.",
            preconditions=(
                "The relation's identity must be unique.",
                "All participants must reference existing objects.",
            ),
            postconditions=("The relation is present in the structure.",),
            invariant_obligations=("Referential integrity is preserved.",),
        )


# ---------------------------------------------------------------------------
# Decay – Removal Operators
# ---------------------------------------------------------------------------


class RemoveObject(StructuralOperator):
    """Remove a KnowledgeObject and all relations that reference it."""

    def __init__(self, object_id: str) -> None:
        self._object_id = object_id

    @property
    def object_id(self) -> str:
        """The id of the object to remove."""
        return self._object_id

    def _mutate(self, objects: dict[str, KnowledgeObject]) -> None:
        if self._object_id not in objects:
            raise ValueError(f"Object '{self._object_id}' does not exist.")
        del objects[self._object_id]
        # Cascade: remove any relation that referenced the object.
        for oid in [
            oid
            for oid, obj in objects.items()
            if isinstance(obj, CanonicalRelation)
            and self._object_id in obj.participants
        ]:
            del objects[oid]

    def contract(self) -> OperatorContract:
        return OperatorContract(
            description=f"Remove KnowledgeObject '{self._object_id}'.",
            preconditions=("The object must exist.",),
            postconditions=(
                "The object is absent.",
                "All relations referencing the object are also removed.",
            ),
            invariant_obligations=("Referential integrity is preserved.",),
        )


class RemoveRelation(StructuralOperator):
    """Remove a CanonicalRelation by its identity."""

    def __init__(self, relation_id: str) -> None:
        self._relation_id = relation_id

    @property
    def relation_id(self) -> str:
        """The id of the relation to remove."""
        return self._relation_id

    def _mutate(self, objects: dict[str, KnowledgeObject]) -> None:
        target = objects.get(self._relation_id)
        if target is None:
            raise ValueError(f"Relation '{self._relation_id}' does not exist.")
        if not isinstance(target, CanonicalRelation):
            # Without this check, RemoveRelation would silently accept
            # a plain KnowledgeObject id and remove the object itself
            # *without* cascading to relations that reference it --
            # unlike RemoveObject, which does cascade. That would leave
            # a dangling reference behind and violate the
            # "referential integrity is preserved" contract below.
            raise TypeError(
                f"'{self._relation_id}' is a KnowledgeObject, not a "
                "CanonicalRelation; use RemoveObject instead (it will "
                "also cascade-remove any relations that reference it)."
            )
        del objects[self._relation_id]

    def contract(self) -> OperatorContract:
        return OperatorContract(
            description=f"Remove CanonicalRelation '{self._relation_id}'.",
            preconditions=(
                "The relation must exist.",
                (
                    "The identity must refer to a CanonicalRelation, not a "
                    "plain KnowledgeObject."
                ),
            ),
            postconditions=("The relation is absent.",),
            invariant_obligations=("Referential integrity is preserved.",),
        )


# ---------------------------------------------------------------------------
# Metabolism – In-Place Update
# ---------------------------------------------------------------------------


class UpdateObject(StructuralOperator):
    """
    Update an existing KnowledgeObject's ``structure`` fields in place.

    Unlike ``RemoveObject`` followed by ``AddObject`` -- previously the
    only way to change a KnowledgeObject's content -- this operator
    never touches the object's identity or the relations that
    reference it: since ``identity.id`` is unchanged, every
    ``CanonicalRelation`` with this object as a participant remains
    valid with no cascade, and no relation has to be reconstructed by
    the caller.

    Two update modes are supported:

    - ``"merge"`` (default): ``structure_patch`` is shallow-merged into
      the object's existing ``structure`` dict. A key mapped to
      ``None`` in the patch removes that key from ``structure``; every
      other key is set/overwritten. Keys not mentioned in the patch
      are left untouched.
    - ``"replace"``: the object's ``structure`` dict is replaced
      wholesale with ``structure_patch``.
    """

    def __init__(
        self,
        object_id: str,
        structure_patch: dict[str, Any],
        *,
        mode: str = "merge",
    ) -> None:
        if mode not in ("merge", "replace"):
            raise ValueError(
                f"Unknown update mode '{mode}'; expected 'merge' or 'replace'."
            )
        self._object_id = object_id
        self._structure_patch = structure_patch
        self._mode = mode

    @property
    def object_id(self) -> str:
        """The id of the object to update."""
        return self._object_id

    @property
    def structure_patch(self) -> dict[str, Any]:
        """The patch to apply to the object's structure."""
        return dict(self._structure_patch)

    @property
    def mode(self) -> str:
        """Update mode: 'merge' or 'replace'."""
        return self._mode

    def _mutate(self, objects: dict[str, KnowledgeObject]) -> None:
        target = objects.get(self._object_id)
        if target is None:
            raise ValueError(f"Object '{self._object_id}' does not exist.")
        if isinstance(target, CanonicalRelation):
            raise TypeError(
                f"'{self._object_id}' is a CanonicalRelation; "
                "UpdateObject only updates plain KnowledgeObjects."
            )

        if self._mode == "replace":
            new_structure_dict = dict(self._structure_patch)
        else:
            new_structure_dict = dict(target.structure)
            for key, value in self._structure_patch.items():
                if value is None:
                    new_structure_dict.pop(key, None)
                else:
                    new_structure_dict[key] = value

        objects[self._object_id] = KnowledgeObject(
            identity=target.identity,
            structure=new_structure_dict,
        )

    def contract(self) -> OperatorContract:
        return OperatorContract(
            description=(
                f"Update KnowledgeObject '{self._object_id}' (mode={self._mode})."
            ),
            preconditions=(
                "The object must exist.",
                "The object must not be a CanonicalRelation.",
            ),
            postconditions=(
                "The object's identity is unchanged.",
                "The object's structure reflects the patch.",
            ),
            invariant_obligations=(
                (
                    "Referential integrity is preserved (no relation is "
                    "touched, since the object's id does not change)."
                ),
            ),
        )


# ---------------------------------------------------------------------------
# Rename – Identity Mutation
# ---------------------------------------------------------------------------


class RenameObject(StructuralOperator):
    """
    Rename an existing KnowledgeObject: change its ``identity.name``
    while leaving ``identity.id`` and ``identity.type`` untouched.

    This is strictly weaker than a full identity change: ``id`` is the
    canonical reference key used by every ``CanonicalRelation``'s
    ``participants`` list, so keeping it means no relation is invalidated
    and no cascade is needed. Only the human-readable ``name`` field —
    which carries no structural semantics inside the graph — is updated.

    Use ``RemoveObject`` + ``AddObject`` if you need to change the ``id``
    or ``type`` of an object (at the cost of cascade-removing all
    referencing relations first).
    """

    def __init__(self, object_id: str, new_name: str) -> None:
        if not new_name or not new_name.strip():
            raise ValueError("new_name must be a non-empty string.")
        self._object_id = object_id
        self._new_name = new_name

    @property
    def object_id(self) -> str:
        """The id of the object to rename."""
        return self._object_id

    @property
    def new_name(self) -> str:
        """The new human-readable name for the object."""
        return self._new_name

    def _mutate(self, objects: dict[str, KnowledgeObject]) -> None:
        target = objects.get(self._object_id)
        if target is None:
            raise ValueError(f"Object '{self._object_id}' does not exist.")

        from .core import ObjectIdentity

        new_identity = ObjectIdentity(
            id=target.identity.id,
            type=target.identity.type,
            name=self._new_name,
        )
        if isinstance(target, CanonicalRelation):
            objects[self._object_id] = CanonicalRelation(
                identity=new_identity,
                participants=list(target.participants),
                relation_type=target.relation_type,
                structure={
                    k: v
                    for k, v in target.structure.items()
                    if k not in ("participants", "relation_type")
                },
            )
        else:
            objects[self._object_id] = KnowledgeObject(
                identity=new_identity,
                structure=dict(target.structure),
            )

    def contract(self) -> OperatorContract:
        return OperatorContract(
            description=(
                f"Rename KnowledgeObject '{self._object_id}' "
                f"to '{self._new_name}'."
            ),
            preconditions=("The object must exist.",),
            postconditions=(
                "The object's identity.name is updated to the new value.",
                "The object's identity.id and identity.type are unchanged.",
            ),
            invariant_obligations=(
                (
                    "Referential integrity is preserved (no relation is "
                    "touched, since the object's id does not change)."
                ),
            ),
        )


# ---------------------------------------------------------------------------
# Reasoning – Inference Recording (ADR-001)
# ---------------------------------------------------------------------------


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
        # cks.constraints package at module-import time -- evolution.py
        # otherwise only ever imports from .core.
        from .constraints.reasoning import INFERENCE_STEP_TYPE

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


# ---------------------------------------------------------------------------
# JSON Deserialization of Operators
# ---------------------------------------------------------------------------
#
# Consumers (the CLI, cks-mcp, and any other adapter) receive evolution
# requests as plain JSON — a list of dicts such as
# ``{"type": "add_object", "identity": {...}, "structure": {...}}``.
# This is the single canonical place that turns that wire format into
# concrete StructuralOperator instances, so every adapter shares the
# same admissible operation set and the same error messages.


def parse_operations(ops_data: Iterable[dict[str, Any]]) -> list[StructuralOperator]:
    """
    Parse a JSON-compatible list of operation descriptors into
    StructuralOperators.

    Parameters
    ----------
    ops_data
        A sequence of dicts, each with a ``"type"`` field of
        ``"add_object" | "add_relation" | "remove_object" |
        "remove_relation" | "update_object" | "rename_object" |
        "record_inference"``
        and the fields required by that operation.

    Raises
    ------
    ValueError
        If an operation descriptor is missing required fields or has an
        unknown ``"type"``.
    """
    from .core import ObjectIdentity

    operators: list[StructuralOperator] = []

    def _build_identity(i: int, identity_data: Any) -> ObjectIdentity:
        """Construct an ObjectIdentity from a JSON-decoded operation
        field, translating any malformed shape (missing/unexpected
        subfield, wrong type) into the same ValueError-with-operation-
        index style used for every other check in this function --
        ObjectIdentity itself only raises a raw, less-specific
        TypeError for these cases."""
        if not isinstance(identity_data, dict):
            # ValueError (not TypeError) is deliberate here: every other
            # malformed-input check in this function raises ValueError,
            # and callers (the CLI's `evolve` command) only catch that.
            raise ValueError(  # noqa: TRY004
                f"Operation #{i}: 'identity' must be an object, got "
                f"{type(identity_data).__name__}"
            )
        try:
            return ObjectIdentity(**identity_data)
        except TypeError as exc:
            raise ValueError(f"Operation #{i}: invalid 'identity': {exc}") from exc

    for i, op in enumerate(ops_data):
        op_type = op.get("type")
        if op_type is None:
            raise ValueError(f"Operation #{i}: missing 'type' field")

        if op_type == "add_object":
            identity_data = op.get("identity")
            if identity_data is None:
                raise ValueError(f"Operation #{i}: missing 'identity' field")
            identity = _build_identity(i, identity_data)
            obj = KnowledgeObject(identity=identity, structure=op.get("structure", {}))
            operators.append(AddObject(obj))

        elif op_type == "add_relation":
            identity_data = op.get("identity")
            if identity_data is None:
                raise ValueError(f"Operation #{i}: missing 'identity' field")
            identity = _build_identity(i, identity_data)
            participants = op.get("participants")
            if participants is None:
                raise ValueError(f"Operation #{i}: missing 'participants' field")
            relation_type = op.get("relation_type")
            if relation_type is None:
                raise ValueError(f"Operation #{i}: missing 'relation_type' field")
            relation = CanonicalRelation(
                identity=identity,
                participants=participants,
                relation_type=relation_type,
                structure=op.get("structure", {}),
            )
            operators.append(AddRelation(relation))

        elif op_type == "remove_object":
            object_id = op.get("object_id")
            if object_id is None:
                raise ValueError(f"Operation #{i}: missing 'object_id' field")
            operators.append(RemoveObject(object_id))

        elif op_type == "remove_relation":
            relation_id = op.get("relation_id")
            if relation_id is None:
                raise ValueError(f"Operation #{i}: missing 'relation_id' field")
            operators.append(RemoveRelation(relation_id))

        elif op_type == "update_object":
            object_id = op.get("object_id")
            if object_id is None:
                raise ValueError(f"Operation #{i}: missing 'object_id' field")
            structure_patch = op.get("structure_patch")
            if structure_patch is None:
                raise ValueError(f"Operation #{i}: missing 'structure_patch' field")
            mode = op.get("mode", "merge")
            try:
                operators.append(UpdateObject(object_id, structure_patch, mode=mode))
            except ValueError as exc:
                raise ValueError(f"Operation #{i}: {exc}") from exc

        elif op_type == "rename_object":
            object_id = op.get("object_id")
            if object_id is None:
                raise ValueError(f"Operation #{i}: missing 'object_id' field")
            new_name = op.get("new_name")
            if new_name is None:
                raise ValueError(f"Operation #{i}: missing 'new_name' field")
            try:
                operators.append(RenameObject(object_id, new_name))
            except ValueError as exc:
                raise ValueError(f"Operation #{i}: {exc}") from exc

        elif op_type == "record_inference":
            identity_data = op.get("identity")
            if identity_data is None:
                raise ValueError(f"Operation #{i}: missing 'identity' field")
            identity = _build_identity(i, identity_data)
            obj = KnowledgeObject(identity=identity, structure=op.get("structure", {}))
            try:
                operators.append(RecordInference(obj))
            except ValueError as exc:
                raise ValueError(f"Operation #{i}: {exc}") from exc

        else:
            raise ValueError(f"Operation #{i}: unknown operation type '{op_type}'")

    return operators


# ---------------------------------------------------------------------------
# Composition
# ---------------------------------------------------------------------------


def compose(
    structure: KnowledgeStructure,
    operators: Iterable[StructuralOperator],
) -> KnowledgeStructure:
    """
    Apply a sequence of operators in order, returning the final structure.

    Every operator is applied to one shared ``{id: object}`` dict via
    its ``_mutate()`` method, and the (O(n)) KnowledgeStructure — id
    index plus two sorted Merkle-style hashes — is built exactly once,
    after the last operator, rather than once per operator. See
    ``StructuralOperator._mutate`` for why that matters for batches of
    more than a couple of operators.
    """
    objects = {obj.identity.id: obj for obj in structure.objects}
    for op in operators:
        op._mutate(objects)
    return KnowledgeStructure(objects.values())


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

__all__ = [
    "AddObject",
    "AddRelation",
    "OperatorContract",
    "RecordInference",
    "RemoveObject",
    "RemoveRelation",
    "RenameObject",
    "StructuralOperator",
    "UpdateObject",
    "compose",
    "parse_operations",
]