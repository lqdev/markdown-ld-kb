# Existing Shapes Reference

The current shapes in `ontology/shapes.ttl`:

```turtle
@prefix sh: <http://www.w3.org/ns/shacl#> .
@prefix schema: <https://schema.org/> .
@prefix kb: <https://example.com/vocab/kb#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .

# Every schema:Article must have a name and datePublished
<urn:kb:shape:ArticleShape> a sh:NodeShape ;
  sh:targetClass schema:Article ;
  sh:property [
    sh:path schema:name ;
    sh:minCount 1 ;
    sh:datatype xsd:string ;
    sh:message "Every Article must have a schema:name." ;
  ] ;
  sh:property [
    sh:path schema:datePublished ;
    sh:minCount 1 ;
    sh:message "Every Article must have a schema:datePublished." ;
  ] .

# Every entity must have a label
<urn:kb:shape:EntityShape> a sh:NodeShape ;
  sh:targetClass schema:Thing ;
  sh:property [
    sh:path schema:name ;
    sh:minCount 1 ;
    sh:message "Every entity must have a schema:name (label)." ;
  ] .

# Confidence must be in [0, 1]
<urn:kb:shape:ConfidenceShape> a sh:NodeShape ;
  sh:targetSubjectsOf kb:confidence ;
  sh:property [
    sh:path kb:confidence ;
    sh:minInclusive 0.0 ;
    sh:maxInclusive 1.0 ;
    sh:datatype xsd:decimal ;
    sh:message "kb:confidence must be a decimal in [0, 1]." ;
  ] .
```

## Shape Coverage Matrix

| Entity Type | Shape Exists? | Validates |
|-------------|:------------:|-----------|
| `schema:Article` | ✅ | `schema:name`, `schema:datePublished` |
| `schema:Thing` | ✅ | `schema:name` |
| `schema:Person` | ❌ | — |
| `schema:Organization` | ❌ | — |
| `schema:SoftwareApplication` | ❌ | — |
| `schema:CreativeWork` | ❌ | — |
| Assertions (`kb:confidence`) | ✅ | Value in [0, 1] |
| Provenance (`prov:wasDerivedFrom`) | ❌ | — |

## Recommended New Shapes

Priority shapes to add:

1. **PersonShape** — Validate `schema:Person` has `schema:name`
2. **OrganizationShape** — Validate `schema:Organization` has `schema:name`
3. **SoftwareApplicationShape** — Validate `schema:SoftwareApplication` has `schema:name`
4. **AssertionShape** — Validate assertions have both `kb:confidence` and `prov:wasDerivedFrom`
5. **SameAsShape** — Validate that `schema:sameAs` values are IRIs, not literals
