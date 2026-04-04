"""Tests for SHACL validation of generated graphs."""

import json
from pathlib import Path

import pytest

try:
    import rdflib
    from rdflib import Graph, Namespace
    HAS_RDFLIB = True
except ImportError:
    HAS_RDFLIB = False

try:
    from pyshacl import validate as shacl_validate
    HAS_PYSHACL = True
except ImportError:
    HAS_PYSHACL = False


SHAPES_PATH = Path("ontology/shapes.ttl")


@pytest.mark.skipif(not HAS_RDFLIB, reason="rdflib not installed")
@pytest.mark.skipif(not HAS_PYSHACL, reason="pyshacl not installed")
class TestShaclValidation:
    """SHACL validation of generated graph artifacts."""

    def _load_shapes(self) -> Graph:
        shapes = Graph()
        shapes.parse(str(SHAPES_PATH), format="turtle")
        return shapes

    def test_shapes_file_loads(self):
        """The SHACL shapes file should parse without errors."""
        shapes = self._load_shapes()
        assert len(shapes) > 0

    def test_valid_article_graph(self):
        """A well-formed article graph should pass SHACL validation."""
        data = Graph()
        data.parse(
            data="""
            @prefix schema: <https://schema.org/> .
            @prefix xsd: <http://www.w3.org/2001/XMLSchema#> .

            <https://example.com/test/> a schema:Article ;
                schema:name "Test Article" ;
                schema:datePublished "2026-04-01"^^xsd:date .

            <https://example.com/id/python> a schema:SoftwareApplication ;
                schema:name "Python" .
            """,
            format="turtle",
        )

        shapes = self._load_shapes()
        conforms, _, report_text = shacl_validate(data, shacl_graph=shapes)
        assert conforms, f"SHACL validation failed:\n{report_text}"

    def test_invalid_article_missing_name(self):
        """An article missing schema:name should fail SHACL validation."""
        data = Graph()
        data.parse(
            data="""
            @prefix schema: <https://schema.org/> .
            @prefix xsd: <http://www.w3.org/2001/XMLSchema#> .

            <https://example.com/test/> a schema:Article ;
                schema:datePublished "2026-04-01"^^xsd:date .
            """,
            format="turtle",
        )

        shapes = self._load_shapes()
        conforms, _, report_text = shacl_validate(data, shacl_graph=shapes)
        assert not conforms, "Should fail: article has no name"
