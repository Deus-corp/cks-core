"""
CKS Semantic Constraints.

Canonical semantic validation constraints.
"""

from __future__ import annotations

from typing import Any

from ..core import KnowledgeStructure
from ..diagnostics import (
    Diagnostic,
    DiagnosticSeverity,
)
from ..validation import ValidationStage
from .base import Constraint

# =============================================================================
# Helpers
# =============================================================================


def _error(
    *,
    identity: str,
    message: str,
    location: str | None = None,
) -> Diagnostic:
    return Diagnostic(
        identity=identity,
        severity=DiagnosticSeverity.ERROR,
        message=message,
        location=location,
    )


# =============================================================================
# Derivation Arity Constraint
# =============================================================================


class DerivationArityConstraint(Constraint):
    """Every derivation relation shall have exactly two participants."""

    identity = "CKS-SEM-DERIVATION-ARITY"
    stage = ValidationStage.SEMANTIC
    description = "Derivation relations shall contain exactly two participants."

    def evaluate(
        self,
        structure: KnowledgeStructure,
    ) -> list[Diagnostic]:
        diagnostics: list[Diagnostic] = []

        for relation in structure.relations():
            if relation.relation_type != "derives":
                continue
            if len(relation.participants) != 2:
                diagnostics.append(
                    _error(
                        identity=self.identity,
                        message=(
                            "A derivation relation shall contain exactly "
                            "two participants."
                        ),
                        location=relation.identity.id,
                    )
                )
        return diagnostics


# =============================================================================
# Derivation Cycle Constraint
# =============================================================================


class DerivationCycleConstraint(Constraint):
    """Derivation relations shall not form a cycle."""

    identity = "CKS-SEM-CYCLE"
    stage = ValidationStage.SEMANTIC
    description = "Derivation cycles are prohibited."

    def evaluate(
        self,
        structure: KnowledgeStructure,
    ) -> list[Diagnostic]:
        diagnostics: list[Diagnostic] = []
        adjacency: dict[str, list[str]] = {}

        existing = {obj.identity.id for obj in structure.objects}

        for relation in structure.relations():
            if relation.relation_type != "derives":
                continue
            if len(relation.participants) != 2:
                continue
            source, target = relation.participants
            # Dangling participants are reported by
            # NoDanglingRelationConstraint (STRUCTURAL stage). This
            # constraint only reasons about edges between objects that
            # actually exist, so it must not crash on references it
            # cannot resolve.
            if source not in existing or target not in existing:
                continue
            adjacency.setdefault(source, []).append(target)

        WHITE, GRAY, BLACK = 0, 1, 2
        colour = {obj.identity.id: WHITE for obj in structure.objects}

        def dfs(start: str) -> None:
            # Iterative DFS (explicit stack of node + neighbour-iterator
            # pairs) so that a long derives-chain (thousands of nodes)
            # cannot blow the Python call stack with a RecursionError.
            # Behaviourally equivalent to the recursive walk it replaces:
            # each frame still gets to inspect every one of its
            # neighbours (a GRAY hit records a diagnostic and continues
            # on to the remaining neighbours; a WHITE hit is pushed as a
            # new frame and this frame resumes where it left off once
            # that subtree is fully explored).
            colour[start] = GRAY
            stack: list[str] = [start]
            iter_stack: list[Any] = [iter(adjacency.get(start, ()))]

            while stack:
                node = stack[-1]
                it = iter_stack[-1]
                descended = False
                for neighbour in it:
                    state = colour[neighbour]
                    if state == GRAY:
                        diagnostics.append(
                            _error(
                                identity=self.identity,
                                message="A derivation cycle was detected.",
                                location=node,
                            )
                        )
                        continue
                    if state == WHITE:
                        colour[neighbour] = GRAY
                        stack.append(neighbour)
                        iter_stack.append(iter(adjacency.get(neighbour, ())))
                        descended = True
                        break
                if not descended:
                    colour[node] = BLACK
                    stack.pop()
                    iter_stack.pop()

        for node in adjacency:
            if colour[node] == WHITE:
                dfs(node)

        return diagnostics


# =============================================================================
# Canonical Constraint Set
# =============================================================================


SEMANTIC_CONSTRAINTS = (
    DerivationArityConstraint(),
    DerivationCycleConstraint(),
)


__all__ = [
    "SEMANTIC_CONSTRAINTS",
    "DerivationArityConstraint",
    "DerivationCycleConstraint",
]
