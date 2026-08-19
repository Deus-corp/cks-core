"""
Decay — KnowledgeObject Removal (CKS-004).
"""

from __future__ import annotations

from ..core import CanonicalRelation, KnowledgeObject
from .base import OperatorContract, StructuralOperator


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
