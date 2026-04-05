# API Reference

The Markdown-LD knowledge bank exposes two HTTP endpoints via Azure Functions.

## `GET/POST /api/sparql`

Execute SPARQL 1.1 queries against the knowledge graph.

### GET

```
GET /api/sparql?query={url-encoded-sparql}
```

### POST (preferred for complex queries)

```
POST /api/sparql
Content-Type: application/sparql-query

PREFIX schema: <https://schema.org/>
SELECT ?name WHERE { ?e schema:name ?name }
```

### POST (form-encoded)

```
POST /api/sparql
Content-Type: application/x-www-form-urlencoded

query=PREFIX+schema...
```

### Response

```
Content-Type: application/sparql-results+json

{
  "head": { "vars": ["name"] },
  "results": {
    "bindings": [
      { "name": { "type": "literal", "value": "Neo4j" } }
    ]
  }
}
```

### Errors

- `400` — Missing query parameter or SPARQL syntax error
- `403` — Mutating query detected (INSERT, DELETE, etc.)

### Headers

```
Access-Control-Allow-Origin: *
Cache-Control: public, max-age=300
```

## `GET/POST /api/ask`

Translate natural language to SPARQL and execute.

### GET

```
GET /api/ask?question={url-encoded-question}
```

### POST (preferred)

```
POST /api/ask
Content-Type: application/json

{"question": "What entities are in the knowledge graph?"}
```

### Response

```json
{
  "question": "What entities are in the knowledge graph?",
  "sparql": "PREFIX schema: <https://schema.org/>\nSELECT DISTINCT ?entity ?name ?type WHERE {\n  ?entity a ?type ;\n          schema:name ?name .\n  FILTER(?type != schema:Article)\n}\nLIMIT 100",
  "results": {
    "head": { "vars": ["entity", "name", "type"] },
    "results": { "bindings": [...] }
  }
}
```

### Errors

- `400` — Missing question parameter or SPARQL execution error
- `502` — LLM rate limit or API error

### Requirements

The `/api/ask` endpoint requires `GITHUB_TOKEN` as an environment variable for LLM access (GitHub Models). The `/api/sparql` endpoint works without any configuration.

## Available Schema

### Classes

| Class | Description |
|-------|-------------|
| `schema:Article` | A Markdown article |
| `schema:Person` | A person |
| `schema:Organization` | A company, foundation, or team |
| `schema:SoftwareApplication` | Software tools and libraries |
| `schema:CreativeWork` | Books, papers, specs |
| `schema:Thing` | Base type for any entity |

### Properties

| Property | Domain → Range |
|----------|---------------|
| `schema:name` | Any → string |
| `schema:mentions` | Article → Thing |
| `schema:about` | Article → Thing |
| `schema:author` | Article → Person |
| `schema:creator` | Thing → Person/Org |
| `schema:datePublished` | Article → date |
| `schema:dateModified` | Article → date |
| `schema:sameAs` | Thing → URI |
| `schema:keywords` | Article → string |
| `schema:description` | Article → string |
| `kb:relatedTo` | Thing → Thing |
| `kb:confidence` | Assertion → decimal |
| `prov:wasDerivedFrom` | Assertion → URI |
