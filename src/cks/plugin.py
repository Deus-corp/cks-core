"""
CKS Plugin — External Constraint Discovery.

This module provides a mechanism for discovering and loading canonical
validation constraints from external packages using the ``entry_points``
machinery (``importlib.metadata``).

Plugins are discovered via the ``cks.constraints`` entry-point group.
Each entry-point must reference a callable that accepts zero arguments
and returns an iterable of `Constraint` instances.

Loaded constraints are automatically registered in the canonical global
`ConstraintRegistry`.
"""

from __future__ import annotations

import logging
from typing import Iterable, List

from .constraints.base import Constraint
from .constraints.registry import ConstraintRegistry
from .constraints import registry as _global_registry

logger = logging.getLogger(__name__)


def discover_entry_points() -> Iterable:
    """Yield every entry-point registered under the ``cks.constraints`` group."""
    from importlib.metadata import entry_points

    eps = entry_points(group="cks.constraints")
    yield from eps


def load_constraints_from_entry_point(ep) -> List[Constraint]:
    """Call the entry-point and return the resulting constraints.

    Raises
    ------
    RuntimeError
        If the entry-point cannot be loaded or does not return an
        iterable of `Constraint` instances.
    """
    try:
        factory = ep.load()
    except Exception as exc:
        raise RuntimeError(
            f"Failed to load entry-point {ep.name!r} ({ep.value!r}): {exc}"
        ) from exc

    try:
        constraints = list(factory())
    except Exception as exc:
        raise RuntimeError(
            f"Entry-point factory {ep.name!r} raised an exception: {exc}"
        ) from exc

    for c in constraints:
        if not isinstance(c, Constraint):
            raise RuntimeError(
                f"Entry-point {ep.name!r} returned an object that is not "
                f"a Constraint: {c!r}"
            )
    return constraints


def load_external_constraints(
    registry: ConstraintRegistry | None = None,
    *,
    strict: bool = False,
) -> int:
    """Discover and register all external constraints.

    Parameters
    ----------
    registry : ConstraintRegistry or None
        The target registry.  If *None*, the canonical global registry
        is used.
    strict : bool
        If True, raise RuntimeError on the first plugin failure
        instead of logging a warning and continuing.

    Returns
    -------
    int
        Number of external constraints registered.
    """
    target = registry if registry is not None else _global_registry
    count = 0
    for ep in discover_entry_points():
        try:
            constraints = load_constraints_from_entry_point(ep)
        except RuntimeError:
            if strict:
                raise
            logger.warning(
                "Could not load plugin %r (%r)",
                ep.name,
                ep.value,
                exc_info=True,
            )
            continue
        for constraint in constraints:
            target.register(constraint)
            count += 1
    return count


__all__ = [
    "discover_entry_points",
    "load_constraints_from_entry_point",
    "load_external_constraints",
]
