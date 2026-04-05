---
name: llm-rdf-extraction
description: Design and iterate on LLM prompts that extract structured RDF (entities and assertions) from natural language text. Covers system prompt architecture, JSON output schema enforcement, few-shot example design, confidence calibration, chunking strategies, and common extraction failure modes. Use when building or tuning an LLM-powered knowledge graph extraction pipeline.
---

# LLM RDF Extraction

Design prompts that reliably extract structured RDF knowledge from natural language text. The extraction pipeline chunks Markdown articles and sends each chunk to an LLM that returns entities and assertions in a strict JSON schema.

## Pipeline Overview

```
Markdown article
  → Parse frontmatter (metadata, entity_hints)
  → Split at H1/H2 headings into chunks (~750 tokens each)
  → For each batch of 3-5 chunks:
      → Send to LLM with system prompt + user message
      → Parse JSON response
      → Cache result per chunk
  → Post-process: canonicalize entities, deduplicate assertions
  → Validate with SHACL
  → Write JSON-LD + Turtle outputs
```

## System Prompt Architecture

The system prompt has five sections. Each is critical:

### 1. Role Declaration

```
You are a deterministic RDF extraction engine. Output MUST be valid JSON
per the schema below. Do not invent facts.
```

**Why:** Anchors the LLM in a strict, non-creative role. "Deterministic" and "do not invent facts" reduce hallucination.

### 2. Ontology Definition

```
ONTOLOGY (use schema.org first; kb: only for extraction metadata):
- Types: schema:Article, schema:Person, schema:Organization,
         schema:SoftwareApplication, schema:CreativeWork, schema:Thing
- Preferred properties: schema:about, schema:mentions, schema:sameAs,
         schema:author, schema:creator, schema:datePublished, schema:dateModified
- Fallback: kb:relatedTo
- Provenance: prov:wasDerivedFrom (use chunk URI)
- Confidence: kb:confidence (0..1)
```

**Why:** Constraining the vocabulary prevents the LLM from inventing predicates. The "use schema.org first" instruction creates a preference hierarchy.

### 3. Extraction Rules

Key rules and their rationale:

| Rule | Rationale |
|------|-----------|
| Only extract explicitly stated or strongly implied facts | Prevents hallucination |
| Prefer schema.org properties over kb:relatedTo | Produces richer, more queryable graphs |
| Every entity must have id, type, label | Ensures well-formed output |
| Use stable slug-based IDs | Enables deduplication across chunks |
| Set confidence based on explicitness | Lets downstream consumers filter by quality |

### 4. Output JSON Schema

```json
{
  "entities": [
    {"id": "...", "type": "schema:Thing", "label": "...", "sameAs": ["..."]}
  ],
  "assertions": [
    {"s": "...", "p": "schema:mentions", "o": "...", "confidence": 0.85, "source": "urn:kb:chunk:..."}
  ]
}
```

**Critical:** Use `response_format: {"type": "json_object"}` in the API call to force JSON output.

### 5. Few-Shot Examples

Include 2-3 examples showing:
- Simple entity extraction
- Relationship extraction with confidence scores
- The `ARTICLE_ID` placeholder pattern

```
TEXT: "Neo4j was created by Emil Eifrem."
OUTPUT:
{"entities":[
 {"id":"https://example.com/id/neo4j","type":"schema:SoftwareApplication","label":"Neo4j"},
 {"id":"https://example.com/id/emil-eifrem","type":"schema:Person","label":"Emil Eifrem"}
],
"assertions":[
 {"s":".../neo4j","p":"schema:creator","o":".../emil-eifrem","confidence":0.92,"source":"urn:kb:chunk:EXAMPLE"}
]}
```

## Confidence Calibration

Teach the LLM a consistent confidence scale:

| Score | Criterion | Example |
|-------|-----------|---------|
| 0.9+ | Directly stated | "X was created by Y" |
| 0.7–0.9 | Strongly implied | "Y, the creator of X, said..." |
| 0.5–0.7 | Weakly implied | "X and Y are in the same domain" |
| < 0.5 | **Do not emit** | Speculative connections |

The 0.5 threshold acts as a quality gate — it's better to miss a weak assertion than pollute the graph with noise.

## Chunking Strategy

The chunker determines extraction quality as much as the prompt does.

### How It Works

1. Parse frontmatter (strip from extraction input)
2. Split body at H1/H2 heading boundaries
3. Pack consecutive sections until reaching ~750 tokens
4. Hash each chunk's content for a stable `chunk_id`

### Why ~750 Tokens?

- **Too small** (< 300): Loses cross-sentence context, entities mentioned once get missed
- **Just right** (~750): Fits multiple paragraphs, each chunk is self-contained
- **Too large** (> 1500): Approaches input limits when batching, LLM attention degrades

### Batching

Send 3-5 chunks per API call to stay under the 8K input token limit (GitHub Models GPT-4o-mini). The user message includes:

```
ARTICLE_ID: {article_id}
--- CHUNK 1 (chunk_id: abc123, source: urn:kb:chunk:{doc_id}:abc123) ---
{chunk text}

--- CHUNK 2 (chunk_id: def456, source: urn:kb:chunk:{doc_id}:def456) ---
{chunk text}
```

## Caching

Cache each chunk's extraction result keyed by `{chunk_id}.{prompt_version}.{model}`. This means:

- Re-running the pipeline on unchanged content is free
- Changing the prompt version invalidates all caches (intentional)
- Changing the model invalidates all caches (intentional)

## Common Failure Modes

### 1. JSON Parse Errors

**Symptom:** LLM returns markdown-fenced JSON or invalid JSON.

**Fix:** Use `response_format: {"type": "json_object"}`. Add a fallback regex to extract JSON from code blocks:
```python
json_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
```

### 2. Hallucinated Predicates

**Symptom:** LLM invents predicates like `schema:uses`, `schema:partOf`.

**Fix:** List available properties explicitly in the system prompt. Add: "Only use properties listed above."

### 3. Missing Entity IDs

**Symptom:** Entities have labels but no `id` field.

**Fix:** Add the ID generation rule with examples to the prompt. Show the exact `{base_url}/id/{slug}` pattern.

### 4. Cross-Chunk Reference Loss

**Symptom:** Entity mentioned in chunk 1 and chunk 3, but chunk 2 creates a duplicate with a different ID.

**Fix:** Post-processing canonicalization merges by slug. The system tolerates this at extraction time and fixes it downstream.

### 5. Over-Extraction

**Symptom:** Every noun becomes an entity.

**Fix:** Add the rule: "Only extract named entities that are specific, identifiable things — not generic concepts like 'data' or 'systems'."

## Prompt Versioning

The prompt file is versioned (`extract_rdf_v1.txt`). When making changes:

1. Create a new version file (`extract_rdf_v2.txt`)
2. Update `PROMPT_VERSION` in `llm_client.py`
3. This automatically invalidates the cache for all chunks
4. Run the pipeline and compare output quality

## Rate Limit Management

GitHub Models free tier: **150 requests/day, 8K input tokens**.

Strategies:
- Batch 3-5 chunks per request (reduces total API calls)
- Cache aggressively (only call LLM for changed/new content)
- Use `git diff` to detect changed files (skip unchanged articles)
- Exponential backoff on `429 Too Many Requests`

## Reference

See [references/prompt-patterns.md](references/prompt-patterns.md) for the complete extraction prompt and iteration patterns.
