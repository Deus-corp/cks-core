"""Tests for CKS adapters."""

from pathlib import Path

import pytest

from cks.adapters.cks_to_jsonld import CksToJsonLdConverter
from cks.adapters.cks_to_rdf import CksToRdfConverter
from cks.adapters.jsonld_to_cks import JsonLdToCksConverter
from cks.adapters.rdf_to_cks import RdfConversionError, RdfToCksConverter
from cks.serialization import parse
from cks.validator import validate


def test_jsonld_conversion():
    jsonld = {
        "@graph": [
            {"@id": "urn:person:1", "@type": "Person", "name": "Alice"},
            {"@id": "urn:person:2", "@type": "Person", "name": "Bob"},
            {
                "@id": "urn:person:1",
                "knows": [{"@id": "urn:person:2"}],
            },
        ]
    }
    converter = JsonLdToCksConverter(jsonld)
    structure = converter.convert()
    assert len(structure.objects) == 3  # 2 entities + 1 relation

    result = validate(structure)
    assert result.is_valid


def test_rdf_conversion():
    turtle_data = """
@prefix schema: <http://schema.org/> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .

<urn:person:1> a schema:Person ;
    schema:name "Alice" ;
    schema:knows <urn:person:2> .

<urn:person:2> a schema:Person ;
    schema:name "Bob" .
"""
    converter = RdfToCksConverter(turtle_data, format="turtle")
    structure = converter.convert()
    assert len(structure.objects) == 6  # entities + types + relations
    result = validate(structure)
    assert result.is_valid

def test_cks_to_jsonld():
    structure = parse(Path("examples/corpus/valid_theory_example.json").read_text())
    converter = CksToJsonLdConverter(structure)
    result = converter.convert()
    assert "@graph" in result
    assert len(result["@graph"]) > 0


def test_cks_to_rdf():
    structure = parse(Path("examples/corpus/valid_theory_example.json").read_text())
    converter = CksToRdfConverter(structure)
    graph = converter.convert()
    assert len(graph) > 0
    assert converter.to_turtle()
    assert converter.to_rdfxml()


# ---------------------------------------------------------------------------
# RDF/XML DOCTYPE hardening (entity-expansion / "billion laughs" DoS)
# ---------------------------------------------------------------------------


def test_rdf_xml_rejects_doctype_entity_expansion():
    """A DOCTYPE with self-referencing entities must be rejected outright,
    not expanded -- expanding it is what makes the "billion laughs"
    attack possible."""
    payload = """<?xml version="1.0"?>
<!DOCTYPE rdf:RDF [
  <!ENTITY a "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa">
  <!ENTITY b "&a;&a;&a;&a;&a;&a;&a;&a;&a;&a;">
]>
<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"
         xmlns:rdfs="http://www.w3.org/2000/01/rdf-schema#">
  <rdf:Description rdf:about="http://example.org/thing">
    <rdfs:label>&b;</rdfs:label>
  </rdf:Description>
</rdf:RDF>
"""
    with pytest.raises(RdfConversionError, match="DOCTYPE"):
        RdfToCksConverter(payload, format="xml")


def test_rdf_xml_rejects_external_entity_doctype():
    """A DOCTYPE referencing an external/local resource is rejected
    for the same reason, regardless of whether the underlying XML
    parser would have resolved it."""
    payload = """<?xml version="1.0"?>
<!DOCTYPE rdf:RDF [ <!ENTITY xxe SYSTEM "file:///etc/hostname"> ]>
<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"
         xmlns:rdfs="http://www.w3.org/2000/01/rdf-schema#">
  <rdf:Description rdf:about="http://example.org/thing">
    <rdfs:label>&xxe;</rdfs:label>
  </rdf:Description>
</rdf:RDF>
"""
    with pytest.raises(RdfConversionError, match="DOCTYPE"):
        RdfToCksConverter(payload, format="xml")


def test_rdf_xml_without_doctype_still_works():
    """Ordinary RDF/XML with no DOCTYPE is unaffected by the hardening."""
    payload = """<?xml version="1.0"?>
<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"
         xmlns:rdfs="http://www.w3.org/2000/01/rdf-schema#">
  <rdf:Description rdf:about="http://example.org/thing">
    <rdfs:label>Hello</rdfs:label>
  </rdf:Description>
</rdf:RDF>
"""
    structure = RdfToCksConverter(payload, format="xml").convert()
    assert len(structure.objects) == 1


def test_turtle_with_doctype_like_text_is_unaffected():
    """The DOCTYPE check only applies to XML-based formats -- Turtle
    input is never scanned for it, so a literal containing the
    substring is not falsely rejected."""
    turtle_data = '@prefix ex: <http://example.org/> . ex:a ex:label "<!DOCTYPE html>" .'
    structure = RdfToCksConverter(turtle_data, format="turtle").convert()
    assert len(structure.objects) >= 1


def test_rdf_malformed_input_raises_clean_error():
    """Malformed RDF input of any kind raises RdfConversionError (a
    ValueError subclass) instead of leaking the underlying parser's
    raw exception type."""
    with pytest.raises(RdfConversionError):
        RdfToCksConverter("not valid turtle {{{ ]]] ???", format="turtle")