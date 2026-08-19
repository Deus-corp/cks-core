"""
Structural Operator Contract and Abstract Base (CKS-004, Section 7).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from ..core import KnowledgeObject, KnowledgeStructure

# ---------------------------------------------------------------------------
# Structural Operator Contract
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class OperatorContract:
    """Formal contract for a StructuralOperator (CKS‑004, Section 7)."""

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
