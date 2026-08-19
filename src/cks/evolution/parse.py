"""
JSON Deserialization of Operators.

Consumers (the CLI, cks-mcp, and any other adapter) receive evolution
requests as plain JSON — a list of dicts such as
``{"type": "add_object", "identity": {...}, "structure": {...}}``.
This is the single canonical place that turns that wire format into
concrete StructuralOperator instances, so every adapter shares the
same admissible operation set and the same error messages.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from ..core import CanonicalRelation, KnowledgeObject
from .add_object import AddObject
from .add_relation import AddRelation
from .base import StructuralOperator
from .record_inference import RecordInference
from .remove_object import RemoveObject
from .remove_relation import RemoveRelation
from .rename_object import RenameObject
from .resolve_inference_conflict import ResolveInferenceConflict
from .update_object import UpdateObject


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
        "record_inference" | "resolve_inference_conflict"``
        and the fields required by that operation.

    Raises
    ------
    ValueError
        If an operation descriptor is missing required fields or has an
        unknown ``"type"``.
    """
    from ..core import ObjectIdentity

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

        elif op_type == "resolve_inference_conflict":
            conclusion_id = op.get("conclusion_id")
            if conclusion_id is None:
                raise ValueError(f"Operation #{i}: missing 'conclusion_id' field")
            winner_id = op.get("winner_id")
            if winner_id is None:
                raise ValueError(f"Operation #{i}: missing 'winner_id' field")
            try:
                operators.append(ResolveInferenceConflict(conclusion_id, winner_id))
            except ValueError as exc:
                raise ValueError(f"Operation #{i}: {exc}") from exc

        else:
            raise ValueError(f"Operation #{i}: unknown operation type '{op_type}'")

    return operators
