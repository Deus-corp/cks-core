"""
CKS Constraints — Built-in Canonical Constraints.

Reference implementations of the canonical constraints defined by the
CKS specifications.

This module serves as a manifest. All constraint implementations reside
in the corresponding domain modules (structural, semantic, derivation,
etc.).
"""

from __future__ import annotations

from .structural import UniqueIdentityConstraint, NoDanglingRelationConstraint
from .semantic import DerivationArityConstraint, DerivationCycleConstraint
from .projection import EmbeddingProjectionIntegrityConstraint
from .verification import VerificationRecordIntegrityConstraint
from .ontology import TypeHierarchyCycleConstraint, RelationTypeConstraint
from .contradiction import MutualExclusionConstraint, FunctionalRelationConstraint


# =============================================================================
# Built-in Constraint Set
# =============================================================================
#
# Normative constraints defined by CKS-001..CKS-008. These are
# auto-registered into the global registry (see constraints/__init__.py)
# and therefore apply to every call to cks.validate() by default.

BUILTIN_CONSTRAINTS = (
    # --- Structural Domain ---
    UniqueIdentityConstraint(),
    NoDanglingRelationConstraint(),
    # --- Semantic Domain ---
    DerivationArityConstraint(),
    DerivationCycleConstraint(),
)


# =============================================================================
# Optional Constraint Set
# =============================================================================
#
# Extensions built on top of the CKS-001..CKS-008 core vocabulary, but
# not themselves part of the normative specifications. NOT auto-registered:
# opt in explicitly, e.g.
#
#     from cks.constraints.builtin import OPTIONAL_CONSTRAINTS
#     from cks.constraints.registry import ConstraintRegistry, registry
#
#     for constraint in OPTIONAL_CONSTRAINTS:
#         registry.register(constraint)   # process-wide, or:
#
#     custom = ConstraintRegistry()
#     for constraint in (*BUILTIN_CONSTRAINTS, *OPTIONAL_CONSTRAINTS):
#         custom.register(constraint)     # scoped to one ReferenceValidator

OPTIONAL_CONSTRAINTS = (
    # --- Projection Domain (CKS-001 "Documents as Structural Projections") ---
    EmbeddingProjectionIntegrityConstraint(),
    VerificationRecordIntegrityConstraint(),
    # --- Ontology Domain (declared type hierarchy + relation typing) ---
    TypeHierarchyCycleConstraint(),
    RelationTypeConstraint(),
    # --- Contradiction Domain (declared mutual exclusion / functional relations) ---
    MutualExclusionConstraint(),
    FunctionalRelationConstraint(),
)

# Stable name -> constraint lookup for callers that select extensions by
# name at the API boundary (e.g. an MCP tool parameter such as
# `extensions=["embedding_projection"]`). Keeps that name->constraint
# mapping defined once, in core, instead of re-implemented per caller.
OPTIONAL_CONSTRAINTS_BY_NAME = {
    "embedding_projection": EmbeddingProjectionIntegrityConstraint(),
    "verification_record": VerificationRecordIntegrityConstraint(),
    "type_hierarchy": TypeHierarchyCycleConstraint(),
    "relation_type": RelationTypeConstraint(),
    "mutual_exclusion": MutualExclusionConstraint(),
    "functional_relation": FunctionalRelationConstraint(),
}