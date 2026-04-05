# Vocabulary Reference

Complete vocabulary used in the Markdown-LD knowledge bank.

## Namespace Prefixes

| Prefix | URI | Usage |
|--------|-----|-------|
| `schema:` | `https://schema.org/` | Primary vocabulary for types and properties |
| `kb:` | `https://example.com/vocab/kb#` | Custom KB properties (confidence, relatedTo) |
| `prov:` | `http://www.w3.org/ns/prov#` | Provenance tracking |
| `rdf:` | `http://www.w3.org/1999/02/22-rdf-syntax-ns#` | RDF core |
| `rdfs:` | `http://www.w3.org/2000/01/rdf-schema#` | RDF Schema |
| `xsd:` | `http://www.w3.org/2001/XMLSchema#` | XML Schema datatypes |
| `sh:` | `http://www.w3.org/ns/shacl#` | SHACL validation shapes |

## Custom Vocabulary (`kb:`)

Defined in `ontology/kb.ttl`:

### `kb:confidence`
- Type: `rdf:Property`
- Range: `xsd:decimal`
- Description: Extractor confidence in [0, 1]
- Usage: Attached to reified assertions to indicate how explicitly the text states the relation

### `kb:relatedTo`
- Type: `rdf:Property`
- Domain: `schema:Thing`
- Range: `schema:Thing`
- Description: Fallback relation when no schema.org property fits

### `kb:chunk`
- Type: `rdf:Property`
- Description: Chunk that produced an assertion

### `kb:docPath`
- Type: `rdf:Property`
- Description: Relative file path of the source Markdown document

### `kb:charStart` / `kb:charEnd`
- Type: `rdf:Property`
- Range: `xsd:integer`
- Description: Character offsets of the chunk in the source document

## Entity ID Convention

All entity IDs follow the pattern:

```
{base_url}/id/{slug}
```

Where `slug` is derived from the entity label:
- Lowercase
- Replace spaces and underscores with hyphens
- Remove special characters
- Collapse consecutive hyphens

Examples:
- "Neo4j" → `https://example.com/id/neo4j`
- "JSON-LD 1.1" → `https://example.com/id/json-ld-1-1`
- "Emil Eifrem" → `https://example.com/id/emil-eifrem`

## Article ID Convention

Article IDs are derived from their file path or `canonical_url` frontmatter:

```
content/2026/04/my-article.md → https://example.com/2026/04/my-article/
```

If `canonical_url` is set in frontmatter, it takes precedence over the path-derived ID.

## Type Hierarchy

```
schema:Thing
├── schema:Person
├── schema:Organization
├── schema:SoftwareApplication
├── schema:CreativeWork
│   └── schema:Article
└── (other schema.org types as needed)
```

The extraction pipeline uses a type priority system when merging duplicate entities:
- `schema:Person` (priority 5)
- `schema:Organization` (priority 5)
- `schema:SoftwareApplication` (priority 5)
- `schema:CreativeWork` (priority 4)
- `schema:Article` (priority 4)
- `schema:Thing` (priority 1 — default)

When the same entity appears with different types across chunks, the highest-priority type wins.
