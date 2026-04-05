---
name: markdown-ld-authoring
description: Write Markdown articles that produce high-quality Linked Data when processed by an LLM extraction pipeline. Covers YAML frontmatter conventions, entity_hints for Wikidata alignment, wikilink syntax for entity marking, and content structuring patterns that maximize RDF extraction accuracy. Use when creating or editing content for a Markdown-LD knowledge bank.
---

# Markdown-LD Authoring

Write Markdown articles in `content/` that an LLM pipeline will process into RDF/JSON-LD knowledge graphs. Your goal: write naturally readable prose that also produces rich, accurate structured data.

## File Placement

Articles go in `content/` organized by date:

```
content/
└── YYYY/
    └── MM/
        └── slug-title.md
```

The path determines the canonical URL: `content/2026/04/my-article.md` → `https://{base}/2026/04/my-article/`

## Frontmatter Schema

Every article starts with YAML frontmatter between `---` fences:

```yaml
---
title: "What is a Knowledge Graph?"
date_published: "2026-04-04"
date_modified: "2026-04-04"
authors:
  - name: "Author Name"
tags: ["knowledge-graph", "sparql", "linked-data"]
about:
  - "https://schema.org/KnowledgeGraph"
summary: "An introduction to knowledge graphs — what they are and why they matter."
canonical_url: "https://example.com/2026/04/what-is-a-knowledge-graph/"
entity_hints:
  - label: "Knowledge Graph"
    sameAs: "https://www.wikidata.org/wiki/Q33002955"
  - label: "SPARQL"
    sameAs: "https://www.wikidata.org/wiki/Q54872"
  - label: "RDF"
    sameAs: "https://www.wikidata.org/wiki/Q54848"
---
```

### Required Fields

| Field | Type | Purpose |
|-------|------|---------|
| `title` | string | Article title → `schema:name` |
| `date_published` | ISO date | Publication date → `schema:datePublished` |
| `tags` | string[] | Topic tags → `schema:keywords` |

### Recommended Fields

| Field | Type | Purpose |
|-------|------|---------|
| `date_modified` | ISO date | Last edit date → `schema:dateModified` |
| `authors` | object[] | Author names → `schema:author` |
| `summary` | string | Description → `schema:description` |
| `canonical_url` | URL | Overrides the path-derived article ID |
| `about` | URL[] | Schema.org type URIs the article is about |
| `entity_hints` | object[] | Pre-identified entities with Wikidata links |

### Entity Hints

Entity hints are the highest-leverage frontmatter field. They tell the extraction pipeline exactly which entities exist and how to link them to external knowledge bases:

```yaml
entity_hints:
  - label: "Neo4j"
    type: "schema:SoftwareApplication"
    sameAs: "https://www.wikidata.org/entity/Q7071552"
  - label: "Emil Eifrem"
    type: "schema:Person"
    sameAs: "https://www.wikidata.org/entity/Q5372614"
```

**Fields:**
- `label` (required): Exact text as it appears in the article
- `type` (optional): Schema.org type — defaults to `schema:Thing`
- `sameAs` (optional): Wikidata or other canonical URI

**Finding Wikidata IDs:** Search [wikidata.org](https://www.wikidata.org) for the entity. The ID is in the URL: `https://www.wikidata.org/wiki/Q54872` → `Q54872` for SPARQL.

## Wikilinks

Mark important entities with double-bracket wikilinks:

```markdown
The key standards are [[RDF]] and [[SPARQL]].
[[Google]] uses the [[Google Knowledge Graph]] to enhance search.
```

**Rules:**
- Use the entity's canonical label inside brackets
- Match the label in `entity_hints` when possible
- Don't over-link — mark an entity on first mention in each section
- Common words (the, data, web) should NOT be wikilinked

## Content Structure for Extraction Quality

The extraction pipeline chunks articles at H1/H2 heading boundaries (~750 tokens per chunk). Structure your content accordingly:

### DO

- **Use H1/H2 headings** to organize into clear sections
- **State relationships explicitly**: "Neo4j was created by Emil Eifrem" → extracts `schema:creator`
- **Name entities clearly** on first use before abbreviating
- **One topic per section** — each chunk should be self-contained
- **Front-load key facts** — the first paragraph sets context for the whole article

### DON'T

- **Don't use H3+ exclusively** — the chunker splits on H1/H2 only
- **Don't rely on pronouns** across section boundaries — "it" won't extract well
- **Don't embed entities only in code blocks** — the LLM may skip them
- **Don't write walls of text** without headings — creates oversized chunks

## Relationship Patterns

The LLM maps natural language to schema.org properties. Write sentences that align with these patterns for high-confidence extraction:

| Write this... | Extracts as... |
|---------------|---------------|
| "X was created by Y" | `schema:creator` |
| "X was authored by Y" | `schema:author` |
| "This article discusses X" | `schema:mentions` |
| "X is a type of software" | `schema:SoftwareApplication` |
| "X is related to Y" | `kb:relatedTo` (fallback) |

## Available Entity Types

Choose from these schema.org types in `entity_hints`:

| Type | Use for |
|------|---------|
| `schema:Person` | People, authors, creators |
| `schema:Organization` | Companies, teams, foundations |
| `schema:SoftwareApplication` | Software tools, libraries, platforms |
| `schema:CreativeWork` | Books, papers, specifications |
| `schema:Article` | Reserved for the article itself |
| `schema:Thing` | Default — anything that doesn't fit above |

## Complete Example

See [references/example-article.md](references/example-article.md) for a fully annotated example article.

## Validation Checklist

Before committing an article:

- [ ] `title` and `date_published` are set in frontmatter
- [ ] At least 2-3 `entity_hints` with Wikidata `sameAs` links
- [ ] Key entities are `[[wikilinked]]` on first mention
- [ ] Content uses H1/H2 headings for section breaks
- [ ] Relationships are stated explicitly, not implied through pronouns
- [ ] Tags are lowercase, hyphenated (`knowledge-graph`, not `Knowledge Graph`)
