# JSON-LD Context Design Patterns

## Pattern 1: Aliasing @id and @type

Make JSON-LD look like normal JSON by aliasing the keywords:

```json
{
  "@context": {
    "id": "@id",
    "type": "@type"
  }
}
```

This lets consumers write `"id": "https://..."` instead of `"@id": "https://..."`.

## Pattern 2: Namespace Prefixes

Define namespace prefixes to shorten URIs:

```json
{
  "@context": {
    "schema": "https://schema.org/",
    "kb": "https://example.com/vocab/kb#"
  }
}
```

Then use `"schema:name"` instead of `"https://schema.org/name"`.

## Pattern 3: Typed Properties

Declare the datatype of properties to avoid ambiguity:

```json
{
  "@context": {
    "confidence": {
      "@id": "kb:confidence",
      "@type": "http://www.w3.org/2001/XMLSchema#decimal"
    },
    "datePublished": {
      "@id": "schema:datePublished",
      "@type": "http://www.w3.org/2001/XMLSchema#date"
    }
  }
}
```

## Pattern 4: Object Properties (References)

Properties that point to other nodes should use `"@type": "@id"`:

```json
{
  "@context": {
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

This tells JSON-LD processors that the value is a URI reference, not a string literal.

## Pattern 5: @graph for Multiple Nodes

Use `@graph` when a document contains multiple entities:

```json
{
  "@context": "context.jsonld",
  "@graph": [
    {"id": "...", "type": "schema:Article", "schema:name": "..."},
    {"id": "...", "type": "schema:Person", "schema:name": "..."}
  ]
}
```

## Pattern 6: External Context Reference

Reference a shared context file instead of inlining:

```json
{
  "@context": "../../ontology/context.jsonld",
  "@graph": [...]
}
```

This keeps individual graph documents small and consistent.

## Common Mistakes

| Mistake | Impact | Fix |
|---------|--------|-----|
| Missing `@type` on numeric properties | Values treated as strings | Add explicit `@type` declaration |
| Using string values for object properties | URIs become literals | Add `"@type": "@id"` |
| Inlining context in every file | Inconsistency risk | Use external `@context` reference |
| Forgetting prefix declarations | Properties become full URIs | Declare all used namespaces |

## Validation

Test your JSON-LD with:
- [JSON-LD Playground](https://json-ld.org/playground/) — expand, compact, flatten
- RDFLib: `Graph().parse(data=json_str, format="json-ld")`
