---
name: rdf-jsonld-engineer
description: Design and maintain RDF knowledge graph artifacts for Markdown-LD systems. Covers JSON-LD context authoring, Turtle serialization, entity ID minting, sameAs alignment with Wikidata, and the schema.org type system. Use when working with ontology files, graph outputs, or extending the data model.
---

# RDF / JSON-LD Engineering

Maintain the Linked Data layer of a Markdown-LD knowledge bank. The system produces two serialization formats per article: JSON-LD (for web consumption) and Turtle (for SPARQL/RDFLib).

## JSON-LD Context

The shared context lives at `ontology/context.jsonld` and defines how JSON keys map to RDF predicates:

```json
{
  "@context": {
    "schema": "https://schema.org/",
    "prov": "http://www.w3.org/ns/prov#",
    "kb": "https://example.com/vocab/kb#",
    "id": "@id",
    "type": "@type",
    "confidence": {
      "@id": "kb:confidence",
      "@type": "http://www.w3.org/2001/XMLSchema#decimal"
    },
    "source": {
      "@id": "prov:wasDerivedFrom",
      "@type": "@id"
    },
    "relatedTo": {
      "@id": "kb:relatedTo",
      "@type": "@id"
    }
  }
}
```

### Design Principles

1. **Use `@id` aliasing** — `"id": "@id"` and `"type": "@type"` make JSON-LD look like normal JSON
2. **Type coercion** — Declare `@type` on properties to avoid ambiguity (e.g., `confidence` is always `xsd:decimal`)
3. **Namespace prefixes** — Declare `schema`, `prov`, `kb` as prefix shortcuts
4. **ID-typed references** — Properties pointing to other nodes use `"@type": "@id"`

### Extending the Context

When adding new properties:

```json
{
  "@context": {
    "newProperty": {
      "@id": "schema:newProperty",
      "@type": "http://www.w3.org/2001/XMLSchema#string"
    }
  }
}
```

**Rules:**
- Prefer schema.org properties when one exists
- Only add `kb:` properties for concepts schema.org doesn't cover
- Always declare `@type` for datatype properties
- Use `"@type": "@id"` for object properties (references to other nodes)

## JSON-LD Graph Structure

Each article produces a JSON-LD document with `@graph`:

```json
{
  "@context": "../../ontology/context.jsonld",
  "@graph": [
    {
      "id": "https://example.com/2026/04/my-article/",
      "type": "schema:Article",
      "schema:name": "My Article",
      "schema:datePublished": "2026-04-04",
      "schema:keywords": "knowledge-graph, rdf"
    },
    {
      "id": "https://example.com/id/neo4j",
      "type": "schema:SoftwareApplication",
      "schema:name": "Neo4j",
      "schema:sameAs": "https://www.wikidata.org/entity/Q7071552"
    },
    {
      "type": "kb:Assertion",
      "schema:subjectOf": "https://example.com/2026/04/my-article/",
      "schema:mentions": "https://example.com/id/neo4j",
      "confidence": 0.85,
      "source": "urn:kb:chunk:..."
    }
  ]
}
```

### Graph Node Types

1. **Article node** — One per document, typed `schema:Article`
2. **Entity nodes** — Extracted entities with `schema:name` and optional `schema:sameAs`
3. **Assertion nodes** — Reified statements with provenance and confidence

## Turtle Serialization

The same data in Turtle format for RDFLib/SPARQL:

```turtle
@prefix schema: <https://schema.org/> .
@prefix prov: <http://www.w3.org/ns/prov#> .
@prefix kb: <https://example.com/vocab/kb#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .

<https://example.com/2026/04/my-article/> a schema:Article ;
  schema:name "My Article" ;
  schema:datePublished "2026-04-04"^^xsd:date .

<https://example.com/id/neo4j> a schema:SoftwareApplication ;
  schema:name "Neo4j" .
<https://example.com/id/neo4j> schema:sameAs <https://www.wikidata.org/entity/Q7071552> .
```

### Turtle Escaping

Special characters in string literals must be escaped:

| Character | Escape |
|-----------|--------|
| `\` | `\\` |
| `"` | `\"` |
| newline | `\n` |

## Entity ID Minting

All entities get deterministic, stable URIs:

```
{base_url}/id/{slug(label)}
```

The `slugify` function:
1. Lowercase the label
2. Remove characters not in `[a-z0-9\s-]`
3. Replace spaces/underscores with hyphens
4. Collapse consecutive hyphens
5. Strip leading/trailing hyphens

**Examples:**
- `"JSON-LD 1.1"` → `json-ld-1-1`
- `"W3C"` → `w3c`
- `"Apache Jena"` → `apache-jena`

### Stability Guarantee

The same label always produces the same slug and therefore the same URI. This is critical for deduplication across chunks and builds.

## sameAs Alignment

Use `schema:sameAs` to link entities to canonical external identifiers:

```turtle
<https://example.com/id/sparql> schema:sameAs <https://www.wikidata.org/wiki/Q54872> .
```

**Priority sources:**
1. Wikidata (`wikidata.org/wiki/Q...` or `wikidata.org/entity/Q...`)
2. DBpedia (`dbpedia.org/resource/...`)
3. Official website URLs

**When merging entities**, the system takes the union of all `sameAs` URIs.

## Entity Canonicalization

When the same entity appears across multiple chunks (possibly with different labels or types), the post-processor merges them:

1. **Slug match** — Two entities with the same slug are merged
2. **sameAs match** — Entities sharing a `sameAs` URI are merged
3. **Type priority** — The most specific type wins (Person > Thing)
4. **Label preservation** — The first-seen label is kept
5. **sameAs union** — All `sameAs` URIs are collected

## Custom Vocabulary (`ontology/kb.ttl`)

The `kb:` namespace defines properties not covered by schema.org:

| Property | Description |
|----------|-------------|
| `kb:confidence` | Extraction confidence [0, 1] |
| `kb:relatedTo` | Fallback relation between entities |
| `kb:chunk` | Source chunk URI |
| `kb:docPath` | Source file path |
| `kb:charStart` | Chunk start offset |
| `kb:charEnd` | Chunk end offset |

### Adding New Custom Properties

1. Add the RDF definition to `ontology/kb.ttl`:
   ```turtle
   kb:newProp a rdf:Property ;
     rdfs:label "new property" ;
     rdfs:comment "Description of what this property represents." ;
     rdfs:domain schema:Thing ;
     rdfs:range xsd:string .
   ```

2. Add it to `ontology/context.jsonld` for JSON-LD support

3. Add a SHACL shape in `ontology/shapes.ttl` if the property has constraints

4. Update the extraction prompt in `tools/prompts/` to teach the LLM about it

## Reference

See [references/context-design.md](references/context-design.md) for JSON-LD context design patterns.
