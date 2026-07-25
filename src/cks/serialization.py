"""
CKS Serialization — Canonical JSON Serialization.

This module implements the canonical serialization model defined in
CKS-003 (Canonical Serialization) and exposes the serialization
operations required by CKS-007 (Canonical Knowledge Interface).

The implementation is observationally pure:
serialization and deserialization never modify their inputs.
"""

from __future__ import annotations

import json
from typing import Any
from types import MappingProxyType

from .core import (
    CanonicalRelation,
    KnowledgeObject,
    KnowledgeStructure,
    ObjectIdentity,
)

# ============================================================================
# Canonical Serialization Constants
# ============================================================================

CANONICAL_JSON_VERSION = "1.0"

ROOT_OBJECTS_KEY = "objects"
ROOT_VERSION_KEY = "version"

IDENTITY_KEY = "identity"
STRUCTURE_KEY = "structure"

IDENTITY_FIELDS = frozenset(
    {
        "id",
        "type",
        "name",
    }
)

OBJECT_FIELDS = frozenset(
    {
        IDENTITY_KEY,
        STRUCTURE_KEY,
    }
)

RELATION_PARTICIPANTS_KEY = "participants"
RELATION_TYPE_KEY = "relation_type"


# ============================================================================
# Internal Helpers
# ============================================================================


def _jsonify(value: Any) -> Any:
    """
    Convert immutable canonical values into JSON-compatible values.

    The conversion is recursive.

    MappingProxyType -> dict
    tuple            -> list
    frozenset        -> sorted list

    Primitive JSON values are returned unchanged.
    """

    if isinstance(value, MappingProxyType):
        value = dict(value)

    if isinstance(value, dict):
        return {key: _jsonify(val) for key, val in value.items()}

    if isinstance(value, tuple):
        return [_jsonify(item) for item in value]

    if isinstance(value, frozenset):
        return sorted(_jsonify(item) for item in value)

    return value


# ============================================================================
# Exceptions
# ============================================================================


class SerializationError(Exception):
    """Raised when canonical serialization cannot be parsed."""


# ============================================================================
# Canonical Deserializer
# ============================================================================


class CanonicalDeserializer:
    """
    Canonical JSON deserializer.

    Converts canonical JSON into a KnowledgeStructure while preserving
    canonical semantics.
    """

    # ---------------------------------------------------------------------

    def deserialize(self, source: str | dict[str, Any]) -> KnowledgeStructure:
        """
        Deserialize canonical JSON into a KnowledgeStructure.
        """

        data = self._load_json(source)

        if not isinstance(data, dict):
            raise SerializationError("Top-level JSON value must be an object.")

        self._validate_root(data)

        objects: list[KnowledgeObject] = []
        seen: set[str] = set()

        for raw_object in data[ROOT_OBJECTS_KEY]:
            obj = self._parse_object(raw_object)

            oid = obj.identity.id

            if oid in seen:
                raise SerializationError(f"Duplicate canonical identity: {oid!r}")

            seen.add(oid)
            objects.append(obj)

        return KnowledgeStructure(objects)

    # ---------------------------------------------------------------------

    def _load_json(
        self,
        source: str | dict[str, Any],
    ) -> dict[str, Any]:

        if not isinstance(source, (str, dict)):
            raise SerializationError(
                "Source must be a JSON string or decoded JSON object."
            )

        if isinstance(source, dict):
            return source

        try:
            data = json.loads(source)
        except json.JSONDecodeError as exc:
            raise SerializationError(f"Invalid JSON: {exc}") from exc

        if not isinstance(data, dict):
            raise SerializationError("Top-level JSON value must be an object.")
        return data

    # ---------------------------------------------------------------------

    def _validate_root(
        self,
        data: dict[str, Any],
    ) -> None:

        if ROOT_OBJECTS_KEY not in data:
            raise SerializationError("Missing top-level 'objects' array.")

        objects = data[ROOT_OBJECTS_KEY]

        if not isinstance(objects, list):
            raise SerializationError("'objects' must be a JSON array.")

        version = data.get(ROOT_VERSION_KEY)

        if version is not None:
            if version != CANONICAL_JSON_VERSION:
                raise SerializationError(
                    f"Unsupported serialization version {version!r}."
                )

    # ---------------------------------------------------------------------

    def _parse_identity(
        self,
        data: Any,
    ) -> ObjectIdentity:

        if not isinstance(data, dict):
            raise SerializationError("Object identity must be an object.")

        unknown = set(data.keys()) - IDENTITY_FIELDS

        if unknown:
            raise SerializationError(
                "Unknown identity field(s): " + ", ".join(sorted(unknown))
            )

        try:
            oid = data["id"]
            typ = data["type"]
            name = data["name"]

        except KeyError as exc:
            raise SerializationError(
                f"Missing identity field {exc.args[0]!r}."
            ) from exc

        if not all(isinstance(x, str) for x in (oid, typ, name)):
            raise SerializationError("Identity fields must all be strings.")

        return ObjectIdentity(
            id=oid,
            type=typ,
            name=name,
        )

    # ---------------------------------------------------------------------

    def _parse_object(
        self,
        data: Any,
    ) -> KnowledgeObject:

        if not isinstance(data, dict):
            raise SerializationError(
                "Each object must be represented by a JSON object."
            )

        unknown = set(data.keys()) - OBJECT_FIELDS

        if unknown:
            raise SerializationError(
                "Unknown object field(s): " + ", ".join(sorted(unknown))
            )

        if IDENTITY_KEY not in data:
            raise SerializationError("Missing object identity.")

        identity = self._parse_identity(data[IDENTITY_KEY])

        structure = data.get(
            STRUCTURE_KEY,
            {},
        )

        if not isinstance(structure, dict):
            raise SerializationError("Object structure must be an object.")

        # -------------------------------------------------------------
        # Canonical Relation
        # -------------------------------------------------------------

        is_relation = (
            RELATION_PARTICIPANTS_KEY in structure and RELATION_TYPE_KEY in structure
        )

        if is_relation:
            participants = structure.get(RELATION_PARTICIPANTS_KEY)

            relation_type = structure.get(RELATION_TYPE_KEY)

            if not isinstance(participants, list):
                raise SerializationError("Relation participants must be a list.")

            if len(participants) < 2:
                raise SerializationError(
                    "CanonicalRelation requires at least two participants."
                )

            if not all(isinstance(participant, str) for participant in participants):
                raise SerializationError("Relation participants must all be strings.")

            if not isinstance(relation_type, str):
                raise SerializationError("Relation type must be a string.")

            if not relation_type.strip():
                raise SerializationError("Relation type cannot be empty.")

            return CanonicalRelation(
                identity=identity,
                participants=participants,
                relation_type=relation_type,
                structure=structure,
            )

        # -------------------------------------------------------------
        # Ordinary Knowledge Object
        # -------------------------------------------------------------

        return KnowledgeObject(
            identity=identity,
            structure=structure,
        )


