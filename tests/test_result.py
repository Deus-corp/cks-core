import pytest

from cks.diagnostics import (
    Diagnostic,
    DiagnosticCollection,
    DiagnosticSeverity,
)
from cks.result import ValidationResult


def make_error() -> Diagnostic:
    return Diagnostic(
        identity="TEST-ERROR",
        severity=DiagnosticSeverity.ERROR,
        message="Error",
    )


def make_warning() -> Diagnostic:
    return Diagnostic(
        identity="TEST-WARNING",
        severity=DiagnosticSeverity.WARNING,
        message="Warning",
    )


def test_validation_result_default_metadata():
    result = ValidationResult(
        is_valid=True,
    )

    assert result.metadata == {}


def test_validation_result_metadata_is_immutable():
    result = ValidationResult(
        is_valid=True,
    )

    with pytest.raises(TypeError):
        result.metadata["x"] = 1


def test_valid_result_cannot_contain_errors():
    diagnostics = DiagnosticCollection(
        (make_error(),)
    )

    with pytest.raises(ValueError):
        ValidationResult(
            is_valid=True,
            diagnostics=diagnostics,
        )


def test_merge_results():
    left = ValidationResult(
        is_valid=True,
        evaluated_constraints=("A",),
    )

    right = ValidationResult(
        is_valid=False,
        diagnostics=DiagnosticCollection(
            (make_error(),)
        ),
        evaluated_constraints=("B",),
    )

    merged = left.merge(right)

    assert not merged.is_valid
    assert merged.error_count == 1
    assert merged.evaluated_constraints == ("A", "B")


def test_bool_protocol():
    assert bool(
        ValidationResult(is_valid=True)
    )

    assert not bool(
        ValidationResult(is_valid=False)
    )


def test_summary_valid():
    result = ValidationResult(
        is_valid=True,
    )

    assert result.summary() == "Valid"


def test_summary_invalid():
    result = ValidationResult(
        is_valid=False,
        diagnostics=DiagnosticCollection(
            (
                make_error(),
                make_warning(),
            )
        ),
    )

    assert "Invalid" in result.summary()
    assert "1 error" in result.summary()
    assert "1 warning" in result.summary()


def test_repr():
    result = ValidationResult(
        is_valid=True,
    )

    assert "ValidationResult" in repr(result)