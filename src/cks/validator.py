"""
CKS Validator — Reference Validator Implementation.

Reference implementation of the Canonical Validator defined by

    • CKS-005 — Validator Specification
    • CKS-006 — Reference Engine
    • CKS-007 — Canonical Knowledge Interface
    • CKS-008 — Reference Conformance Specification

The validator is intentionally implementation-independent.
Validation is organised as a deterministic pipeline consisting of
independent validation stages.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass

import cks.constraints  # noqa: F401

from .constraints.base import Constraint
from .constraints.registry import ConstraintRegistry
from .constraints.registry import registry as _registry
from .core import KnowledgeStructure
from .diagnostics import Diagnostic, DiagnosticCollection, DiagnosticSeverity
from .result import ValidationResult
from .validation import ValidationStage

ConstraintEvaluator = Callable[[KnowledgeStructure], list[Diagnostic]] | Constraint


@dataclass(frozen=True, slots=True)
class PipelineStage:
    stage: ValidationStage
    evaluator: Callable[[KnowledgeStructure], list[Diagnostic]]


class ValidationPipeline:
    """Ordered deterministic validation pipeline."""

    def __init__(self, stages: Iterable[PipelineStage]) -> None:
        self._stages = tuple(stages)

    @property
    def stages(self) -> tuple[PipelineStage, ...]:
        return self._stages

    def execute(self, structure: KnowledgeStructure) -> list[Diagnostic]:
        diagnostics: list[Diagnostic] = []
        for stage in self._stages:
            diagnostics.extend(stage.evaluator(structure))
        return diagnostics


class ReferenceValidator:
    """Reference implementation of the Canonical Validator."""

    #: Canonical pipeline stage order. Single source of truth, shared
    #: by the default (self._pipeline) path and the scoped-registry
    #: path used when callers pass ``extra_constraints``.
    _STAGE_ORDER: tuple[ValidationStage, ...] = (
        ValidationStage.STRUCTURAL,
        ValidationStage.SEMANTIC,
        ValidationStage.CONSTRAINTS,
    )

    def __init__(self, registry: ConstraintRegistry | None = None) -> None:
        self._registry = registry or _registry
        self._pipeline = ValidationPipeline(
            [
                PipelineStage(ValidationStage.STRUCTURAL, self.structural_validate),
                PipelineStage(ValidationStage.SEMANTIC, self.semantic_validate),
                PipelineStage(ValidationStage.CONSTRAINTS, self.constraint_validate),
            ]
        )

    # ------------------------------------------------------------------
    # Scoped (per-call) constraint sets
    # ------------------------------------------------------------------
    #
    # ``extra_constraints`` lets a caller opt an OPTIONAL_CONSTRAINTS
    # extension (or any other Constraint, e.g. from a plugin) in for a
    # *single call*, without mutating the process-wide global registry
    # that ``registry.register(...)`` would otherwise touch. This is
    # the scoping pattern already used internally by this module's own
    # tests (a fresh ConstraintRegistry passed into ReferenceValidator)
    # — exposed here through the public API instead of requiring
    # callers to reach past it.
    #
    # Duplicate identities are skipped rather than raised on: a caller
    # re-passing a constraint that happens to already be registered
    # (e.g. because it was also enabled process-wide) is not an error.

    def _scoped_registry(
        self,
        extra_constraints: Iterable[Constraint] | None,
    ) -> ConstraintRegistry:
        if not extra_constraints:
            return self._registry

        scoped = ConstraintRegistry()
        for constraint in self._registry.constraints():
            scoped.register(constraint)
        for constraint in extra_constraints:
            if constraint.identity not in scoped:
                scoped.register(constraint)
        return scoped

    # ------------------------------------------------------------------
    # Structural Validation
    # ------------------------------------------------------------------

    def structural_validate(
        self,
        structure: KnowledgeStructure,
        *,
        extra_constraints: Iterable[Constraint] | None = None,
    ) -> list[Diagnostic]:
        registry = self._scoped_registry(extra_constraints)
        return registry.evaluate(structure, stage=ValidationStage.STRUCTURAL)

    # ------------------------------------------------------------------
    # Semantic Validation
    # ------------------------------------------------------------------

    def semantic_validate(
        self,
        structure: KnowledgeStructure,
        *,
        extra_constraints: Iterable[Constraint] | None = None,
    ) -> list[Diagnostic]:
        registry = self._scoped_registry(extra_constraints)
        return registry.evaluate(structure, stage=ValidationStage.SEMANTIC)

    # ------------------------------------------------------------------
    # Constraint Evaluation
    # ------------------------------------------------------------------

    def constraint_validate(
        self,
        structure: KnowledgeStructure,
        *,
        extra_constraints: Iterable[Constraint] | None = None,
    ) -> list[Diagnostic]:
        registry = self._scoped_registry(extra_constraints)
        return registry.evaluate(structure, stage=ValidationStage.CONSTRAINTS)

    # ------------------------------------------------------------------
    # Pipeline
    # ------------------------------------------------------------------

    def pipeline(self) -> ValidationPipeline:
        return self._pipeline

    # ------------------------------------------------------------------
    # Execute Validation
    # ------------------------------------------------------------------

    def validate(
        self,
        structure: KnowledgeStructure,
        *,
        min_severity: DiagnosticSeverity = DiagnosticSeverity.ERROR,
        extra_constraints: Iterable[Constraint] | None = None,
    ) -> ValidationResult:
        if extra_constraints:
            # Scoped path: bypass self._pipeline (which is bound to
            # self._registry) and evaluate the same canonical stage
            # order directly against a one-off registry. The default
            # (no extra_constraints) path below is untouched, so
            # existing behaviour and tests are unaffected.
            registry = self._scoped_registry(extra_constraints)
            diagnostics_raw: list[Diagnostic] = []
            for stage in self._STAGE_ORDER:
                diagnostics_raw.extend(registry.evaluate(structure, stage=stage))
            evaluated_constraints = registry.names()
        else:
            diagnostics_raw = self._pipeline.execute(structure)
            evaluated_constraints = self._registry.names()

        diagnostics = tuple(sorted(diagnostics_raw, key=Diagnostic.sort_key))
        collection = DiagnosticCollection(diagnostics=diagnostics)
        # Every diagnostic is checked against the threshold, INFORMATION
        # included. min_severity=ERROR/WARNING are unaffected either way
        # (INFORMATION's priority, 0, is already below both thresholds),
        # but excluding INFORMATION unconditionally -- as a previous
        # version of this line did -- made the CLI's documented
        # `--min-severity information` (the strictest, most-inclusive
        # setting) silently behave identically to 'warning': an
        # INFORMATION diagnostic could never invalidate a structure no
        # matter what min_severity was passed.
        valid = all(
            d.severity.priority < min_severity.priority
            for d in diagnostics
        )
        return ValidationResult(
            is_valid=valid,
            diagnostics=collection,
            evaluated_constraints=evaluated_constraints,
            metadata={
                "validator": "ReferenceValidator",
                "pipeline": tuple(s.value for s in self._STAGE_ORDER),
                "min_severity": min_severity.value,
            },
        )


# =============================================================================
# Global Reference Validator
# =============================================================================

_validator = ReferenceValidator()


# =============================================================================
# Public API
# =============================================================================


def register_constraint(fn: Constraint) -> None:
    """Register a canonical validation constraint."""
    _registry.register(fn)


def structural_validate(
    structure: KnowledgeStructure,
    *,
    extra_constraints: Iterable[Constraint] | None = None,
) -> list[Diagnostic]:
    """Execute only structural validation."""
    return _validator.structural_validate(
        structure, extra_constraints=extra_constraints
    )


def semantic_validate(
    structure: KnowledgeStructure,
    *,
    extra_constraints: Iterable[Constraint] | None = None,
) -> list[Diagnostic]:
    """Execute only semantic validation."""
    return _validator.semantic_validate(structure, extra_constraints=extra_constraints)


def evaluate_constraints(
    structure: KnowledgeStructure,
    *,
    extra_constraints: Iterable[Constraint] | None = None,
) -> list[Diagnostic]:
    """Execute all registered canonical constraints."""
    return _validator.constraint_validate(
        structure, extra_constraints=extra_constraints
    )


def validate(
    structure: KnowledgeStructure,
    *,
    min_severity: DiagnosticSeverity = DiagnosticSeverity.ERROR,
    extra_constraints: Iterable[Constraint] | None = None,
) -> ValidationResult:
    """
    Execute the complete canonical validation pipeline.

    ``extra_constraints`` opts additional Constraints (e.g. an entry
    from ``cks.constraints.builtin.OPTIONAL_CONSTRAINTS``, or a
    caller-supplied plugin constraint) in for this call only. The
    process-wide global registry is never mutated by this parameter —
    other callers and subsequent calls without ``extra_constraints``
    are unaffected.
    """
    return _validator.validate(
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
    """Validate multiple KnowledgeStructures and return individual results."""
    return [
        _validator.validate(
            s,
            min_severity=min_severity,
            extra_constraints=extra_constraints,
        )
        for s in structures
    ]
