"""
Layering rule constraint: enforces that ``depends_on`` relations respect
a declared architectural layering order. Opt-in via
``extensions: ["layering_rule"]``.
"""

from __future__ import annotations

from ..core import KnowledgeStructure
from ..diagnostics import Diagnostic, DiagnosticSeverity
from ..validation import ValidationStage
from .base import Constraint


# Hardcoded for the CKS ecosystem: cks-core < cks-runtime < cks-mcp.
# A future ADR could make this configurable, but the ecosystem's own
# layering is a property of the project, not of individual deployments.
_LAYERING_ORDER = {
    "cks-core": 0,
    "cks-runtime": 1,
    "cks-mcp": 2,
}


class LayeringRuleConstraint(Constraint):
    identity = "CKS-EXT-LAYERING-RULE"
    stage = ValidationStage.SEMANTIC
    description = "Enforces architectural dependency direction (cks-core < cks-runtime < cks-mcp)."
    severity = DiagnosticSeverity.ERROR

    def evaluate(self, structure: KnowledgeStructure) -> list[Diagnostic]:
        diagnostics: list[Diagnostic] = []

        for rel in structure.relations():
            if rel.relation_type != "depends_on":
                continue
            participants = list(rel.participants)
            if len(participants) != 2:
                continue

            source_id, target_id = participants
            source_layer = _LAYERING_ORDER.get(source_id)
            target_layer = _LAYERING_ORDER.get(target_id)

            if source_layer is not None and target_layer is not None and source_layer >= target_layer:
                diagnostics.append(
                    Diagnostic(
                        identity=self.identity,
                        severity=self.severity,
                        message=f"Layering violation: '{source_id}' depends on '{target_id}' "
                                f"but layering requires cks-core < cks-runtime < cks-mcp.",
                        location=rel.identity.id,
                    )
                )

        return diagnostics