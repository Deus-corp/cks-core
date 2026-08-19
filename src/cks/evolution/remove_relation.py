"""
Decay — CanonicalRelation Removal (CKS-004).
"""

from __future__ import annotations

from ..core import CanonicalRelation, KnowledgeObject
from .base import OperatorContract, StructuralOperator


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
