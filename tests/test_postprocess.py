"""Tests for post-processing: canonicalization, dedup, serialization."""

from tools.postprocess import (
    slugify,
    entity_id,
    canonicalize_entities,
    deduplicate_assertions,
    build_jsonld,
    build_turtle,
)


def test_slugify_basic():
    assert slugify("JSON-LD") == "json-ld"
    assert slugify("Hello World") == "hello-world"
    assert slugify("  spaces  ") == "spaces"


def test_slugify_special_chars():
    assert slugify("C++ Programming") == "c-programming"
    assert slugify("schema.org") == "schemaorg"
    assert slugify("RDF/XML") == "rdfxml"


def test_slugify_numbers():
    assert slugify("Web 3.0") == "web-30"
    assert slugify("Python 3.11") == "python-311"


def test_entity_id():
    result = entity_id("Tim Berners-Lee")
    assert result == "https://example.com/id/tim-berners-lee"


def test_entity_id_custom_base():
    result = entity_id("Test", base_url="https://kb.example.com")
    assert result == "https://kb.example.com/id/test"


def test_canonicalize_entities_merge_duplicates():
    entities = [
        {"id": "1", "type": "schema:Thing", "label": "Python", "sameAs": []},
        {"id": "2", "type": "schema:SoftwareApplication", "label": "Python", "sameAs": ["https://www.wikidata.org/entity/Q28865"]},
    ]
    result = canonicalize_entities(entities)
    assert len(result) == 1
    assert result[0]["type"] == "schema:SoftwareApplication"  # Higher priority
    assert "https://www.wikidata.org/entity/Q28865" in result[0]["sameAs"]


def test_canonicalize_entities_no_duplicates():
    entities = [
        {"id": "1", "type": "schema:Person", "label": "Alice"},
        {"id": "2", "type": "schema:Organization", "label": "Acme Corp"},
    ]
    result = canonicalize_entities(entities)
    assert len(result) == 2


def test_deduplicate_assertions_keeps_highest_confidence():
    assertions = [
        {"s": "a", "p": "schema:mentions", "o": "b", "confidence": 0.7},
        {"s": "a", "p": "schema:mentions", "o": "b", "confidence": 0.9},
    ]
    result = deduplicate_assertions(assertions)
    assert len(result) == 1
    assert result[0]["confidence"] == 0.9


def test_deduplicate_assertions_different_triples():
    assertions = [
        {"s": "a", "p": "schema:mentions", "o": "b", "confidence": 0.9},
        {"s": "a", "p": "schema:creator", "o": "c", "confidence": 0.8},
    ]
    result = deduplicate_assertions(assertions)
    assert len(result) == 2


def test_build_jsonld_structure():
    meta = {"title": "Test Article", "date_published": "2026-04-01", "tags": ["rdf"]}
    entities = [
        {"id": "https://example.com/id/rdf", "type": "schema:Thing", "label": "RDF", "sameAs": []},
    ]
    assertions = [
        {"s": "https://example.com/test/", "p": "schema:mentions", "o": "https://example.com/id/rdf", "confidence": 0.85},
    ]

    result = build_jsonld("https://example.com/test/", meta, entities, assertions)
    assert "@context" in result
    assert "@graph" in result
    assert len(result["@graph"]) >= 2  # article + entity + assertion


def test_build_turtle_structure():
    meta = {"title": "Test Article", "date_published": "2026-04-01"}
    entities = [
        {"id": "https://example.com/id/rdf", "type": "schema:Thing", "label": "RDF", "sameAs": []},
    ]
    assertions = [
        {"s": "https://example.com/test/", "p": "schema:mentions", "o": "https://example.com/id/rdf"},
    ]

    result = build_turtle("https://example.com/test/", meta, entities, assertions)
    assert "@prefix schema:" in result
    assert "schema:Article" in result
    assert "schema:mentions" in result


def test_build_turtle_escaping():
    meta = {"title": 'Article with "quotes"', "date_published": "2026-04-01"}
    result = build_turtle("https://example.com/t/", meta, [], [])
    assert '\\"quotes\\"' in result
