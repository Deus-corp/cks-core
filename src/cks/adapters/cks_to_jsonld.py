"""
CKS Adapter — CKS to JSON‑LD Converter.

Converts a Canonical Knowledge Structure into a JSON‑LD document.
"""

from __future__ import annotations

from typing import Any

from ..core import CanonicalRelation, KnowledgeStructure


class CksToJsonLdConverter:
    """Transform a KnowledgeStructure into a JSON‑LD document."""

    def __init__(self, structure: KnowledgeStructure) -> None:
        self._structure = structure

    def convert(self) -> dict[str, Any]:
        """Run the conversion and return a JSON‑LD dictionary."""
        graph: list[dict[str, Any]] = []

        # 1. Convert every KnowledgeObject to a JSON‑LD entity
        for obj in self._structure.objects:
            if isinstance(obj, CanonicalRelation):
                continue  # handled separately
            entity: dict[str, Any] = {
                "@id": obj.identity.id,
                "@type": obj.identity.type,
                "name": obj.identity.name,
            }
            # Add remaining structure fields
            for key, value in obj.structure.items():
                if key not in ("participants", "relation_type"):
                    entity[key] = value
            graph.append(entity)

        # 2. Convert every CanonicalRelation to JSON‑LD properties
        for rel in self._structure.relations():
            # Find the subject entity and add the relation as a property
            subj_id = rel.participants[0]
            obj_id = rel.participants[1] if len(rel.participants) > 1 else None
            if obj_id is None:
                continue

            # Locate the subject entity in the graph
            for entity in graph:
                if entity["@id"] == subj_id:
                    if rel.relation_type not in entity:
                        entity[rel.relation_type] = []
                    entity[rel.relation_type].append({"@id": obj_id})
                    break
            else:
                # Subject not found — create a minimal entity
                graph.append(
                    {
                        "@id": subj_id,
                        "@type": "Entity",
                        rel.relation_type: [{"@id": obj_id}],
                    }
                )

        return {"@graph": graph}
