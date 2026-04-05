"""Tests for the NL-to-SPARQL translation module."""

import sys
import os
from unittest.mock import patch, MagicMock

import pytest

# Add api/ to path so we can import the module directly
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "api"))

from nl_to_sparql import (
    validate_sparql,
    enforce_safety,
    translate,
    _strip_code_fences,
    _normalize_question,
    _query_cache,
    SYSTEM_PROMPT,
)


class TestValidateSparql:
    """Test SPARQL syntax validation."""

    def test_valid_select(self):
        q = "PREFIX schema: <https://schema.org/> SELECT ?s WHERE { ?s a schema:Article }"
        is_valid, err = validate_sparql(q)
        assert is_valid
        assert err == ""

    def test_valid_ask(self):
        q = "PREFIX schema: <https://schema.org/> ASK { ?s a schema:Article }"
        is_valid, err = validate_sparql(q)
        assert is_valid
        assert err == ""

    def test_invalid_syntax(self):
        q = "SELEC ?s WHERE { ?s ?p ?o }"
        is_valid, err = validate_sparql(q)
        assert not is_valid
        assert err != ""

    def test_empty_query(self):
        is_valid, err = validate_sparql("")
        assert not is_valid

    def test_valid_with_filter(self):
        q = (
            "PREFIX schema: <https://schema.org/> "
            "SELECT ?name WHERE { ?e schema:name ?name . "
            'FILTER(LCASE(STR(?name)) = "sparql") }'
        )
        is_valid, err = validate_sparql(q)
        assert is_valid


class TestEnforceSafety:
    """Test safety enforcement on SPARQL queries."""

    def test_blocks_insert(self):
        is_safe, _, err = enforce_safety("INSERT DATA { <a> <b> <c> }")
        assert not is_safe
        assert "INSERT" in err

    def test_blocks_delete(self):
        is_safe, _, err = enforce_safety("DELETE WHERE { ?s ?p ?o }")
        assert not is_safe
        assert "DELETE" in err

    def test_blocks_drop(self):
        is_safe, _, err = enforce_safety("DROP GRAPH <http://example.com>")
        assert not is_safe
        assert "DROP" in err

    def test_allows_select(self):
        q = "SELECT ?s WHERE { ?s ?p ?o } LIMIT 10"
        is_safe, sanitized, err = enforce_safety(q)
        assert is_safe
        assert err == ""

    def test_injects_limit_when_missing(self):
        q = "SELECT ?s WHERE { ?s ?p ?o }"
        is_safe, sanitized, err = enforce_safety(q)
        assert is_safe
        assert "LIMIT 100" in sanitized

    def test_preserves_existing_limit(self):
        q = "SELECT ?s WHERE { ?s ?p ?o } LIMIT 50"
        is_safe, sanitized, err = enforce_safety(q)
        assert is_safe
        assert "LIMIT 100" not in sanitized
        assert "LIMIT 50" in sanitized

    def test_allows_ask(self):
        q = "ASK { ?s ?p ?o }"
        is_safe, sanitized, err = enforce_safety(q)
        assert is_safe
        # ASK queries don't need LIMIT
        assert "LIMIT" not in sanitized


class TestStripCodeFences:
    """Test markdown code fence stripping."""

    def test_strips_sparql_fence(self):
        text = "```sparql\nSELECT ?s WHERE { ?s ?p ?o }\n```"
        assert _strip_code_fences(text) == "SELECT ?s WHERE { ?s ?p ?o }"

    def test_strips_generic_fence(self):
        text = "```\nSELECT ?s WHERE { ?s ?p ?o }\n```"
        assert _strip_code_fences(text) == "SELECT ?s WHERE { ?s ?p ?o }"

    def test_no_fences_passthrough(self):
        text = "SELECT ?s WHERE { ?s ?p ?o }"
        assert _strip_code_fences(text) == text

    def test_strips_surrounding_whitespace(self):
        text = "  SELECT ?s WHERE { ?s ?p ?o }  "
        assert _strip_code_fences(text) == "SELECT ?s WHERE { ?s ?p ?o }"


class TestNormalizeQuestion:
    """Test question normalization for caching."""

    def test_lowercase(self):
        assert _normalize_question("What Are Articles?") == "what are articles?"

    def test_strips_whitespace(self):
        assert _normalize_question("  hello  ") == "hello"


