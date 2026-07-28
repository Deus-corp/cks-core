"""Tests for CKS adapters."""

from cks.adapters.jsonld_to_cks import JsonLdToCksConverter
from cks.validator import validate

from cks.adapters.rdf_to_cks import RdfToCksConverter
from cks.adapters.cks_to_jsonld import CksToJsonLdConverter
from cks.adapters.cks_to_rdf import CksToRdfConverter
from cks.serialization import parse
from pathlib import Path


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