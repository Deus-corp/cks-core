"""
Genesis — Knowledge Object Extension (CKS-004).
"""

from __future__ import annotations

from ..core import KnowledgeObject
from .base import OperatorContract, StructuralOperator


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
