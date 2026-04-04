# Markdown-LD Knowledge Bank

A Git-based knowledge bank where human-authored Markdown articles are processed by an LLM CI pipeline to extract Linked Data (RDF/JSON-LD), served as static content on Azure Static Web Apps, with a serverless SPARQL endpoint.

## Architecture

```
content/*.md → GitHub Actions → LLM (GitHub Models) → graph/*.jsonld + *.ttl
                                                         ↓
                                                  Azure Static Web Apps
                                                    ├── Static site
                                                    ├── Graph files
                                                    └── SPARQL API (RDFLib)
```

## Quick Start

### Prerequisites

- Python 3.11+
- Git
- Azure CLI (for deployment)

### Local Development

```bash
# Install dependencies
pip install -r tools/requirements.txt

# Run tests
python -m pytest tests/ -v

# Dry run (chunk only, no LLM)
python -m tools.kg_build --dry-run

# Full build (requires GITHUB_TOKEN)
export GITHUB_TOKEN=your_token
python -m tools.kg_build --repo-root . --base-url https://example.com
```

### Writing Articles

Create Markdown files in `content/` with YAML frontmatter:

```markdown
---
title: "Your Article Title"
date_published: "2026-04-15"
tags:
  - knowledge-graphs
  - rdf
entity_hints:
  - label: "RDF"
    type: "schema:Thing"
    sameAs: "https://www.wikidata.org/entity/Q54872"
---

# Your Content Here

Write naturally. The LLM pipeline extracts entities and relationships.
Use [[wikilinks]] to link between articles.
```

### Example SPARQL Queries

**Find all entities mentioned in an article:**
```sparql
PREFIX schema: <https://schema.org/>
SELECT ?entity ?name WHERE {
  <https://example.com/2026/04/what-is-a-knowledge-graph/> schema:mentions ?entity .
  ?entity schema:name ?name .
}
```

**Find all articles about a topic:**
```sparql
PREFIX schema: <https://schema.org/>
SELECT ?article ?title WHERE {
  ?article a schema:Article ;
           schema:mentions <https://example.com/id/knowledge-graph> ;
           schema:name ?title .
}
```

**Find connections between entities:**
```sparql
PREFIX schema: <https://schema.org/>
SELECT ?subject ?predicate ?object WHERE {
  ?subject ?predicate ?object .
  FILTER(?predicate != rdf:type)
}
LIMIT 50
```

## Project Structure

```
├── content/          # Markdown articles (human-authored)
├── ontology/         # JSON-LD context, vocabulary, SHACL shapes
├── tools/            # Extraction pipeline (chunker, LLM client, post-processor)
├── graph/            # Generated artifacts (committed by CI)
│   ├── articles/     # Per-article JSON-LD and Turtle
│   ├── views/        # Precomputed JSON views
│   ├── cache/        # Per-chunk extraction cache
│   └── manifest.json # Build metadata
├── api/              # Azure Function (SPARQL endpoint)
├── app/              # Static web app
├── tests/            # Test suite
└── .github/workflows/
    ├── kg-build.yml  # KG extraction pipeline
    └── deploy-swa.yml # Azure SWA deployment
```

## Key Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| LLM Provider | GitHub Models (free) | Zero cost, GITHUB_TOKEN auth |
| LLM Model | `openai/gpt-4o-mini` | Best quality/limit ratio (150 req/day) |
| SPARQL Engine | RDFLib | Pure Python, small footprint, built-in JSON-LD |
| Validation | pySHACL | Standard W3C SHACL, works with RDFLib |
| Batching | 3-5 chunks/request | Stay under 8K input token limit |

## Rate Limits

GitHub Models free tier (GPT-4o-mini): 150 requests/day, 8K input tokens.
The pipeline batches 3-5 chunks per request and caches results to stay within limits.

## License

MIT
