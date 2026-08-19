"""
Composition — applying a batch of operators in one pass.
"""

from __future__ import annotations

from collections.abc import Iterable

from ..core import KnowledgeStructure
from .base import StructuralOperator


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
