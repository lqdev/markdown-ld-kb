"""Post-processing: canonicalize entities, deduplicate, add provenance."""

import json
import re
from collections import defaultdict
from pathlib import Path


def slugify(label: str) -> str:
    """Convert a label to a URL-safe slug.

    'JSON-LD 1.1' → 'json-ld-1-1'
    """
    s = label.lower().strip()
    s = re.sub(r"[^a-z0-9\s-]", "", s)
    s = re.sub(r"[\s_]+", "-", s)
    s = re.sub(r"-+", "-", s)
    return s.strip("-")


def entity_id(label: str, base_url: str = "https://example.com") -> str:
    """Generate a canonical entity URI from a label."""
    return f"{base_url}/id/{slugify(label)}"


def canonicalize_entities(
    entities: list[dict],
    base_url: str = "https://example.com",
) -> list[dict]:
    """Merge and canonicalize entities.

    - Normalize IDs via slugify
    - Merge by sameAs first, then exact slug match
    - Preserve the richest type (prefer specific over schema:Thing)
    """
    by_slug: dict[str, dict] = {}

    type_priority = {
        "schema:Person": 5,
        "schema:Organization": 5,
        "schema:SoftwareApplication": 5,
        "schema:CreativeWork": 4,
        "schema:Article": 4,
        "schema:Thing": 1,
    }

    for ent in entities:
        label = ent.get("label", "")
        slug = slugify(label)
        canonical_id = f"{base_url}/id/{slug}"

        if slug in by_slug:
            existing = by_slug[slug]
            # Merge sameAs
            existing_same = set(existing.get("sameAs", []))
            new_same = set(ent.get("sameAs", []))
            existing["sameAs"] = sorted(existing_same | new_same)
            # Keep higher-priority type
            existing_priority = type_priority.get(existing.get("type", ""), 0)
            new_priority = type_priority.get(ent.get("type", ""), 0)
            if new_priority > existing_priority:
                existing["type"] = ent["type"]
        else:
            by_slug[slug] = {
                "id": canonical_id,
                "type": ent.get("type", "schema:Thing"),
                "label": label,
                "sameAs": sorted(set(ent.get("sameAs", []))),
            }

    return list(by_slug.values())


def deduplicate_assertions(assertions: list[dict]) -> list[dict]:
    """Remove duplicate (s, p, o) assertions, keeping highest confidence."""
    best: dict[tuple, dict] = {}
    for a in assertions:
        key = (a.get("s", ""), a.get("p", ""), a.get("o", ""))
        existing = best.get(key)
        if existing is None or a.get("confidence", 0) > existing.get("confidence", 0):
            best[key] = a
    return list(best.values())


def build_jsonld(
    doc_id: str,
    meta: dict,
    entities: list[dict],
    assertions: list[dict],
    context_path: str = "../../ontology/context.jsonld",
) -> dict:
    """Build a JSON-LD document for an article and its extracted knowledge."""
    # Article node
    article = {
        "@context": context_path,
        "id": doc_id,
        "type": "schema:Article",
        "schema:name": meta.get("title", ""),
        "schema:datePublished": meta.get("date_published", ""),
        "schema:dateModified": meta.get("date_modified", ""),
    }

    if meta.get("tags"):
        article["schema:keywords"] = ", ".join(meta["tags"])
    if meta.get("summary"):
        article["schema:description"] = meta["summary"]

    # Build graph nodes
    graph = [article]

    for ent in entities:
        node = {
            "id": ent["id"],
            "type": ent["type"],
            "schema:name": ent["label"],
        }
        if ent.get("sameAs"):
            node["schema:sameAs"] = (
                ent["sameAs"] if len(ent["sameAs"]) > 1 else ent["sameAs"][0]
            )
        graph.append(node)

    # Assertions as reified statements with provenance
    for a in assertions:
        stmt = {
            "type": "kb:Assertion",
            "schema:subjectOf": a["s"],
            a["p"]: a["o"],
            "confidence": a.get("confidence", 0.5),
            "source": a.get("source", ""),
        }
        graph.append(stmt)

    return {"@context": context_path, "@graph": graph}


def build_turtle(
    doc_id: str,
    meta: dict,
    entities: list[dict],
    assertions: list[dict],
) -> str:
    """Build a Turtle serialization of the extracted knowledge."""
    lines = [
        "@prefix schema: <https://schema.org/> .",
        "@prefix prov: <http://www.w3.org/ns/prov#> .",
        "@prefix kb: <https://example.com/vocab/kb#> .",
        "@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .",
        "",
    ]

    # Article
    lines.append(f"<{doc_id}> a schema:Article ;")
    lines.append(f'  schema:name "{_escape_turtle(meta.get("title", ""))}" ;')
    lines.append(
        f'  schema:datePublished "{meta.get("date_published", "")}"^^xsd:date .'
    )
    lines.append("")

    # Entities
    for ent in entities:
        lines.append(f"<{ent['id']}> a {ent['type']} ;")
        lines.append(f'  schema:name "{_escape_turtle(ent["label"])}" .')
        if ent.get("sameAs"):
            for sa in ent["sameAs"]:
                lines.append(f"<{ent['id']}> schema:sameAs <{sa}> .")
        lines.append("")

    # Assertions as direct triples
    for a in assertions:
        s, p, o = a["s"], a["p"], a["o"]
        lines.append(f"<{s}> {p} <{o}> .")

    return "\n".join(lines) + "\n"


def _escape_turtle(s: str) -> str:
    """Escape special characters for Turtle string literals."""
    return s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
