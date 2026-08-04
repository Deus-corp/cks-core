"""
CKS Extension Constraint — Layering Rule.

Status: EXTENSION, not part of the normative CKS-001..CKS-008 core
specifications. Not registered by default (see OPTIONAL_CONSTRAINTS in
`builtin.py`); callers must opt in explicitly (extra_constraints, or
by name via OPTIONAL_CONSTRAINTS_BY_NAME["layering_rule"]).

Rationale
---------
See ADR-004 ("Layering Rule Constraint") in `docs/adr/`. The CKS
ecosystem has a documented layering -- `cks-core` (semantic engine)
depended on by `cks-runtime` (operational layer), in turn depended on
by `cks-mcp` (protocol layer) -- enforced today only by `pyproject.toml`
and developer discipline. This constraint mechanically checks every
`depends_on` relation in the graph against that layering order and
raises an `ERROR` when a dependency points the wrong way (e.g. a
`cks-core → depends_on → cks-runtime` relation, which would make the
lower layer depend on the higher one).
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
    """A ``depends_on`` relation between two recognized CKS components
    shall point from a higher layer to a lower one (e.g. ``cks-runtime``
    may depend on ``cks-core``, never the reverse)."""

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

            if source_layer is None or target_layer is None:
                continue

            # A dependent component must sit strictly above the layer it
            # depends on (cks-runtime[1] -> cks-core[0] is fine). Anything
            # else -- depending downward-or-equal, e.g. cks-core[0] ->
            # cks-runtime[1] -- points the wrong way through the stack.
            if source_layer <= target_layer:
                diagnostics.append(
                    Diagnostic(
                        identity=self.identity,
                        severity=self.severity,
                        message=(
                            f"Layering violation: '{source_id}' depends on '{target_id}' "
                            f"but layering requires cks-core < cks-runtime < cks-mcp."
                        ),
                        location=rel.identity.id,
                    )
                )

        return diagnostics