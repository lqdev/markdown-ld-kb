"""Golden test: end-to-end extraction on the sample article."""

import json
from pathlib import Path

from tools.chunker import chunk_document, parse_frontmatter, doc_id_from_path


SAMPLE_ARTICLE_PATH = "content/2026/04/what-is-a-knowledge-graph.md"


def test_sample_article_chunks():
    """Verify the sample article chunks correctly."""
    article_path = Path(SAMPLE_ARTICLE_PATH)
    if not article_path.exists():
        import pytest
        pytest.skip("Sample article not found")

    content = article_path.read_text(encoding="utf-8")
    meta, body = parse_frontmatter(content)

    assert meta.get("title") == "What is a Knowledge Graph?"
    assert "tags" in meta
    assert "entity_hints" in meta

    doc_id = doc_id_from_path(SAMPLE_ARTICLE_PATH)
    chunks = chunk_document(content, doc_id)

    assert len(chunks) >= 1, f"Expected at least 1 chunk, got {len(chunks)}"

    # Every chunk should have a stable ID
    ids = [c.chunk_id for c in chunks]
    assert len(ids) == len(set(ids)), "Chunk IDs should be unique"

    # Re-chunking should produce the same IDs
    chunks2 = chunk_document(content, doc_id)
    ids2 = [c.chunk_id for c in chunks2]
    assert ids == ids2, "Chunking should be deterministic"


def test_sample_article_doc_id():
    """Verify doc_id derivation from path."""
    doc_id = doc_id_from_path(SAMPLE_ARTICLE_PATH)
    assert "2026/04/what-is-a-knowledge-graph" in doc_id
