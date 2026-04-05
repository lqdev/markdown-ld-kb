---
name: shacl-shape-designer
description: Write and maintain SHACL (Shapes Constraint Language) shapes for validating RDF knowledge graphs. Covers NodeShape design, property constraints, target declarations, and pySHACL integration. Use when adding new entity types, extending the ontology, or debugging validation failures in a Markdown-LD knowledge bank.
---

# SHACL Shape Designer

Write [W3C SHACL](https://www.w3.org/TR/shacl/) shapes that validate the RDF knowledge graph produced by the extraction pipeline. Shapes live in `ontology/shapes.ttl` and are checked by pySHACL during the build.

## Existing Shapes

The KB ships with three foundational shapes:

### ArticleShape
Every `schema:Article` must have a name and publication date:

```turtle
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
```

### EntityShape
Every `schema:Thing` must have a label:

```turtle
<urn:kb:shape:EntityShape> a sh:NodeShape ;
  sh:targetClass schema:Thing ;
  sh:property [
    sh:path schema:name ;
    sh:minCount 1 ;
    sh:message "Every entity must have a schema:name (label)." ;
  ] .
```

### ConfidenceShape
Confidence values must be in [0, 1]:

```turtle
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

## Writing New Shapes

### Step 1: Choose a Target

SHACL shapes need a target — what nodes they apply to:

```turtle
# Target by class
sh:targetClass schema:Person ;

# Target by subjects of a property
sh:targetSubjectsOf schema:author ;

# Target by objects of a property
sh:targetObjectsOf schema:mentions ;

# Target specific node
sh:targetNode <https://example.com/id/specific-entity> ;
```

### Step 2: Define Property Constraints

Common constraint types:

```turtle
sh:property [
  sh:path schema:name ;

  # Cardinality
  sh:minCount 1 ;      # required
  sh:maxCount 1 ;      # at most one

  # Datatype
  sh:datatype xsd:string ;
  sh:datatype xsd:date ;
  sh:datatype xsd:decimal ;

  # Value range (for numerics)
  sh:minInclusive 0.0 ;
  sh:maxInclusive 1.0 ;

  # String constraints
  sh:minLength 1 ;
  sh:maxLength 500 ;
  sh:pattern "^https?://" ;

  # Node type (for object properties)
  sh:nodeKind sh:IRI ;       # must be a URI
  sh:nodeKind sh:Literal ;   # must be a literal

  # Class constraint (value must be instance of)
  sh:class schema:Person ;

  # Error message
  sh:message "Human-readable error description." ;
] ;
```

### Step 3: Name the Shape

Use the `urn:kb:shape:` namespace with a descriptive PascalCase name:

```turtle
<urn:kb:shape:PersonShape> a sh:NodeShape ;
  ...
```

## Example: Adding a PersonShape

When adding `schema:Person` to the KB, create a shape ensuring every person has a name:

```turtle
<urn:kb:shape:PersonShape> a sh:NodeShape ;
  sh:targetClass schema:Person ;
  sh:property [
    sh:path schema:name ;
    sh:minCount 1 ;
    sh:datatype xsd:string ;
    sh:message "Every Person must have a schema:name." ;
  ] ;
  sh:property [
    sh:path schema:sameAs ;
    sh:nodeKind sh:IRI ;
    sh:message "schema:sameAs must be an IRI (URI), not a literal." ;
  ] .
```

## Example: SoftwareApplicationShape

```turtle
<urn:kb:shape:SoftwareApplicationShape> a sh:NodeShape ;
  sh:targetClass schema:SoftwareApplication ;
  sh:property [
    sh:path schema:name ;
    sh:minCount 1 ;
    sh:datatype xsd:string ;
    sh:message "Every SoftwareApplication must have a schema:name." ;
  ] .
```

## Example: AssertionShape

Validate that assertions have required provenance:

```turtle
<urn:kb:shape:AssertionShape> a sh:NodeShape ;
  sh:targetSubjectsOf kb:confidence ;
  sh:property [
    sh:path kb:confidence ;
    sh:minCount 1 ;
    sh:maxCount 1 ;
    sh:datatype xsd:decimal ;
    sh:minInclusive 0.0 ;
    sh:maxInclusive 1.0 ;
    sh:message "Assertions must have exactly one kb:confidence in [0, 1]." ;
  ] ;
  sh:property [
    sh:path prov:wasDerivedFrom ;
    sh:minCount 1 ;
    sh:nodeKind sh:IRI ;
    sh:message "Assertions must have prov:wasDerivedFrom pointing to a chunk URI." ;
  ] .
```

## Prefixes Required

Always include these prefixes in `shapes.ttl`:

```turtle
@prefix sh: <http://www.w3.org/ns/shacl#> .
@prefix schema: <https://schema.org/> .
@prefix kb: <https://example.com/vocab/kb#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix prov: <http://www.w3.org/ns/prov#> .
```

## Running Validation

### With pySHACL (Python)

```python
from pyshacl import validate
from rdflib import Graph

data_graph = Graph()
data_graph.parse("graph/articles/my-article.ttl", format="turtle")

shapes_graph = Graph()
shapes_graph.parse("ontology/shapes.ttl", format="turtle")

conforms, results_graph, results_text = validate(
    data_graph,
    shacl_graph=shapes_graph,
    inference="rdfs",
)

if not conforms:
    print(results_text)
```

### In the CI Pipeline

The build pipeline runs pySHACL automatically. Validation failures block the build and report which shapes were violated.

### From Tests

```bash
uv run pytest tests/test_shacl.py -v
```

## Debugging Validation Failures

When a shape violation occurs, the error includes:

1. **Focus node** — The entity that violated the constraint
2. **Path** — Which property was invalid
3. **Message** — The `sh:message` you defined
4. **Value** — The actual value that caused the failure

Common causes:
- Missing `schema:name` on extracted entities → check LLM prompt
- Confidence out of [0, 1] → check post-processing
- `sameAs` as a string literal instead of IRI → check entity_hints format

## Design Guidelines

1. **One shape per class** — Keep shapes focused and independent
2. **Always add `sh:message`** — Makes debugging much faster
3. **Start minimal** — Require only essential properties (name, type)
4. **Use `sh:severity`** for warnings vs. errors:
   ```turtle
   sh:severity sh:Warning ;  # non-blocking
   sh:severity sh:Violation ; # blocks build (default)
   ```
5. **Test shapes before committing** — Run against existing graph data
