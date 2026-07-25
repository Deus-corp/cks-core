"""
CKS Adapter — JSON‑LD to CKS Converter.

Converts a JSON‑LD document into a Canonical Knowledge Structure.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from ..core import (
    CanonicalRelation,
    KnowledgeObject,
    KnowledgeStructure,
    ObjectIdentity,
)


class JsonLdToCksConverter:
    """Transform a JSON‑LD document into a KnowledgeStructure."""

    def __init__(self, jsonld_data: Dict[str, Any]) -> None:
        self._data = jsonld_data

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def convert(self) -> KnowledgeStructure:
        """Run the conversion and return a KnowledgeStructure."""
        objects: List[KnowledgeObject] = []

        # 1. Merge entities with the same @id
        merged_entities = self._merge_entities()

        # 2. Convert each merged entity to a KnowledgeObject
        for entity in merged_entities.values():
            objects.append(self._entity_to_ko(entity))

        # 3. Convert relations
        for relation in self._iter_relations():
            objects = objects + [relation]

        return KnowledgeStructure(objects)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _merge_entities(self) -> Dict[str, Dict[str, Any]]:
        """Merge all nodes that share the same @id."""
        merged: Dict[str, Dict[str, Any]] = {}
        for entity in self._iter_entities():
            oid = entity.get("@id", "unknown")
            if oid not in merged:
                merged[oid] = dict(entity)
            else:
                # Merge: later properties override earlier ones
                merged[oid].update(entity)
        return merged

    def _iter_entities(self) -> List[Dict[str, Any]]:
        """Yield every entity described in the JSON‑LD document."""
        graph = self._data.get("@graph")
        if isinstance(graph, list):
            return graph
        if isinstance(self._data, dict):
            return [self._data]
        return []

    def _entity_to_ko(self, entity: Dict[str, Any]) -> KnowledgeObject:
        oid = entity.get("@id", "unknown")
        otype = self._pick_type(entity)
        name = entity.get("name", entity.get("rdfs:label", oid))

        identity = ObjectIdentity(id=oid, type=otype, name=str(name))
        structure = dict(entity)
        return KnowledgeObject(identity=identity, structure=structure)

    @staticmethod
    def _pick_type(entity: Dict[str, Any]) -> str:
        types = entity.get("@type", [])
        if isinstance(types, list) and types:
            return str(types[0])
        if isinstance(types, str):
            return types
        return "Entity"

    def _iter_relations(self) -> List[CanonicalRelation]:
        relations: List[CanonicalRelation] = []
        for entity in self._iter_entities():
            subject_id = entity.get("@id")
            if not subject_id:
                continue
            for predicate, objects in entity.items():
                if predicate in (
                    "@id",
                    "@type",
                    "@context",
                    "@graph",
                    "name",
                    "rdfs:label",
                ):
                    continue
                if not isinstance(objects, list):
                    objects = [objects]
                for obj in objects:
                    obj_id = self._object_to_id(obj)
                    if obj_id is None:
                        continue
                    rel_id = f"{subject_id}-{predicate}-{obj_id}"
                    relation = CanonicalRelation(
                        identity=ObjectIdentity(
                            id=rel_id, type="Relation", name=predicate
                        ),
                        participants=[subject_id, obj_id],
                        relation_type=predicate,
                    )
                    relations.append(relation)
        return relations

    @staticmethod
    def _object_to_id(obj: Any) -> Optional[str]:
        if isinstance(obj, str):
            return obj
        if isinstance(obj, dict):
            return obj.get("@id")
        return None
