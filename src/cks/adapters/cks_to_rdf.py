"""
CKS Adapter — CKS to RDF Converter.

Converts a Canonical Knowledge Structure into an RDF graph
(Turtle or RDF/XML).
"""

from __future__ import annotations


from rdflib import RDF, RDFS, Graph, Literal, URIRef

from ..core import CanonicalRelation, KnowledgeStructure

# Base namespace for CKS entities that don't have an absolute URI.
CKS_NS = "http://cks.org/"


def _to_uri(raw: str) -> URIRef:
    """Return *raw* as an absolute URI, prepending CKS_NS if necessary."""
    if "://" in raw:
        return URIRef(raw)
    return URIRef(CKS_NS + raw)


class CksToRdfConverter:
    """Transform a KnowledgeStructure into an RDF graph."""

    def __init__(self, structure: KnowledgeStructure) -> None:
        self._structure = structure
        self._graph = Graph()

    def convert(self) -> Graph:
        """Run the conversion and return an rdflib Graph."""
        # 1. Convert every KnowledgeObject to an RDF resource
        for obj in self._structure.objects:
            if isinstance(obj, CanonicalRelation):
                continue
            subject = _to_uri(obj.identity.id)
            # Type
            self._graph.add((subject, RDF.type, _to_uri(obj.identity.type)))
            # Name / label
            self._graph.add((subject, RDFS.label, Literal(obj.identity.name)))
            # Additional structure fields
            for key, value in obj.structure.items():
                if key in ("participants", "relation_type"):
                    continue
                if isinstance(value, (str, int, float)):
                    self._graph.add((subject, _to_uri(key), Literal(value)))

        # 2. Convert every CanonicalRelation to RDF triples
        for rel in self._structure.relations():
            subj_id = rel.participants[0]
            obj_id = rel.participants[1] if len(rel.participants) > 1 else None
            if obj_id is None:
                continue
            self._graph.add(
                (_to_uri(subj_id), _to_uri(rel.relation_type), _to_uri(obj_id))
            )

        return self._graph

    def to_turtle(self) -> str:
        """Return the RDF graph serialised as Turtle."""
        return self._graph.serialize(format="turtle")

    def to_rdfxml(self) -> str:
        """Return the RDF graph serialised as RDF/XML."""
        return self._graph.serialize(format="xml")