# ============================================================================
# Canonical Serializer
# ============================================================================


class CanonicalSerializer:
    """
    Canonical JSON serializer.

    Converts a KnowledgeStructure into the canonical JSON
    representation defined by CKS-003.
    """

    # ---------------------------------------------------------------------

    def serialize(
        self,
        structure: KnowledgeStructure,
    ) -> str:

        data = self.serialize_structure(structure)

        return json.dumps(
            data,
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
        )

    def roundtrip(
        self,
        structure: KnowledgeStructure,
    ) -> KnowledgeStructure:
        """
        Serialize and immediately deserialize a KnowledgeStructure.

        Useful for conformance testing.
        """

        return _deserializer.deserialize(self.serialize(structure))

    # ---------------------------------------------------------------------

    def serialize_structure(
        self,
        structure: KnowledgeStructure,
    ) -> dict[str, Any]:

        return {
            ROOT_VERSION_KEY: CANONICAL_JSON_VERSION,
            ROOT_OBJECTS_KEY: [self._encode_object(obj) for obj in structure.objects],
        }

    # ---------------------------------------------------------------------

    def _encode_object(
        self,
        obj: KnowledgeObject,
    ) -> dict[str, Any]:

        identity = {
            "id": obj.identity.id,
            "type": obj.identity.type,
            "name": obj.identity.name,
        }

        structure = _jsonify(obj.structure)

        return {
            IDENTITY_KEY: identity,
            STRUCTURE_KEY: structure,
        }


# ============================================================================
# Singleton Instances
# ============================================================================

#
# Reference implementation instances.
#
# These objects are stateless and therefore safe to reuse throughout the
# lifetime of the process.
#

_deserializer = CanonicalDeserializer()
_serializer = CanonicalSerializer()


# ============================================================================
# Public API (CKS-007)
# ============================================================================


def parse(source: str | dict[str, Any]) -> KnowledgeStructure:
    """
    Parse a canonical JSON representation into a KnowledgeStructure.

    This function implements the canonical Parse operation defined by
    CKS-007.

    Parameters
    ----------
    source:
        Canonical JSON string or an already decoded JSON object.

    Returns
    -------
    KnowledgeStructure

    Raises
    ------
    SerializationError
        If the input cannot be interpreted as canonical serialization.
    """
    return _deserializer.deserialize(source)


def serialize(structure: KnowledgeStructure) -> str:
    """
    Serialize a KnowledgeStructure into canonical JSON.

    This function implements the canonical Serialize operation defined
    by CKS-007.

    The resulting serialization satisfies the canonical round-trip
    property

        parse(serialize(S)) ≡ S

    where ≡ denotes Structural Equivalence (CKS-001, Section 15).
    """
    return _serializer.serialize(structure)


# ============================================================================
# Public Symbols
# ============================================================================

__all__ = [
    "SerializationError",
    "CanonicalDeserializer",
    "CanonicalSerializer",
    "parse",
    "serialize",
]
