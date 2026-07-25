"""
Canonical structural constraints.

These constraints validate the structural integrity of a
KnowledgeStructure.

They correspond to the Structural Validation stage defined by
CKS-005.
"""

from __future__ import annotations

from ..constraints.base import Constraint
from ..core import KnowledgeStructure
from ..validation import ValidationStage

from ..diagnostics import (
    Diagnostic,
    DiagnosticSeverity,
)


# ============================================================================
# Helpers
# ============================================================================


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


# ============================================================================
# Unique Identity Constraint
# ============================================================================


class UniqueIdentityConstraint(Constraint):
    """Every KnowledgeObject shall have a unique canonical identity."""

    identity = "CKS-STRUCT-UNIQUE-IDENTITY"
    stage = ValidationStage.STRUCTURAL
    description = "Canonical identities shall be unique."

    def evaluate(
        self,
        structure: KnowledgeStructure,
    ) -> list[Diagnostic]:

        diagnostics: list[Diagnostic] = []

        seen: set[str] = set()

        for obj in structure.objects:
            oid = obj.identity.id

            if oid in seen:
                diagnostics.append(
                    _error(
                        identity=self.identity,
                        message=(f"Duplicate canonical identity '{oid}'."),
                        location=oid,
                    )
                )

            else:
                seen.add(oid)

        return diagnostics


# ============================================================================
# Dangling Relation Constraint
# ============================================================================


class NoDanglingRelationConstraint(Constraint):
    """Every relation participant shall reference an existing object."""

    identity = "CKS-STRUCT-DANGLING-REF"
    stage = ValidationStage.STRUCTURAL
    description = "Relation participants shall exist."

    def evaluate(
        self,
        structure: KnowledgeStructure,
    ) -> list[Diagnostic]:

        diagnostics: list[Diagnostic] = []

        existing = {obj.identity.id for obj in structure.objects}

        for relation in structure.relations():
            for participant in relation.participants:
                if participant not in existing:
                    diagnostics.append(
                        _error(
                            identity=self.identity,
                            message=(
                                f"Relation '{relation.identity.id}' "
                                f"references unknown object "
                                f"'{participant}'."
                            ),
                            location=relation.identity.id,
                        )
                    )

        return diagnostics


# ============================================================================
# Canonical Structural Constraint Set
# ============================================================================

STRUCTURAL_CONSTRAINTS: tuple[Constraint, ...] = (
    UniqueIdentityConstraint(),
    NoDanglingRelationConstraint(),
)

# ============================================================================
# Public Symbols
# ============================================================================

__all__ = [
    "UniqueIdentityConstraint",
    "NoDanglingRelationConstraint",
    "STRUCTURAL_CONSTRAINTS",
]
