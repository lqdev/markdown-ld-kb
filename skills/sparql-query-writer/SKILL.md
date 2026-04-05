---
name: sparql-query-writer
description: Write SPARQL 1.1 queries against schema.org-based knowledge graphs built from Markdown-LD content. Covers the available vocabulary (classes, properties, prefixes), common query patterns, case-insensitive matching, safety constraints, and result interpretation. Use when querying a Markdown-LD knowledge bank's SPARQL endpoint or helping users formulate queries.
---

# SPARQL Query Writer

Write SPARQL queries for knowledge graphs built from Markdown articles using schema.org vocabulary. The KB stores articles, entities, and their relationships as RDF triples.

## Prefixes

Always declare the prefixes you use:

```sparql
PREFIX schema: <https://schema.org/>
PREFIX kb:     <https://example.com/vocab/kb#>
PREFIX prov:   <http://www.w3.org/ns/prov#>
PREFIX rdf:    <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX xsd:    <http://www.w3.org/2001/XMLSchema#>
```

## Available Classes

| Class | Description |
|-------|-------------|
| `schema:Article` | A Markdown article in the KB |
| `schema:Person` | A person (author, creator, etc.) |
| `schema:Organization` | A company, foundation, or team |
| `schema:SoftwareApplication` | Software tools, libraries, platforms |
| `schema:CreativeWork` | Books, papers, specifications |
| `schema:Thing` | Base type for any entity |

## Available Properties

| Property | Domain → Range | Description |
|----------|---------------|-------------|
| `schema:name` | Any → `xsd:string` | Label/title of any entity or article |
| `schema:mentions` | Article → Thing | Article mentions an entity |
| `schema:about` | Article → Thing | Article is about a topic |
| `schema:author` | Article → Person | Author of an article |
| `schema:creator` | Thing → Person/Org | Creator of a thing |
| `schema:datePublished` | Article → `xsd:date` | Publication date |
| `schema:dateModified` | Article → `xsd:date` | Last modified date |
| `schema:sameAs` | Thing → URI | Link to external identity (Wikidata) |
| `schema:keywords` | Article → `xsd:string` | Comma-separated tags |
| `schema:description` | Article → `xsd:string` | Summary text |
| `kb:relatedTo` | Thing → Thing | Fallback relation |
| `kb:confidence` | Assertion → `xsd:decimal` | Extraction confidence 0–1 |
| `prov:wasDerivedFrom` | Assertion → URI | Provenance: source chunk |

## Core Query Patterns

### List all entities (non-articles)

```sparql
PREFIX schema: <https://schema.org/>
SELECT DISTINCT ?entity ?name ?type WHERE {
  ?entity a ?type ;
          schema:name ?name .
  FILTER(?type != schema:Article)
}
LIMIT 100
```

### Find articles mentioning an entity

```sparql
PREFIX schema: <https://schema.org/>
SELECT ?article ?title WHERE {
  ?article a schema:Article ;
           schema:name ?title ;
           schema:mentions ?entity .
  ?entity schema:name ?entityName .
  FILTER(LCASE(STR(?entityName)) = "sparql")
}
LIMIT 100
```

### Find all entities of a specific type

```sparql
PREFIX schema: <https://schema.org/>
SELECT ?entity ?name WHERE {
  ?entity a schema:Organization ;
          schema:name ?name .
}
LIMIT 100
```

### Find topics covered by an article

```sparql
PREFIX schema: <https://schema.org/>
SELECT ?topic ?topicName WHERE {
  ?article a schema:Article ;
           schema:name ?title ;
           schema:mentions ?topic .
  ?topic schema:name ?topicName .
  FILTER(CONTAINS(LCASE(STR(?title)), "knowledge graph"))
}
LIMIT 100
```

### Find connections between entities

```sparql
PREFIX schema: <https://schema.org/>
SELECT ?subject ?predicate ?object WHERE {
  ?subject ?predicate ?object .
  FILTER(?predicate != rdf:type)
}
LIMIT 50
```

### Find entities with Wikidata links

```sparql
PREFIX schema: <https://schema.org/>
SELECT ?entity ?name ?wikidata WHERE {
  ?entity schema:name ?name ;
          schema:sameAs ?wikidata .
  FILTER(CONTAINS(STR(?wikidata), "wikidata.org"))
}
LIMIT 100
```

## Case-Insensitive Matching

Entity names are stored as plain strings. Always match case-insensitively:

```sparql
-- Exact match (case-insensitive)
FILTER(LCASE(STR(?name)) = "neo4j")

-- Contains match (case-insensitive)
FILTER(CONTAINS(LCASE(STR(?name)), "knowledge"))

-- Regex match
FILTER(REGEX(?name, "graph", "i"))
```

**Prefer `LCASE` + exact match** over REGEX for performance.

## Safety Constraints

The endpoint enforces these rules:

1. **Only `SELECT` and `ASK` queries** — `INSERT`, `DELETE`, `LOAD`, `CLEAR`, `DROP`, `CREATE` are blocked
2. **Always include `LIMIT`** — default to `LIMIT 100` unless the user asks for all results
3. **No mutating operations** — the graph is read-only at query time

## Using the Endpoint

### GET request

```
/api/sparql?query={url-encoded-sparql}
```

### POST request (preferred for complex queries)

```
POST /api/sparql
Content-Type: application/sparql-query

{raw SPARQL query}
```

### Response format

The endpoint returns [SPARQL Results JSON](https://www.w3.org/TR/sparql11-results-json/):

```json
{
  "head": { "vars": ["entity", "name"] },
  "results": {
    "bindings": [
      {
        "entity": { "type": "uri", "value": "https://example.com/id/neo4j" },
        "name": { "type": "literal", "value": "Neo4j" }
      }
    ]
  }
}
```

## Natural Language Alternative

Don't know SPARQL? Use the `/api/ask` endpoint:

```
POST /api/ask
Content-Type: application/json
{"question": "What entities are in the knowledge graph?"}
```

The response includes the generated SPARQL so you can learn the query language:

```json
{
  "question": "What entities are in the knowledge graph?",
  "sparql": "PREFIX schema: ...",
  "results": { ... }
}
```

## Common Mistakes

| Mistake | Fix |
|---------|-----|
| Forgetting `PREFIX` declarations | Always include prefixes you reference |
| Case-sensitive name matching | Use `LCASE(STR(?name))` |
| Missing `LIMIT` clause | Default to `LIMIT 100` |
| Inventing predicates | Only use properties from the table above |
| Using `INSERT`/`DELETE` | The endpoint is read-only |

## Reference

See [references/vocabulary.md](references/vocabulary.md) for the complete vocabulary definition.
