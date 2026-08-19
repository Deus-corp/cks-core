"""
Genesis — Canonical Relation Extension (CKS-004).
"""

from __future__ import annotations

from ..core import CanonicalRelation, KnowledgeObject
from .base import OperatorContract, StructuralOperator


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
