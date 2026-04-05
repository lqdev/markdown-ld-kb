---
name: knowledge-graph-mcp
description: Build an MCP (Model Context Protocol) server that exposes a Markdown-LD knowledge graph to AI agents. Provides tool definitions for SPARQL queries, natural language questions, entity listing, and article discovery. Use when creating an MCP server to make a knowledge bank queryable by LLMs and agent frameworks.
---

# Knowledge Graph MCP Server

Build an [MCP server](https://modelcontextprotocol.io/) that wraps a Markdown-LD knowledge bank, letting any AI agent query the knowledge graph through structured tool calls.

## Why MCP?

The knowledge bank already has HTTP endpoints (`/api/sparql`, `/api/ask`). An MCP server adds:

- **Agent discoverability** — Agents automatically discover available tools
- **Structured input/output** — Zod/Pydantic schemas for parameters and results
- **Tool annotations** — Read-only hints, descriptions that help agents choose tools
- **Local or remote** — Works via stdio (local) or streamable HTTP (remote)

## Architecture

```
Agent (Claude, Copilot, etc.)
  ↕ MCP Protocol (stdio or HTTP)
MCP Server
  ↕ RDFLib (local) or HTTP (remote)
Knowledge Graph (Turtle files)
```

Two deployment modes:

1. **Local mode** — MCP server loads `.ttl` files directly into RDFLib
2. **Remote mode** — MCP server proxies to the deployed Azure Functions API

## Tool Definitions

### 1. `query_sparql`

Execute a SPARQL query against the knowledge graph.

```python
@mcp.tool(
    annotations={
        "readOnlyHint": True,
        "openWorldHint": False,
    }
)
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
```

### 2. `ask_question`

Natural language query — the server translates to SPARQL.

```python
@mcp.tool(
    annotations={
        "readOnlyHint": True,
        "openWorldHint": False,
    }
)
def ask_question(question: str) -> str:
    """Ask a natural language question about the knowledge graph.

    The question is translated to SPARQL and executed. The response
    includes both the generated SPARQL and the results.

    Example questions:
    - "What entities are in the knowledge graph?"
    - "Which articles mention SPARQL?"
    - "Find all organizations"

    Args:
        question: A natural language question about the knowledge.

    Returns:
        JSON with 'question', 'sparql', and 'results' fields.
    """
```

### 3. `list_entities`

Browse entities with optional type filter.

```python
@mcp.tool(
    annotations={
        "readOnlyHint": True,
        "openWorldHint": False,
    }
)
def list_entities(entity_type: str = "schema:Thing", limit: int = 50) -> str:
    """List entities in the knowledge graph, optionally filtered by type.

    Available types: schema:Person, schema:Organization,
    schema:SoftwareApplication, schema:CreativeWork, schema:Thing

    Args:
        entity_type: Schema.org type to filter by (default: all entities).
        limit: Maximum number of results (default: 50).

    Returns:
        JSON array of entities with id, name, and type.
    """
```

### 4. `list_articles`

Discover articles in the knowledge bank.

```python
@mcp.tool(
    annotations={
        "readOnlyHint": True,
        "openWorldHint": False,
    }
)
def list_articles(limit: int = 50) -> str:
    """List articles in the knowledge bank.

    Args:
        limit: Maximum number of results (default: 50).

    Returns:
        JSON array of articles with id, title, datePublished, and keywords.
    """
```

### 5. `get_entity_details`

Deep-dive into a specific entity's relationships.

```python
@mcp.tool(
    annotations={
        "readOnlyHint": True,
        "openWorldHint": False,
    }
)
def get_entity_details(entity_name: str) -> str:
    """Get detailed information about a specific entity.

    Returns the entity's type, sameAs links, articles that mention it,
    and related entities.

    Args:
        entity_name: The name of the entity to look up (case-insensitive).

    Returns:
        JSON with entity details and relationships.
    """
```

## Implementation (Python / FastMCP)

See [scripts/server.py](scripts/server.py) for a complete reference implementation.

### Quick Start

```bash
# Install dependencies
pip install mcp rdflib

# Run locally (stdio transport)
python scripts/server.py --graph-dir ./graph/articles

# Run as HTTP server
python scripts/server.py --transport http --port 8080
```

### Connecting to an Agent

**Claude Code / Copilot:**
```json
{
  "mcpServers": {
    "knowledge-graph": {
      "command": "python",
      "args": ["skills/knowledge-graph-mcp/scripts/server.py", "--graph-dir", "./graph/articles"]
    }
  }
}
```

## Safety

All tools are read-only:
- SPARQL queries are validated: `INSERT`, `DELETE`, `LOAD`, `CLEAR`, `DROP`, `CREATE` are blocked
- A `LIMIT` clause is injected if missing (default 100)
- No authentication required for read access

## Error Handling

Return clear, actionable errors:

```python
if not is_valid:
    return json.dumps({
        "error": f"Invalid SPARQL syntax: {error_msg}",
        "hint": "Check PREFIX declarations and property names. "
                "Available properties: schema:name, schema:mentions, schema:about, ..."
    })
```

## Reference

- [references/api-reference.md](references/api-reference.md) — Full API endpoint documentation
- [scripts/server.py](scripts/server.py) — Reference MCP server implementation
