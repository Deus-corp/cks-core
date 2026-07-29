"""
CKS Extension Constraints — Embedding Projections.

Status: EXTENSION, not part of the normative CKS-001..CKS-008 core
specifications. Not registered by default (see OPTIONAL_CONSTRAINTS
in `builtin.py`); callers must opt in explicitly.

Rationale
---------
CKS-001 ("Documents as Structural Projections") defines:

    Document = Projection(CKS)

i.e. any concrete representation of a Canonical Knowledge Structure
-- an article, a website, a database -- is a *projection*, never a
primary source of semantics. This module treats vector-space
representations (embeddings used for structured retrieval) as one
more instance of the same general mechanism, rather than as a
foreign concept bolted onto CKS:

    EmbeddingProjection = Projection(KnowledgeObject) into vector space

An EmbeddingProjection is a specialised Knowledge Object. Per CKS-001
("Canonical Derivations"), it records *provenance* -- which source
object it represents and by which method -- not the vector payload
itself. Storage architectures and optimization strategies are an
explicit Non-Goal of the Core Specification, so the actual vector
(and any ANN index) must live in an external store; this module only
enforces that the *reference* to that external store is present and
that the link back to a real, existing source object is intact.

This gives a concrete, mechanically checked anti-hallucination
property for retrieval: if a generation step cites an
EmbeddingProjection, NoDanglingRelationConstraint and
EmbeddingProjectionIntegrityConstraint together guarantee that
citation resolves to a real canonical object, never a fabricated one.
"""

from __future__ import annotations

from ..core import KnowledgeStructure
from ..diagnostics import Diagnostic, DiagnosticSeverity
from ..validation import ValidationStage
from .base import Constraint

# Canonical vocabulary for this extension. Deliberately distinct from
# the existing `cks.project()` API (subgraph extraction by identity),
# which is an unrelated, pre-existing concept.
REPRESENTS_RELATION = "represents"
EMBEDDING_PROJECTION_TYPE = "EmbeddingProjection"

# Structural content keys.
_STORE_REF_KEY = "store_ref"
_DISALLOWED_INLINE_PAYLOAD_KEYS = ("vector", "embedding")


def _error(*, identity: str, message: str, location: str | None = None) -> Diagnostic:
    return Diagnostic(
        identity=identity,
        severity=DiagnosticSeverity.ERROR,
        message=message,
        location=location,
    )


class EmbeddingProjectionIntegrityConstraint(Constraint):
    """
    Every EmbeddingProjection object shall:

      1. have exactly one 'represents' relation to an existing
         source Knowledge Object;
      2. reference its vector payload via a non-empty 'store_ref'
         rather than embedding raw vector data inline.

    This constraint is additive: Knowledge Structures that do not use
    the EmbeddingProjection type are entirely unaffected by it.
    """

    identity = "CKS-EXT-EMBEDDING-PROJECTION"
    stage = ValidationStage.SEMANTIC
    description = (
        "EmbeddingProjection objects must carry exactly one valid "
        "provenance link and reference their payload externally."
    )

    def evaluate(self, structure: KnowledgeStructure) -> list[Diagnostic]:
        diagnostics: list[Diagnostic] = []
        existing = {obj.identity.id for obj in structure.objects}

        # projection_id -> [source_id, ...]
        sources_by_projection: dict[str, list[str]] = {}
        for relation in structure.relations():
            if relation.relation_type != REPRESENTS_RELATION:
                continue
            if len(relation.participants) != 2:
                continue
            source_id, projection_id = relation.participants
            sources_by_projection.setdefault(projection_id, []).append(source_id)

        for obj in structure.objects:
            if obj.identity.type != EMBEDDING_PROJECTION_TYPE:
                continue

            sources = sources_by_projection.get(obj.identity.id, [])
            if len(sources) != 1:
                diagnostics.append(
                    _error(
                        identity=self.identity,
                        message=(
                            f"EmbeddingProjection '{obj.identity.id}' must have "
                            f"exactly one '{REPRESENTS_RELATION}' relation to its "
                            f"source object (found {len(sources)})."
                        ),
                        location=obj.identity.id,
                    )
                )
            elif sources[0] not in existing:
                # Also independently caught by NoDanglingRelationConstraint
                # at the STRUCTURAL stage; reported here too so this
                # constraint's own diagnostic is self-explanatory.
                diagnostics.append(
                    _error(
                        identity=self.identity,
                        message=(
                            f"EmbeddingProjection '{obj.identity.id}' references "
                            f"unknown source object '{sources[0]}'."
                        ),
                        location=obj.identity.id,
                    )
                )

            store_ref = obj.structure.get(_STORE_REF_KEY)
            if not store_ref:
                diagnostics.append(
                    _error(
                        identity=self.identity,
                        message=(
                            f"EmbeddingProjection '{obj.identity.id}' must "
                            f"reference its payload via a non-empty "
                            f"'{_STORE_REF_KEY}' rather than embedding it."
                        ),
                        location=obj.identity.id,
                    )
                )

            leaked = [k for k in _DISALLOWED_INLINE_PAYLOAD_KEYS if k in obj.structure]
            if leaked:
                diagnostics.append(
                    _error(
                        identity=self.identity,
                        message=(
                            f"EmbeddingProjection '{obj.identity.id}' must not "
                            f"embed raw vector payloads inline "
                            f"({', '.join(sorted(leaked))}); store the vector "
                            f"externally and reference it via '{_STORE_REF_KEY}'."
                        ),
                        location=obj.identity.id,
                    )
                )

        return diagnostics


__all__ = [
    "EMBEDDING_PROJECTION_TYPE",
    "REPRESENTS_RELATION",
    "EmbeddingProjectionIntegrityConstraint",
]
