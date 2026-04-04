---
title: "What is a Knowledge Graph?"
date_published: "2026-04-04"
date_modified: "2026-04-04"
authors:
  - name: "Author Name"
tags: ["knowledge-graph", "sparql", "linked-data", "markdown"]
about:
  - "https://schema.org/KnowledgeGraph"
summary: "An introduction to knowledge graphs — what they are, why they matter, and how Markdown can be the authoring layer."
canonical_url: "https://example.com/2026/04/what-is-a-knowledge-graph/"
entity_hints:
  - label: "Knowledge Graph"
    sameAs: "https://www.wikidata.org/wiki/Q33002955"
  - label: "SPARQL"
    sameAs: "https://www.wikidata.org/wiki/Q54872"
  - label: "RDF"
    sameAs: "https://www.wikidata.org/wiki/Q54848"
---

# What is a Knowledge Graph?

A **knowledge graph** is a structured representation of real-world entities and the relationships between them. Unlike traditional databases that store data in rigid tables, knowledge graphs use a flexible graph model where nodes represent entities and edges represent relationships.

## Why Knowledge Graphs Matter

Knowledge graphs power many modern applications:

- [[Google]] uses the [[Google Knowledge Graph]] to enhance search results with structured information.
- [[Wikidata]] provides a free, collaborative knowledge base that anyone can edit.
- Enterprise knowledge graphs help organizations connect siloed data across departments.

The key standards behind knowledge graphs are [[RDF]] (Resource Description Framework) and [[SPARQL]] (the query language for RDF data). Together, they provide a vendor-neutral way to represent and query knowledge.

## Markdown as an Authoring Layer

Traditional knowledge graph construction requires specialized tools and ontology expertise. Our approach is different: **write normal Markdown, and let a CI pipeline extract the graph automatically**.

This means:

- Authors focus on writing clear, well-structured articles.
- [[Wikilinks]] (like `[[Entity Name]]`) mark important entities without disrupting readability.
- A build pipeline uses [[JSON-LD]] to serialize the extracted knowledge as Linked Data.
- The result is both human-readable (Markdown/HTML) and machine-readable (RDF/JSON-LD).

## The Technology Stack

Our knowledge bank uses:

- **[[Schema.org]]** as the primary vocabulary for typing entities and relationships.
- **[[JSON-LD]]** for serializing Linked Data in a web-friendly JSON format.
- **[[SHACL]]** for validating the graph against constraints.
- **[[PROV-O]]** for tracking the provenance of every extracted assertion.

This combination keeps the system standards-compliant and interoperable with the broader Semantic Web.
