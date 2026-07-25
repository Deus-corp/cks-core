"""
CKS Semantic Constraints.

Canonical semantic validation constraints.
"""

from __future__ import annotations

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

        def dfs(node: str) -> None:
            colour[node] = GRAY
            for neighbour in adjacency.get(node, ()):
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
                    dfs(neighbour)
            colour[node] = BLACK

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
    "DerivationArityConstraint",
    "DerivationCycleConstraint",
    "SEMANTIC_CONSTRAINTS",
]
