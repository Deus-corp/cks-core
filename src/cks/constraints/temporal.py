"""
Temporal validity constraint: flags facts whose ``valid_until`` window
has closed. Opt-in via ``extensions: ["temporal_validity"]``.
"""

from __future__ import annotations

from datetime import UTC, datetime

from cks.constraints.base import Diagnostic, DiagnosticSeverity, StructuralConstraint
from cks.core import KnowledgeStructure


class TemporalValidityConstraint(StructuralConstraint):
    identity = "CKS-EXT-TEMPORAL-VALIDITY"
    description = "Flags objects whose 'valid_until' timestamp is in the past."
    severity = DiagnosticSeverity.WARNING

    def evaluate(self, structure: KnowledgeStructure) -> list[Diagnostic]:
        diagnostics: list[Diagnostic] = []
        now = datetime.now(UTC)

        for obj in structure.objects:
            valid_until = obj.structure.get("valid_until")
            if valid_until is None:
                continue
            try:
                expiry = datetime.fromisoformat(str(valid_until))
                if expiry.tzinfo is None:
                    expiry = expiry.replace(tzinfo=UTC)
            except (ValueError, TypeError):
                diagnostics.append(
                    Diagnostic(
                        identity=self.identity,
                        severity=DiagnosticSeverity.ERROR,
                        message=f"Object '{obj.identity.id}' has malformed 'valid_until': {valid_until!r}",
                        location=obj.identity.id,
                    )
                )
                continue
            if expiry < now:
                diagnostics.append(
                    Diagnostic(
                        identity=self.identity,
                        severity=self.severity,
                        message=f"Object '{obj.identity.id}' expired at {valid_until}.",
                        location=obj.identity.id,
                    )
                )

        return diagnostics