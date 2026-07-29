"""
CKS Schema — JSON Schema Validation.

This module validates serialized Knowledge Structures against the
canonical JSON Schema (CKS‑003).  It is used by the parser to catch
structural errors early, before semantic validation.
"""

from __future__ import annotations

import json
from importlib import resources
from typing import Any

import jsonschema
from jsonschema import validate as jsonschema_validate

# The canonical schema ships as package data (see [tool.setuptools.package-data]
# in pyproject.toml) so it is available both when running from source and
# when installed from a built wheel/sdist.
_SCHEMA_PACKAGE = "cks.schemas"
_SCHEMA_FILENAME = "cks-schema.json"

# Load schema once at import time.
with (
    resources.files(_SCHEMA_PACKAGE)
    .joinpath(_SCHEMA_FILENAME)
    .open("r", encoding="utf-8") as _fh
):
    _CANONICAL_SCHEMA: dict[str, Any] = json.load(_fh)


class SchemaValidationError(Exception):
    """Raised when a JSON document fails schema validation."""


def validate_json(
    data: dict[str, Any], *, schema: dict[str, Any] | None = None
) -> None:
    """Validate *data* against the canonical CKS JSON Schema.

    Parameters
    ----------
    data
        The JSON document to validate.
    schema
        An optional schema dictionary.  If not provided, the canonical
        CKS schema is used.

    Raises
    ------
    SchemaValidationError
        If *data* does not conform to the schema.
    """
    target = schema if schema is not None else _CANONICAL_SCHEMA
    try:
        jsonschema_validate(data, target)
    except jsonschema.exceptions.ValidationError as exc:
        raise SchemaValidationError(str(exc)) from exc


__all__ = [
    "SchemaValidationError",
    "validate_json",
]