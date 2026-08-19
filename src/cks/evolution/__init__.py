"""
CKS Evolution — Canonical Structure Evolution (CKS‑004).

This package implements the Primitive Structural Extensions (PSE)
defined in CKS‑004: Knowledge Object Extension and Canonical Relation
Extension.  It also provides a generic StructuralOperator abstraction
and a composition function for building complex evolutions.

All operators are observationally pure and preserve the invariants
required by CKS‑001 and CKS‑005.

Each operator lives in its own module (one class per file); this
``__init__`` re-exports the full public surface so existing code that
imports from ``cks.evolution`` (e.g. ``from cks.evolution import
AddObject`` or ``cks.evolution.compose``) keeps working unchanged.
"""

from __future__ import annotations

from ..core import CanonicalRelation
from .add_object import AddObject
from .add_relation import AddRelation
from .base import OperatorContract, StructuralOperator
from .compose import compose
from .parse import parse_operations
from .record_inference import RecordInference
from .remove_object import RemoveObject
from .remove_relation import RemoveRelation
from .rename_object import RenameObject
from .resolve_inference_conflict import ResolveInferenceConflict
from .update_object import UpdateObject

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
#
# CanonicalRelation is re-exported here (not just from cks.core) because
# the previous single-module cks/evolution.py imported it at module level
# for AddRelation's type hints, which made `from cks.evolution import
# CanonicalRelation` importable even though it was never listed in
# __all__. Downstream consumers (e.g. cks-mcp's clone_graph tool) came
# to rely on that path, so it is kept as an explicit, intentional
# re-export rather than a broken implicit one.

__all__ = [
    "AddObject",
    "AddRelation",
    "CanonicalRelation",
    "OperatorContract",
    "RecordInference",
    "RemoveObject",
    "RemoveRelation",
    "RenameObject",
    "ResolveInferenceConflict",
    "StructuralOperator",
    "UpdateObject",
    "compose",
    "parse_operations",
]
