"""
Tests for the canonical diagnostic model.
"""

import pytest

from cks.diagnostics import (
    Diagnostic,
    DiagnosticSeverity,
)

# ============================================================================
# Diagnostic Metadata
# ============================================================================


def test_metadata_is_immutable():
    diagnostic = Diagnostic(
        identity="TEST",
        severity=DiagnosticSeverity.ERROR,
        message="error",
        metadata={"x": 1},
    )

    with pytest.raises(TypeError):
        diagnostic.metadata["y"] = 2


def test_metadata_list_becomes_tuple():
    diagnostic = Diagnostic(
        identity="TEST",
        severity=DiagnosticSeverity.ERROR,
        message="error",
        metadata={
            "items": [1, 2, 3],
        },
    )

    assert diagnostic.metadata["items"] == (1, 2, 3)


# ============================================================================
# Basic Properties
# ============================================================================


def test_error_flags():
    diagnostic = Diagnostic(
        identity="TEST",
        severity=DiagnosticSeverity.ERROR,
        message="error",
    )

    assert diagnostic.is_error
    assert not diagnostic.is_warning
    assert not diagnostic.is_information


def test_warning_flags():
    diagnostic = Diagnostic(
        identity="TEST",
        severity=DiagnosticSeverity.WARNING,
        message="warning",
    )

    assert diagnostic.is_warning
    assert not diagnostic.is_error
    assert not diagnostic.is_information


def test_information_flags():
    diagnostic = Diagnostic(
        identity="TEST",
        severity=DiagnosticSeverity.INFORMATION,
        message="info",
    )

    assert diagnostic.is_information
    assert not diagnostic.is_error
    assert not diagnostic.is_warning