class TestSystemPrompt:
    """Test that the system prompt contains required schema elements."""

    def test_contains_classes(self):
        for cls in ["schema:Article", "schema:Person", "schema:Organization",
                     "schema:SoftwareApplication", "schema:Thing"]:
            assert cls in SYSTEM_PROMPT, f"Missing class: {cls}"

    def test_contains_properties(self):
        for prop in ["schema:name", "schema:mentions", "schema:about",
                      "schema:author", "schema:datePublished", "kb:confidence"]:
            assert prop in SYSTEM_PROMPT, f"Missing property: {prop}"

    def test_contains_prefixes(self):
        for prefix in ["schema:", "kb:", "prov:", "rdf:", "xsd:"]:
            assert prefix in SYSTEM_PROMPT, f"Missing prefix: {prefix}"

    def test_contains_few_shot_examples(self):
        assert "Q:" in SYSTEM_PROMPT
        assert "SELECT" in SYSTEM_PROMPT


class TestTranslate:
    """Test the full translate() function with mocked LLM."""

    @patch("nl_to_sparql._create_client")
    def test_successful_translation(self, mock_create):
        _query_cache.clear()
        mock_client = MagicMock()
        mock_create.return_value = mock_client

        sparql_response = (
            "PREFIX schema: <https://schema.org/>\n"
            "SELECT ?name WHERE { ?e schema:name ?name }\n"
            "LIMIT 100"
        )
        mock_client.chat.completions.create.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content=sparql_response))]
        )

        result, error = translate("What entities exist?")
        assert error is None
        assert "SELECT" in result
        assert "schema:name" in result

    @patch("nl_to_sparql._create_client")
    def test_cannot_answer(self, mock_create):
        _query_cache.clear()
        mock_client = MagicMock()
        mock_create.return_value = mock_client
        mock_client.chat.completions.create.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(
                content="CANNOT_ANSWER: No weather data in the knowledge graph"
            ))]
        )

        result, error = translate("What's the weather?")
        assert result == ""
        assert "CANNOT_ANSWER" in error

    @patch("nl_to_sparql._create_client")
    def test_cache_hit(self, mock_create):
        _query_cache.clear()
        cached_sparql = "SELECT ?s WHERE { ?s ?p ?o } LIMIT 10"
        _query_cache["test question"] = cached_sparql

        result, error = translate("test question")
        assert error is None
        assert result == cached_sparql
        mock_create.assert_not_called()

    @patch("nl_to_sparql._create_client")
    def test_strips_code_fences_from_llm(self, mock_create):
        _query_cache.clear()
        mock_client = MagicMock()
        mock_create.return_value = mock_client

        fenced = (
            "```sparql\n"
            "PREFIX schema: <https://schema.org/>\n"
            "SELECT ?name WHERE { ?e schema:name ?name }\n"
            "LIMIT 100\n"
            "```"
        )
        mock_client.chat.completions.create.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content=fenced))]
        )

        result, error = translate("List entities")
        assert error is None
        assert "```" not in result
        assert "SELECT" in result

    @patch("nl_to_sparql._create_client")
    def test_missing_github_token(self, mock_create):
        _query_cache.clear()
        mock_create.side_effect = ValueError("GITHUB_TOKEN required")

        result, error = translate("anything")
        assert result == ""
        assert "GITHUB_TOKEN" in error

    @patch("nl_to_sparql._create_client")
    def test_retries_on_syntax_error(self, mock_create):
        _query_cache.clear()
        mock_client = MagicMock()
        mock_create.return_value = mock_client

        bad_sparql = "SELEC ?s WHERE { ?s ?p ?o }"
        good_sparql = (
            "PREFIX schema: <https://schema.org/>\n"
            "SELECT ?s WHERE { ?s ?p ?o }\n"
            "LIMIT 100"
        )

        mock_client.chat.completions.create.side_effect = [
            MagicMock(choices=[MagicMock(message=MagicMock(content=bad_sparql))]),
            MagicMock(choices=[MagicMock(message=MagicMock(content=good_sparql))]),
        ]

        result, error = translate("Show me everything")
        assert error is None
        assert "SELECT" in result
        assert mock_client.chat.completions.create.call_count == 2
