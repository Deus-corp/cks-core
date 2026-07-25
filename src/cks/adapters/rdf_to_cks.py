"""
CKS Adapter — RDF to CKS Converter.

Converts an RDF graph (RDF/XML, Turtle, etc.) into a Canonical Knowledge Structure.
"""

from __future__ import annotations


import rdflib

from ..core import (
    CanonicalRelation,
    KnowledgeObject,
    KnowledgeStructure,
    ObjectIdentity,
)


class RdfToCksConverter:
    """Transform an RDF graph into a KnowledgeStructure."""

    def __init__(self, rdf_data: str, format: str = "turtle") -> None:
        self._graph = rdflib.Graph()
        self._graph.parse(data=rdf_data, format=format)

    def convert(self) -> KnowledgeStructure:
        """Run the conversion and return a KnowledgeStructure."""
        objects: list[KnowledgeObject] = []
        seen_ids: set[str] = set()
        relations: list[CanonicalRelation] = []

        # 1. Convert every subject to a KnowledgeObject
        for subject in self._graph.subjects():
            oid = str(subject)
            if oid not in seen_ids:
                seen_ids.add(oid)
                objects.append(self._subject_to_ko(subject))

        # 2. Convert triples
        for s, p, o in self._graph:
            if isinstance(o, rdflib.Literal):
                # Skip literal objects – they are not KnowledgeObjects
                continue

            subj_id = str(s)
            pred = str(p)
            obj_id = str(o)

            # Ensure participants exist
            for pid in (subj_id, obj_id):
                if pid not in seen_ids:
                    seen_ids.add(pid)
                    objects.append(
                        KnowledgeObject(
                            identity=ObjectIdentity(id=pid, type="Entity", name=pid),
                            structure={},
                        )
                    )

            rel_id = f"{subj_id}-{pred}-{obj_id}"
            relation = CanonicalRelation(
                identity=ObjectIdentity(id=rel_id, type="Relation", name=pred),
                participants=[subj_id, obj_id],
                relation_type=pred,
            )
            relations.append(relation)

        all_objects = objects + list(relations)
        return KnowledgeStructure(all_objects)

    def _subject_to_ko(self, subject: rdflib.term.Node) -> KnowledgeObject:
        oid = str(subject)
        # Try to get a human-readable label
        label = None
        for _, _, lbl in self._graph.triples((subject, rdflib.RDFS.label, None)):
            label = str(lbl)
            break
        name = label or oid

        # Try to get a type
        otype = "Entity"
        for _, _, t in self._graph.triples((subject, rdflib.RDF.type, None)):
            otype = str(t).split("#")[-1] if "#" in str(t) else str(t)
            break

        identity = ObjectIdentity(id=oid, type=otype, name=name)
        return KnowledgeObject(identity=identity, structure={})
