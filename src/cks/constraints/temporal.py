"""
CKS Extension Constraint — Temporal Validity.

Status: EXTENSION, not part of the normative CKS-001..CKS-008 core
specifications. Not registered by default (see OPTIONAL_CONSTRAINTS in
`builtin.py`); callers must opt in explicitly (extra_constraints, or
by name via OPTIONAL_CONSTRAINTS_BY_NAME["temporal_validity"]).

Rationale
---------
See ADR-003 ("Temporal Validity Constraint") in `docs/adr/`. A fact
may be true only within a bounded time window; this constraint checks
every object's ``structure`` for an optional ``valid_until`` field
(ISO-8601 datetime string) and flags it once that window has closed.
This is deliberately minimal: it answers exactly one question --
"has this fact expired?" -- and does not reason about time intervals
or temporal logic.
"""

from __future__ import annotations

from datetime import UTC, datetime

from ..core import KnowledgeStructure
from ..diagnostics import Diagnostic, DiagnosticSeverity
from ..validation import ValidationStage
from .base import Constraint


class TemporalValidityConstraint(Constraint):
    """An object's ``valid_until``, when present, shall be a
    well-formed ISO-8601 datetime that has not yet passed."""

    identity = "CKS-EXT-TEMPORAL-VALIDITY"
    stage = ValidationStage.SEMANTIC
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
                        message=(
                            f"Object '{obj.identity.id}' has malformed "
                            f"'valid_until': {valid_until!r}"
                        ),
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
