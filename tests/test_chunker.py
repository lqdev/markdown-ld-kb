"""Tests for the Markdown chunker."""

from tools.chunker import (
    chunk_document,
    parse_frontmatter,
    doc_id_from_path,
    _compute_chunk_id,
    _estimate_tokens,
    _normalize_text,
)


SAMPLE_DOC = """---
title: "Test Article"
date_published: "2026-04-01"
tags:
  - testing
  - rdf
---

# Introduction

This is the introduction paragraph. It contains some basic information
about knowledge graphs and linked data.

## Key Concepts

Knowledge graphs represent information as a network of entities and
relationships. They use standards like RDF and JSON-LD for interoperability.

## Implementation

The implementation uses Python with RDFLib for graph processing
and pySHACL for validation of the extracted triples.
"""


def test_parse_frontmatter():
    meta, body = parse_frontmatter(SAMPLE_DOC)
    assert meta["title"] == "Test Article"
    assert meta["date_published"] == "2026-04-01"
    assert "testing" in meta["tags"]
    assert "# Introduction" in body


def test_parse_frontmatter_no_frontmatter():
    meta, body = parse_frontmatter("# Just a heading\n\nSome text.")
    assert meta == {}
    assert "Just a heading" in body


def test_chunk_id_determinism():
    """Same text must produce the same chunk ID every time."""
    text = "This is a test sentence for chunking."
    id1 = _compute_chunk_id(text)
    id2 = _compute_chunk_id(text)
    assert id1 == id2
    assert len(id1) == 16  # sha256[:16]


def test_chunk_id_whitespace_normalization():
    """Different whitespace should produce the same chunk ID."""
    id1 = _compute_chunk_id("hello   world")
    id2 = _compute_chunk_id("hello world")
    id3 = _compute_chunk_id("hello\n\nworld")
    assert id1 == id2 == id3


def test_chunk_document_produces_chunks():
    chunks = chunk_document(SAMPLE_DOC, "https://example.com/test/")
    assert len(chunks) > 0
    for chunk in chunks:
        assert chunk.doc_id == "https://example.com/test/"
        assert chunk.chunk_id  # non-empty
        assert chunk.text.strip()  # non-empty text


def test_chunk_document_respects_token_target():
    """No chunk should drastically exceed the token target."""
    chunks = chunk_document(SAMPLE_DOC, "test", token_target=100)
    for chunk in chunks:
        tokens = _estimate_tokens(chunk.text)
        # Allow some overshoot since we don't split mid-section
        assert tokens < 500, f"Chunk too large: {tokens} tokens"


def test_chunk_to_dict():
    chunks = chunk_document(SAMPLE_DOC, "test")
    d = chunks[0].to_dict()
    assert "doc_id" in d
    assert "chunk_id" in d
    assert "text" in d
    assert "heading_path" in d


def test_doc_id_from_path():
    result = doc_id_from_path("content/2026/04/my-article.md")
    assert "2026/04/my-article" in result
    assert result.endswith("/")


def test_doc_id_from_path_with_base_url():
    result = doc_id_from_path(
        "content/2026/04/test.md", base_url="https://kb.example.com"
    )
    assert result.startswith("https://kb.example.com/")


def test_estimate_tokens():
    # Rough: 4 chars per token
    assert _estimate_tokens("a" * 400) == 100
    assert _estimate_tokens("") == 0


def test_normalize_text():
    assert _normalize_text("  hello   world  ") == "hello world"
    assert _normalize_text("a\n\nb\tc") == "a b c"


def test_empty_document():
    chunks = chunk_document("", "test")
    assert chunks == []


def test_frontmatter_only():
    doc = "---\ntitle: Test\n---\n"
    chunks = chunk_document(doc, "test")
    assert chunks == []
