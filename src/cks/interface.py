"""
CKS Interface — Canonical Public API.

This module provides the canonical entry points defined by the
Canonical Knowledge Interface (CKS-007).

Applications should normally import functions from this module rather
than interacting directly with internal implementation modules.

Every exported function is:

    • deterministic
    • observationally pure
    • implementation-independent
"""

from __future__ import annotations

from typing import Iterable, Mapping, Any

from .core import (
    KnowledgeObject,
    KnowledgeStructure,
    SubgraphResult,
)

from .engine import ReferenceEngine
from .result import ValidationResult
from .serialization import SerializationError
from .diagnostics import DiagnosticCollection, DiagnosticSeverity

from .validator import validate as _validate, validate_all as _validate_all
from .constraints.base import Constraint

__all__ = [
    # Construction
    "construct",
    "parse",
    "serialize",
    # Validation
    "validate",
    "diagnose",
    # Inspection
    "inspect",
    "compare",
    "extract",
    "project",
    # Evolution
    "evolve",
    # Public classes
    "ReferenceEngine",
    "SerializationError",
    "merge",
]

# Canonical shared ReferenceEngine.
#
# The ReferenceEngine is stateless and observationally pure, therefore a
# single process-wide instance is sufficient.
_ENGINE = ReferenceEngine()

# =============================================================================
# Canonical Public API
# =============================================================================

# ---------------------------------------------------------------------------
# Construction & Serialization
# ---------------------------------------------------------------------------


def construct(
    objects: Iterable[KnowledgeObject],
) -> KnowledgeStructure:
    """
    Construct a canonical KnowledgeStructure.

    This is the canonical entry point for building structures from
    Knowledge Objects.
    """
    return _ENGINE.construct(objects)


def parse(
    source: str | dict,
) -> KnowledgeStructure:
    """
    Parse canonical JSON into a KnowledgeStructure.

    The accepted serialization format is defined by CKS-003.
    """
    return _ENGINE.parse(source)


def serialize(
    structure: KnowledgeStructure,
) -> str:
    """
    Serialize a KnowledgeStructure to canonical JSON.

    The resulting representation is suitable for canonical round-trip
    serialization.
    """
    return _ENGINE.serialize(structure)


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def diagnose(
    structure: KnowledgeStructure,
) -> DiagnosticCollection:
    """
    Return only diagnostics produced during validation.

    Unlike validate(), this function omits the ValidationResult wrapper.
    """
    return _ENGINE.diagnose(structure)


# ---------------------------------------------------------------------------
# Inspection & Comparison
# ---------------------------------------------------------------------------


def inspect(
    structure: KnowledgeStructure,
) -> Mapping[str, object]:
    """
    Return a canonical summary of the structure's observable properties.
    """
    return _ENGINE.inspect(structure)


def compare(
    left: KnowledgeStructure,
    right: KnowledgeStructure,
) -> Mapping[str, object]:
    """
    Compare two KnowledgeStructures.

    Comparison is based on canonical structural equivalence.
    """
    return _ENGINE.compare(left, right)


def extract(
    structure: KnowledgeStructure,
    identity: str,
) -> KnowledgeObject | None:
    """
    Extract a single KnowledgeObject by its canonical identity.
    """
    return _ENGINE.extract(structure, identity)


def project(
    structure: KnowledgeStructure,
    identities: Iterable[str],
) -> KnowledgeStructure:
    """
    Project a subset of a KnowledgeStructure.

    Missing identities are ignored.
    """
    return _ENGINE.project(structure, identities)


# ---------------------------------------------------------------------------
# Evolution
# ---------------------------------------------------------------------------


def evolve(
    structure: KnowledgeStructure,
    operators: Iterable[Any],
) -> KnowledgeStructure:
    """
    Apply a sequence of admissible structural operators to a Knowledge Structure.

    Parameters
    ----------
    structure
        Original immutable structure.
    operators
        Structural operators implementing the desired evolution
        (Genesis/Decay).  Each operator must satisfy its contract.
    """
    return _ENGINE.evolve(structure, operators=operators)


def validate(
    structure: KnowledgeStructure,
    *,
    min_severity: DiagnosticSeverity = DiagnosticSeverity.ERROR,
    extra_constraints: Iterable[Constraint] | None = None,
) -> ValidationResult:
    return _validate(
        structure,
        min_severity=min_severity,
        extra_constraints=extra_constraints,
    )


def validate_all(
    structures: Iterable[KnowledgeStructure],
    *,
    min_severity: DiagnosticSeverity = DiagnosticSeverity.ERROR,
    extra_constraints: Iterable[Constraint] | None = None,
) -> list[ValidationResult]:
    return _validate_all(
        structures,
        min_severity=min_severity,
        extra_constraints=extra_constraints,
    )


def merge(
    base: KnowledgeStructure,
    branch_a: KnowledgeStructure,
    branch_b: KnowledgeStructure,
) -> KnowledgeStructure:
    """
    Three-way merge of independently evolved Knowledge Structures.

    ``base`` is the common ancestor; ``branch_a`` and ``branch_b``
    are two structures independently evolved from it.  Returns the
    merged result.

    Raises :class:`MergeConflictError` when the two branches changed
    the same identity to different, irreconcilable results.
    """
    return base.merge(branch_a, branch_b)


def query_subgraph(
    structure: KnowledgeStructure,
    seed_ids: str | Iterable[str],
    depth: int = 1,
    *,
    include_relation_types: set[str] | None = None,
    include_object_types: set[str] | None = None,
    max_tokens: int | None = None,
    max_objects: int | None = None,
    type_weights: dict[str, float] | None = None,
) -> SubgraphResult:
    """
    Extract the local neighborhood around ``seed_ids`` out to
    ``depth`` hops, as a self-contained, dangling-reference-free
    subgraph.

    See :meth:`KnowledgeStructure.query_subgraph` for the full
    contract: traversal semantics (including n-ary relations),
    budget/ranking behavior, and what each ``SubgraphResult`` field
    means.
    """
    return structure.query_subgraph(
        seed_ids,
        depth,
        include_relation_types=include_relation_types,
        include_object_types=include_object_types,
        max_tokens=max_tokens,
        max_objects=max_objects,
        type_weights=type_weights,
    )
