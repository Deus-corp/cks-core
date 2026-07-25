"""
CKS Diagnostics — Canonical Diagnostic Model.

This module implements the canonical diagnostic model defined in
CKS-006 (Section 8).

Diagnostics are immutable, observationally pure, deterministic, and
implementation-independent.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from types import MappingProxyType
from typing import Any, Mapping, Optional


# ============================================================================
# Internal Helpers
# ============================================================================


def _freeze_mapping(
    mapping: Mapping[str, Any],
) -> Mapping[str, Any]:
    """
    Return an immutable shallow copy of a mapping.

    Lists are converted to tuples.

    The returned mapping cannot be modified.
    """

    frozen: dict[str, Any] = {}

    for key, value in mapping.items():
        if isinstance(value, list):
            value = tuple(value)

        frozen[key] = value

    return MappingProxyType(frozen)


# ============================================================================
# Diagnostic Severity
# ============================================================================


class DiagnosticSeverity(str, Enum):
    """
    Canonical diagnostic severity.

    The ordering reflects increasing severity:

        INFORMATION < WARNING < ERROR
    """

    INFORMATION = "information"
    WARNING = "warning"
    ERROR = "error"

    @property
    def priority(self) -> int:
        """Numeric ordering used for deterministic sorting."""
        return {
            DiagnosticSeverity.INFORMATION: 0,
            DiagnosticSeverity.WARNING: 1,
            DiagnosticSeverity.ERROR: 2,
        }[self]


# ============================================================================
# Canonical Diagnostic
# ============================================================================


@dataclass(frozen=True, slots=True)
class Diagnostic:
    """
    Canonical diagnostic.

    Parameters
    ----------
    identity
        Canonical diagnostic identifier.

    severity
        Canonical severity level.

    message
        Human-readable explanation.

    location
        Canonical identity of the affected Knowledge Object,
        Relation, Derivation, or other entity.

    metadata
        Optional implementation-independent metadata.
    """

    identity: str

    severity: DiagnosticSeverity

    message: str

    location: Optional[str] = None

    metadata: Mapping[str, Any] = field(default_factory=dict)

    # ------------------------------------------------------------------

    def __post_init__(self) -> None:

        if not self.identity:
            raise ValueError("Diagnostic identity cannot be empty.")

        if not self.message:
            raise ValueError("Diagnostic message cannot be empty.")

        #
        # Make metadata immutable.
        #
        object.__setattr__(
            self,
            "metadata",
            _freeze_mapping(self.metadata),
        )

    # ------------------------------------------------------------------

    @property
    def is_error(self) -> bool:
        return self.severity is DiagnosticSeverity.ERROR

    @property
    def is_warning(self) -> bool:
        return self.severity is DiagnosticSeverity.WARNING

    @property
    def is_information(self) -> bool:
        return self.severity is DiagnosticSeverity.INFORMATION

    # ------------------------------------------------------------------

    def sort_key(self) -> tuple[int, str, str, str]:
        """
        Deterministic ordering key.

        Diagnostics are ordered by

        1. severity
        2. identity
        3. location
        """

        return (
            self.severity.priority,
            self.identity,
            self.location or "",
            self.message,
        )


# ============================================================================
# Diagnostic Collection
# ============================================================================


@dataclass(frozen=True, slots=True)
class DiagnosticCollection:
    """
    Immutable collection of canonical diagnostics.

    The collection is observationally pure and deterministic.
    """

    diagnostics: tuple[Diagnostic, ...] = field(default_factory=tuple)

    # ------------------------------------------------------------------

    def __post_init__(self) -> None:

        ordered = tuple(
            sorted(
                self.diagnostics,
                key=lambda d: d.sort_key(),
            )
        )

        object.__setattr__(
            self,
            "diagnostics",
            ordered,
        )

    # ------------------------------------------------------------------
    # Collection protocol
    # ------------------------------------------------------------------

    def __len__(self) -> int:
        return len(self.diagnostics)

    def __iter__(self):
        return iter(self.diagnostics)

    def __getitem__(self, index):
        return self.diagnostics[index]

    def __bool__(self) -> bool:
        return bool(self.diagnostics)

    def __contains__(self, identity: object) -> bool:
        if not isinstance(identity, str):
            return False

        return any(d.identity == identity for d in self.diagnostics)

    # ------------------------------------------------------------------
    # Statistics
    # ------------------------------------------------------------------

    @property
    def error_count(self) -> int:
        return sum(d.is_error for d in self.diagnostics)

    @property
    def warning_count(self) -> int:
        return sum(d.is_warning for d in self.diagnostics)

    @property
    def information_count(self) -> int:
        return sum(d.is_information for d in self.diagnostics)

    # ------------------------------------------------------------------

    def has_errors(self) -> bool:
        return self.error_count > 0

    def has_warnings(self) -> bool:
        return self.warning_count > 0

    def has_information(self) -> bool:
        return self.information_count > 0

    def empty(self) -> bool:
        return not self.diagnostics

    # ------------------------------------------------------------------
    # Filters
    # ------------------------------------------------------------------

    def errors(self) -> tuple[Diagnostic, ...]:
        return tuple(d for d in self.diagnostics if d.is_error)

    def warnings(self) -> tuple[Diagnostic, ...]:
        return tuple(d for d in self.diagnostics if d.is_warning)

    def information(self) -> tuple[Diagnostic, ...]:
        return tuple(d for d in self.diagnostics if d.is_information)

    def filter_by_identity(
        self,
        identity: str,
    ) -> tuple[Diagnostic, ...]:

        return tuple(d for d in self.diagnostics if d.identity == identity)

    def filter_by_location(
        self,
        location: str,
    ) -> tuple[Diagnostic, ...]:

        return tuple(d for d in self.diagnostics if d.location == location)

    # ------------------------------------------------------------------
    # Composition
    # ------------------------------------------------------------------

    def merge(
        self,
        other: "DiagnosticCollection",
    ) -> "DiagnosticCollection":

        return DiagnosticCollection(self.diagnostics + other.diagnostics)

    # ------------------------------------------------------------------

    def extend(
        self,
        diagnostics: tuple[Diagnostic, ...],
    ) -> "DiagnosticCollection":

        return DiagnosticCollection(self.diagnostics + tuple(diagnostics))

    # ------------------------------------------------------------------

    def __repr__(self) -> str:

        return (
            "DiagnosticCollection("
            f"total={len(self)}, "
            f"errors={self.error_count}, "
            f"warnings={self.warning_count}, "
            f"information={self.information_count}"
            ")"
        )


# ============================================================================
# Factory Functions
# ============================================================================


def make_information(
    *,
    identity: str,
    message: str,
    location: str | None = None,
    metadata: Mapping[str, Any] | None = None,
) -> Diagnostic:
    """
    Construct an informational Diagnostic.
    """
    return Diagnostic(
        identity=identity,
        severity=DiagnosticSeverity.INFORMATION,
        message=message,
        location=location,
        metadata=metadata or {},
    )


def make_warning(
    *,
    identity: str,
    message: str,
    location: str | None = None,
    metadata: Mapping[str, Any] | None = None,
) -> Diagnostic:
    """
    Construct a warning Diagnostic.
    """
    return Diagnostic(
        identity=identity,
        severity=DiagnosticSeverity.WARNING,
        message=message,
        location=location,
        metadata=metadata or {},
    )


def make_error(
    *,
    identity: str,
    message: str,
    location: str | None = None,
    metadata: Mapping[str, Any] | None = None,
) -> Diagnostic:
    """
    Construct an error Diagnostic.
    """
    return Diagnostic(
        identity=identity,
        severity=DiagnosticSeverity.ERROR,
        message=message,
        location=location,
        metadata=metadata or {},
    )


# ============================================================================
# Public Symbols
# ============================================================================

__all__ = [
    "DiagnosticSeverity",
    "Diagnostic",
    "DiagnosticCollection",
    "make_information",
    "make_warning",
    "make_error",
]
