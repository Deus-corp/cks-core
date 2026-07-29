"""
CKS Constraints — Canonical Constraint Registry.

The registry stores canonical constraints and provides deterministic
lookup and evaluation.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..core import KnowledgeStructure
from ..diagnostics import Diagnostic
from ..validation import ValidationStage
from .base import Constraint


@dataclass(slots=True)
class ConstraintRegistry:
    """
    Registry of canonical constraints.

    Registration preserves insertion order.

    Duplicate identities are rejected.
    """

    _constraints: list[Constraint] = field(default_factory=list)

    _index: dict[str, Constraint] = field(default_factory=dict)

    # ------------------------------------------------------------------

    def register(
        self,
        constraint: Constraint,
    ) -> None:
        """
        Register a canonical constraint.
        """

        if constraint.identity in self._index:
            raise ValueError(
                f"Constraint '{constraint.identity}' is already registered."
            )

        self._constraints.append(constraint)
        self._index[constraint.identity] = constraint

    # ------------------------------------------------------------------

    def clear(self) -> None:
        """
        Remove every registered constraint.
        """

        self._constraints.clear()
        self._index.clear()

    # ------------------------------------------------------------------

    def constraints(
        self,
        *,
        stage: ValidationStage | None = None,
    ) -> tuple[Constraint, ...]:
        """
        Return registered constraints.

        When stage is specified only constraints belonging to the
        requested stage are returned.
        """

        if stage is None:
            return tuple(self._constraints)

        return tuple(
            constraint for constraint in self._constraints if constraint.stage is stage
        )

    # ------------------------------------------------------------------

    def names(self) -> tuple[str, ...]:
        """
        Canonical constraint identifiers.
        """

        return tuple(constraint.identity for constraint in self._constraints)

    # ------------------------------------------------------------------

    def __contains__(
        self,
        identity: str,
    ) -> bool:
        """
        Return True if a constraint with the given identity
        is registered.
        """

        return identity in self._index

    # ------------------------------------------------------------------

    def get(
        self,
        identity: str,
    ) -> Constraint | None:
        """
        Return a registered constraint by identity.
        """

        return self._index.get(identity)

    # ------------------------------------------------------------------

    def evaluate(
        self,
        structure: KnowledgeStructure,
        *,
        stage: ValidationStage | None = None,
    ) -> list[Diagnostic]:
        """
        Evaluate registered constraints.
        """

        diagnostics: list[Diagnostic] = []

        for constraint in self.constraints(stage=stage):
            diagnostics.extend(constraint(structure))

        return diagnostics


# =============================================================================
# Canonical Global Registry
# =============================================================================

registry = ConstraintRegistry()

__all__ = [
    "ConstraintRegistry",
    "registry",
]
