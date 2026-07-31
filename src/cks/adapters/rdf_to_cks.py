"""
CKS Adapter — RDF to CKS Converter.

Converts an RDF graph (RDF/XML, Turtle, etc.) into a Canonical Knowledge Structure.
"""

from __future__ import annotations

import re

import rdflib

from ..core import (
    CanonicalRelation,
    KnowledgeObject,
    KnowledgeStructure,
    ObjectIdentity,
)

# ============================================================================
# XML entity-expansion ("billion laughs") hardening
# ============================================================================
#
# rdflib's XML-based RDF formats (RDF/XML, TriX, ...) are parsed via
# Python's stdlib ``xml.sax``, which resolves *internal* DTD general
# entities during parsing. Python's expat backend already refuses to
# fetch *external* entities (``SYSTEM "file://..."`` / ``"http://..."``),
# so classic file-disclosure XXE is not reachable here -- but a DOCTYPE
# whose internal subset defines entities that reference each other
# exponentially is still expanded in full before any CKS-level
# validation ever sees the result: a few hundred bytes of input can
# balloon into gigabytes of text and exhaust memory/CPU.
#
# Legitimate RDF interchange has no need for a DOCTYPE with custom
# entities, so rather than trying to allow "safe" DOCTYPEs, every
# DOCTYPE is rejected outright for the RDF formats that are actually
# XML underneath -- the same posture OWASP and ``defusedxml`` recommend
# for untrusted XML.
_XML_BASED_RDF_FORMATS = frozenset(
    {
        "xml",
        "pretty-xml",
        "application/rdf+xml",
        "trix",
        "application/trix",
    }
)

_DOCTYPE_PATTERN = re.compile(r"<!DOCTYPE", re.IGNORECASE)


class RdfConversionError(ValueError):
    """Raised when RDF input cannot be safely or correctly converted to CKS."""


def _reject_xml_dtd(rdf_data: str, format: str) -> None:
    """Refuse a DOCTYPE declaration in an XML-based RDF serialization.

    Only applies to formats rdflib parses via ``xml.sax`` (see
    ``_XML_BASED_RDF_FORMATS``) -- Turtle/N-Triples/JSON-LD are not
    XML and are left untouched, including any literal text that
    happens to contain the substring ``<!DOCTYPE``.
    """
    if format not in _XML_BASED_RDF_FORMATS:
        return

    if _DOCTYPE_PATTERN.search(rdf_data):
        raise RdfConversionError(
            "Refusing to parse RDF/XML input containing a DOCTYPE "
            "declaration: custom XML entities are not supported and "
            "can be used to exhaust memory/CPU (the 'billion laughs' "
            "attack). Remove the DOCTYPE and inline any entity values "
            "directly."
        )


class RdfToCksConverter:
    """Transform an RDF graph into a KnowledgeStructure."""

    def __init__(self, rdf_data: str, format: str = "turtle") -> None:
        _reject_xml_dtd(rdf_data, format)
        self._graph = rdflib.Graph()
        try:
            self._graph.parse(data=rdf_data, format=format)
        except RdfConversionError:
            raise
        except Exception as exc:
            raise RdfConversionError(
                f"Failed to parse RDF input as {format!r}: {exc}"
            ) from exc

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