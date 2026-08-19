"""
Metabolism — In-Place KnowledgeObject Update (CKS-004).
"""

from __future__ import annotations

from typing import Any

from ..core import CanonicalRelation, KnowledgeObject
from .base import OperatorContract, StructuralOperator


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
