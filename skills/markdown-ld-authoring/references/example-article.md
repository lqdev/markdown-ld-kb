# Example Article

A complete example showing all authoring conventions.

```markdown
---
title: "Graph Databases vs. Triple Stores"
date_published: "2026-04-10"
date_modified: "2026-04-10"
authors:
  - name: "Jane Smith"
tags: ["graph-database", "triple-store", "rdf", "neo4j"]
about:
  - "https://schema.org/TechArticle"
summary: "A comparison of property graph databases and RDF triple stores, their trade-offs, and when to use each."
canonical_url: "https://example.com/2026/04/graph-databases-vs-triple-stores/"
entity_hints:
  - label: "Neo4j"
    type: "schema:SoftwareApplication"
    sameAs: "https://www.wikidata.org/entity/Q7071552"
  - label: "Apache Jena"
    type: "schema:SoftwareApplication"
    sameAs: "https://www.wikidata.org/entity/Q16939122"
  - label: "RDF"
    type: "schema:Thing"
    sameAs: "https://www.wikidata.org/wiki/Q54848"
  - label: "W3C"
    type: "schema:Organization"
    sameAs: "https://www.wikidata.org/wiki/Q37033"
  - label: "Emil Eifrem"
    type: "schema:Person"
    sameAs: "https://www.wikidata.org/entity/Q5372614"
---

# Graph Databases vs. Triple Stores

There are two dominant approaches to storing graph-structured data: **property graph databases** and **[[RDF]] triple stores**. Both model data as graphs, but they differ in data model, query language, and ecosystem.

## Property Graph Databases

[[Neo4j]] is the most widely adopted property graph database. It was created by [[Emil Eifrem]] and uses the [[Cypher]] query language. Property graphs allow arbitrary key-value pairs on both nodes and edges, making them flexible for application-level modeling.

Other property graph databases include [[Amazon Neptune]] (which also supports RDF) and [[TigerGraph]].

## RDF Triple Stores

RDF triple stores like [[Apache Jena]] and [[Blazegraph]] implement the [[W3C]] standards for Linked Data. They use [[SPARQL]] as the query language and represent all data as subject-predicate-object triples.

The key advantage of triple stores is interoperability: any RDF dataset can be merged with any other without schema mapping, because the data model is universal.

## When to Use Each

- Choose a **property graph** when you need flexible schemas and your data stays within one application.
- Choose a **triple store** when you need to integrate data across organizational boundaries or publish Linked Data on the web.
```

## What This Article Produces

The extraction pipeline would generate entities like:

```json
{
  "entities": [
    {"id": "https://example.com/id/neo4j", "type": "schema:SoftwareApplication", "label": "Neo4j", "sameAs": ["https://www.wikidata.org/entity/Q7071552"]},
    {"id": "https://example.com/id/emil-eifrem", "type": "schema:Person", "label": "Emil Eifrem", "sameAs": ["https://www.wikidata.org/entity/Q5372614"]},
    {"id": "https://example.com/id/apache-jena", "type": "schema:SoftwareApplication", "label": "Apache Jena", "sameAs": ["https://www.wikidata.org/entity/Q16939122"]}
  ],
  "assertions": [
    {"s": "https://example.com/id/neo4j", "p": "schema:creator", "o": "https://example.com/id/emil-eifrem", "confidence": 0.92},
    {"s": "https://example.com/2026/04/graph-databases-vs-triple-stores/", "p": "schema:mentions", "o": "https://example.com/id/neo4j", "confidence": 0.85}
  ]
}
```

## Anti-Patterns

### Bad: Vague references across sections

```markdown
## Section One
Neo4j is a graph database.

## Section Two
It was created by a Swedish entrepreneur.
```

The chunker may split these into separate chunks. The LLM won't know "it" refers to Neo4j.

### Good: Self-contained sections

```markdown
## Property Graph Databases
[[Neo4j]] is a graph database created by [[Emil Eifrem]].
```

Explicit subject + relationship in the same chunk = high-confidence extraction.
