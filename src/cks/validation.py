"""
CKS Validation — Canonical Validation Types.

This module defines the implementation-independent validation types
shared across the validator, constraint framework and future validation
extensions.

Only common validation abstractions belong here.
"""

from __future__ import annotations

from enum import Enum


# =============================================================================
# Validation Stage
# =============================================================================


class ValidationStage(str, Enum):
    """
    Canonical validation pipeline stages.

    The ordering follows CKS-006 (Validation Pipeline).

        STRUCTURAL
            ↓
        SEMANTIC
            ↓
        CONSTRAINTS
    """

    STRUCTURAL = "structural"

    SEMANTIC = "semantic"

    CONSTRAINTS = "constraints"


# =============================================================================
# Public Symbols
# =============================================================================

__all__ = [
    "ValidationStage",
]
