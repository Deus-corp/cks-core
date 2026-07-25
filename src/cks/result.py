"""
CKS Result — Canonical Validation Result.

This module implements the immutable ValidationResult type defined in
CKS-005 (Section 7) and CKS-006 (Section 7).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Mapping

from .diagnostics import DiagnosticCollection


# ============================================================================
# Validation Result
# ============================================================================


@dataclass(frozen=True, slots=True)
class ValidationResult:
    """
    Canonical outcome of a validation execution.

    Parameters
    ----------
    is_valid
        True iff every mandatory canonical validation constraint
        has been satisfied.

    diagnostics
        Immutable collection of canonical diagnostics.

    evaluated_constraints
        Canonical identifiers of every evaluated constraint.

    metadata
        Implementation-independent execution metadata.
    """

    is_valid: bool

    diagnostics: DiagnosticCollection = field(default_factory=DiagnosticCollection)

    evaluated_constraints: tuple[str, ...] = field(default_factory=tuple)

    metadata: Mapping[str, Any] = field(default_factory=dict)

    # ------------------------------------------------------------------

    def __post_init__(self) -> None:
        """
        Preserve canonical invariants.

        A ValidationResult cannot simultaneously be valid and contain
        ERROR diagnostics.
        """

        object.__setattr__(
            self,
            "evaluated_constraints",
            tuple(self.evaluated_constraints),
        )

        metadata = MappingProxyType(dict(self.metadata))

        object.__setattr__(
            self,
            "metadata",
            metadata,
        )

        if self.is_valid and self.diagnostics.has_errors():
            raise ValueError(
                "A valid ValidationResult cannot contain ERROR diagnostics."
            )

        if not self.is_valid and not self.diagnostics.has_errors():
            #
            # Not invalidating here.
            #
            # Future specifications may introduce
            # implementation-defined failure states.
            #
            pass

    # ------------------------------------------------------------------
    # Convenience Properties
    # ------------------------------------------------------------------

    @property
    def success(self) -> bool:
        """
        Alias for is_valid.
        """
        return self.is_valid

    @property
    def error_count(self) -> int:
        return self.diagnostics.error_count

    @property
    def warning_count(self) -> int:
        return self.diagnostics.warning_count

    @property
    def information_count(self) -> int:
        return self.diagnostics.information_count

    @property
    def constraint_count(self) -> int:
        return len(self.evaluated_constraints)

    # ------------------------------------------------------------------
    # Convenience Methods
    # ------------------------------------------------------------------

    def has_errors(self) -> bool:
        return self.diagnostics.has_errors()

    def has_warnings(self) -> bool:
        return self.diagnostics.has_warnings()

    def has_information(self) -> bool:
        return self.diagnostics.has_information()

    def errors(self):
        return self.diagnostics.errors()

    def warnings(self):
        return self.diagnostics.warnings()

    def information(self):
        return self.diagnostics.information()

    # ------------------------------------------------------------------

    def summary(self) -> str:
        """
        Return a short human-readable summary.

        Examples
        --------
        Valid

        Invalid (2 errors)

        Invalid (2 errors, 1 warning)
        """

        if self.is_valid:
            return "Valid"

        parts: list[str] = []

        if self.error_count:
            parts.append(
                f"{self.error_count} error{'' if self.error_count == 1 else 's'}"
            )

        if self.warning_count:
            parts.append(
                f"{self.warning_count} warning{'' if self.warning_count == 1 else 's'}"
            )

        parts.append(
            f"{self.information_count} informational message"
            f"{'' if self.information_count == 1 else 's'}"
        )

        return "Invalid (" + ", ".join(parts) + ")"

    # ------------------------------------------------------------------
    # Composition
    # ------------------------------------------------------------------

    def merge(
        self,
        other: "ValidationResult",
    ) -> "ValidationResult":
        """
        Merge two ValidationResults.

        The merged result is valid iff both operands are valid.
        Diagnostics and evaluated constraints are combined.
        """

        return ValidationResult(
            is_valid=self.is_valid and other.is_valid,
            diagnostics=self.diagnostics.merge(other.diagnostics),
            evaluated_constraints=tuple(
                dict.fromkeys(self.evaluated_constraints + other.evaluated_constraints)
            ),
            metadata={
                **dict(self.metadata),
                **dict(other.metadata),
            },
        )

    # ------------------------------------------------------------------
    # Python Protocols
    # ------------------------------------------------------------------

    def __bool__(self) -> bool:
        """
        Truth value equals canonical validity.
        """
        return self.is_valid

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"valid={self.is_valid}, "
            f"errors={self.error_count}, "
            f"warnings={self.warning_count}, "
            f"info={self.information_count}, "
            f"constraints={self.constraint_count})"
        )


# ============================================================================
# Public Symbols
# ============================================================================

__all__ = [
    "ValidationResult",
]
