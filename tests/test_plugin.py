"""Contract tests for the plugin system."""
import logging
import sys
from importlib.metadata import EntryPoint

import pytest

from cks.constraints.base import Constraint
from cks.constraints.registry import ConstraintRegistry
from cks.plugin import (
    discover_entry_points,
    load_constraints_from_entry_point,
    load_external_constraints,
)


class _ValidConstraint(Constraint):
    identity = "TEST-VALID"
    description = "A valid test constraint."

    def evaluate(self, structure):
        return []


# ---------------------------------------------------------------------------
# Helper: create a realistic EntryPoint for a given factory.
# ---------------------------------------------------------------------------

def _make_entrypoint(name: str, factory, group: str = "cks.constraints"):
    """Return an EntryPoint that wraps *factory*."""
    return EntryPoint(
        name=name,
        value=f"{factory.__module__}:{factory.__qualname__}",
        group=group,
    )


# ---------------------------------------------------------------------------
# Factory functions used by the tests.
# ---------------------------------------------------------------------------

def _factory_valid():
    return [_ValidConstraint()]


def _factory_broken():
    raise RuntimeError("Simulated plugin error")


def _factory_empty():
    return []


def _factory_mixed():
    return [_ValidConstraint(), "not-a-constraint"]


# ---------------------------------------------------------------------------
# Actual tests
# ---------------------------------------------------------------------------

def test_load_valid_constraint():
    ep = _make_entrypoint("valid", _factory_valid)
    constraints = load_constraints_from_entry_point(ep)
    assert len(constraints) == 1
    assert isinstance(constraints[0], Constraint)


def test_load_empty_plugin():
    ep = _make_entrypoint("empty", _factory_empty)
    constraints = load_constraints_from_entry_point(ep)
    assert len(constraints) == 0


def test_load_mixed_plugin():
    ep = _make_entrypoint("mixed", _factory_mixed)
    with pytest.raises(TypeError, match="not a Constraint"):
        load_constraints_from_entry_point(ep)


def test_strict_mode_raises():
    ep = _make_entrypoint("broken", _factory_broken)
    with pytest.raises(RuntimeError, match="Simulated plugin error"):
        load_constraints_from_entry_point(ep)


def test_non_strict_mode_logs(caplog):
    registry = ConstraintRegistry()
    caplog.set_level(logging.WARNING)

    # Create an entry point that will fail, and one that succeeds.
    broken_ep = _make_entrypoint("broken", _factory_broken)
    valid_ep = _make_entrypoint("valid", _factory_valid)

    # Temporarily patch discover_entry_points to return our controlled set.
    def _fake_eps():
        yield from [broken_ep, valid_ep]

    import cks.plugin as p
    original = p.discover_entry_points
    p.discover_entry_points = _fake_eps
    try:
        count = p.load_external_constraints(registry=registry)
    finally:
        p.discover_entry_points = original

    # The valid plugin should have been registered; the broken one logged.
    assert count == 1
    assert "Could not load plugin" in caplog.text