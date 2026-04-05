"""MCP server for a Markdown-LD knowledge graph.

Exposes the knowledge bank as MCP tools that AI agents can discover
and call. Supports both local mode (loads .ttl files directly) and
remote mode (proxies to a deployed API).

Usage:
    # Local mode (stdio transport)
    python server.py --graph-dir ./graph/articles

    # Local mode (HTTP transport)
    python server.py --graph-dir ./graph/articles --transport http --port 8080

    # Remote mode (proxy to deployed API)
    python server.py --api-url https://your-swa.azurestaticapps.net

Requirements:
    pip install mcp rdflib
"""

import argparse
import json

from mcp.server.fastmcp import FastMCP
from rdflib import Dataset, Graph

mcp = FastMCP(
    "knowledge-graph",
    description="Query a Markdown-LD knowledge graph via SPARQL or natural language.",
)

_dataset: Dataset | None = None
_args = None

MUTATING_KEYWORDS = ["INSERT", "DELETE", "LOAD", "CLEAR", "DROP", "CREATE"]


def _load_dataset() -> Dataset:
    """Load all Turtle files into an RDFLib Dataset."""
    global _dataset
    if _dataset is not None:
        return _dataset

    from pathlib import Path

    ds = Dataset()
    graph_dir = Path(_args.graph_dir)

    if graph_dir.exists():
        for ttl_file in graph_dir.glob("*.ttl"):
            g = Graph()
            g.parse(str(ttl_file), format="turtle")
            for triple in g:
                ds.add(triple)

    _dataset = ds
    return _dataset


def _enforce_safety(sparql: str) -> tuple[bool, str, str]:
    """Validate safety constraints. Returns (is_safe, sanitized, error)."""
    upper = sparql.strip().upper()
    for kw in MUTATING_KEYWORDS:
        if kw in upper:
            return False, sparql, f"Mutating keyword '{kw}' is not allowed"
    if "LIMIT" not in upper and "SELECT" in upper:
        sparql = sparql.rstrip().rstrip(";") + "\nLIMIT 100"
    return True, sparql, ""


@mcp.tool()
def query_sparql(query: str) -> str:
    """Execute a SPARQL 1.1 SELECT or ASK query against the knowledge graph.

    The graph uses schema.org vocabulary. Available prefixes:
    - schema: <https://schema.org/>
    - kb: <https://example.com/vocab/kb#>
    - prov: <http://www.w3.org/ns/prov#>

    Only SELECT and ASK queries are allowed. Include a LIMIT clause.

    Args:
        query: A valid SPARQL 1.1 query string with PREFIX declarations.

    Returns:
        JSON string with SPARQL Results JSON format.
    """
    is_safe, query, error = _enforce_safety(query)
    if not is_safe:
        return json.dumps({"error": error})

    try:
        ds = _load_dataset()
        result = ds.query(query)
        serialized = result.serialize(format="json")
        if isinstance(serialized, bytes):
            serialized = serialized.decode("utf-8")
        return serialized
    except Exception as e:
        return json.dumps({
            "error": f"Query execution failed: {str(e)}",
            "hint": "Check PREFIX declarations and property names. "
                    "Available: schema:name, schema:mentions, schema:about, "
                    "schema:author, schema:creator, schema:sameAs, kb:relatedTo",
        })


@mcp.tool()
def list_entities(entity_type: str = "schema:Thing", limit: int = 50) -> str:
    """List entities in the knowledge graph, optionally filtered by type.

    Available types: schema:Person, schema:Organization,
    schema:SoftwareApplication, schema:CreativeWork, schema:Thing

    Args:
        entity_type: Schema.org type to filter by (default: all non-Article entities).
        limit: Maximum number of results (default: 50).

    Returns:
        JSON array of entities with id, name, and type.
    """
    if entity_type == "schema:Thing":
        query = f"""
        PREFIX schema: <https://schema.org/>
        SELECT DISTINCT ?entity ?name ?type WHERE {{
            ?entity a ?type ; schema:name ?name .
            FILTER(?type != schema:Article)
        }} LIMIT {limit}
        """
    else:
        query = f"""
        PREFIX schema: <https://schema.org/>
        SELECT DISTINCT ?entity ?name WHERE {{
            ?entity a {entity_type} ; schema:name ?name .
        }} LIMIT {limit}
        """
    return query_sparql(query)


@mcp.tool()
def list_articles(limit: int = 50) -> str:
    """List articles in the knowledge bank with their titles and dates.

    Args:
        limit: Maximum number of results (default: 50).

    Returns:
        JSON array of articles with id, title, datePublished, and keywords.
    """
    query = f"""
    PREFIX schema: <https://schema.org/>
    SELECT ?article ?title ?date ?keywords WHERE {{
        ?article a schema:Article ;
                 schema:name ?title .
        OPTIONAL {{ ?article schema:datePublished ?date }}
        OPTIONAL {{ ?article schema:keywords ?keywords }}
    }} LIMIT {limit}
    """
    return query_sparql(query)


@mcp.tool()
def get_entity_details(entity_name: str) -> str:
    """Get detailed information about a specific entity including relationships.

    Returns the entity's type, sameAs links, articles that mention it,
    and related entities.

    Args:
        entity_name: The name of the entity to look up (case-insensitive).

    Returns:
        JSON with entity details and relationships.
    """
    escaped = entity_name.replace('"', '\\"')
    query = f"""
    PREFIX schema: <https://schema.org/>
    PREFIX kb: <https://example.com/vocab/kb#>
    SELECT ?entity ?type ?sameAs ?article ?articleTitle ?related ?relatedName WHERE {{
        ?entity schema:name ?name .
        FILTER(LCASE(STR(?name)) = LCASE("{escaped}"))
        ?entity a ?type .
        OPTIONAL {{ ?entity schema:sameAs ?sameAs }}
        OPTIONAL {{
            ?article a schema:Article ;
                     schema:name ?articleTitle ;
                     schema:mentions ?entity .
        }}
        OPTIONAL {{
            ?entity kb:relatedTo ?related .
            ?related schema:name ?relatedName .
        }}
    }} LIMIT 100
    """
    return query_sparql(query)


def main():
    global _args
    parser = argparse.ArgumentParser(description="Knowledge Graph MCP Server")
    parser.add_argument(
        "--graph-dir",
        default="./graph/articles",
        help="Directory containing .ttl files (local mode)",
    )
    parser.add_argument(
        "--transport",
        choices=["stdio", "http"],
        default="stdio",
        help="MCP transport (default: stdio)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8080,
        help="Port for HTTP transport (default: 8080)",
    )
    _args = parser.parse_args()

    if _args.transport == "http":
        mcp.run(transport="streamable-http", host="0.0.0.0", port=_args.port)
    else:
        mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
