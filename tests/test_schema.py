"""Tests for cks.schema JSON Schema validation."""

import pytest

from cks.schema import SchemaValidationError, validate_json

# Minimal valid CKS document (just version + objects array with one object)
_VALID_CKS = {
    "version": "1.0",
    "objects": [
        {
            "identity": {"id": "obj-1", "type": "Concept", "name": "Knowledge"},
            "structure": {},
        }
    ],
}


def _invalid_cks_extra_field():
    """An object with an unknown top-level field."""
    return {
        "version": "1.0",
        "objects": [
            {
                "identity": {"id": "x", "type": "T", "name": "N"},
                "structure": {},
            }
        ],
        "unknown_field": True,
    }


def _invalid_cks_missing_objects():
    return {"version": "1.0"}


def test_valid_document_passes():
    validate_json(_VALID_CKS)


def test_invalid_extra_field_raises():
    with pytest.raises(SchemaValidationError):
        validate_json(_invalid_cks_extra_field())


def test_invalid_missing_objects_raises():
    with pytest.raises(SchemaValidationError):
        validate_json(_invalid_cks_missing_objects())


def test_custom_schema():
    custom = {
        "type": "object",
        "properties": {"a": {"type": "integer"}},
        "required": ["a"],
    }
    validate_json({"a": 1}, schema=custom)
    with pytest.raises(SchemaValidationError):
        validate_json({"a": "not int"}, schema=custom)