"""Natural language to SPARQL translation using GitHub Models.

Translates user questions into SPARQL queries using an LLM with
schema-injected few-shot prompting, validates syntax, enforces
safety constraints, and caches results.
"""

import json
import logging
import os
import re

from openai import OpenAI, RateLimitError, APIError
from rdflib.plugins.sparql import prepareQuery

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "openai/gpt-4o-mini"
DEFAULT_ENDPOINT = "https://models.github.ai/inference"
MAX_RETRIES = 2  # initial + 1 retry with error feedback

SYSTEM_PROMPT = """\
You are a SPARQL query generator for a knowledge graph built with schema.org vocabulary.
Translate the user's natural language question into a valid SPARQL 1.1 SELECT or ASK query.

PREFIXES (always include the ones you use):
  PREFIX schema: <https://schema.org/>
  PREFIX kb:     <https://example.com/vocab/kb#>
  PREFIX prov:   <http://www.w3.org/ns/prov#>
  PREFIX rdf:    <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
  PREFIX xsd:    <http://www.w3.org/2001/XMLSchema#>

AVAILABLE CLASSES:
  schema:Article, schema:Person, schema:Organization,
  schema:SoftwareApplication, schema:CreativeWork, schema:Thing

AVAILABLE PROPERTIES:
  schema:name          — label/title of any entity or article (xsd:string)
  schema:mentions      — article mentions an entity (Article → Thing)
  schema:about         — article is about a topic (Article → Thing)
  schema:author        — author of an article (Article → Person)
  schema:creator       — creator of a thing (Thing → Person/Org)
  schema:datePublished — publication date (Article → xsd:date)
  schema:dateModified  — last modified date (Article → xsd:date)
  schema:sameAs        — link to external URI like Wikidata
  schema:keywords      — comma-separated tags (Article → xsd:string)
  schema:description   — summary text (Article → xsd:string)
  kb:relatedTo         — fallback relation (Thing → Thing)
  kb:confidence        — extraction confidence 0..1 (xsd:decimal)
  prov:wasDerivedFrom  — provenance link to source chunk

CONSTRAINTS:
1. Output ONLY the SPARQL query — no explanations, no markdown fences.
2. Only use classes and properties listed above. Do NOT invent predicates.
3. Only generate SELECT or ASK queries. Never INSERT, DELETE, or UPDATE.
4. Include a LIMIT clause (default LIMIT 100) unless the user asks for all results.
5. Entity names are stored as plain strings via schema:name (e.g., "Knowledge Graph", "Neo4j").
   Match case-insensitively using FILTER(LCASE(STR(?name)) = LCASE("...")) when searching by name.
6. Articles are typed as schema:Article. Entities may be schema:Thing or a subtype.
7. If the question cannot be answered with the available schema, output exactly:
   CANNOT_ANSWER: <brief reason>

EXAMPLES:

Q: What entities are in the knowledge graph?
A:
PREFIX schema: <https://schema.org/>
SELECT DISTINCT ?entity ?name ?type WHERE {
  ?entity a ?type ;
          schema:name ?name .
  FILTER(?type != schema:Article)
}
LIMIT 100

Q: Which articles mention SPARQL?
A:
PREFIX schema: <https://schema.org/>
SELECT ?article ?title WHERE {
  ?article a schema:Article ;
           schema:name ?title ;
           schema:mentions ?entity .
  ?entity schema:name ?entityName .
  FILTER(LCASE(STR(?entityName)) = "sparql")
}
LIMIT 100

Q: Find all organizations
A:
PREFIX schema: <https://schema.org/>
SELECT ?org ?name WHERE {
  ?org a schema:Organization ;
       schema:name ?name .
}
LIMIT 100

Q: What topics does the article about knowledge graphs cover?
A:
PREFIX schema: <https://schema.org/>
SELECT ?topic ?topicName WHERE {
  ?article a schema:Article ;
           schema:name ?title ;
           schema:mentions ?topic .
  ?topic schema:name ?topicName .
  FILTER(CONTAINS(LCASE(STR(?title)), "knowledge graph"))
}
LIMIT 100
"""

# Simple in-memory cache (per cold start)
_query_cache: dict[str, str] = {}

MUTATING_KEYWORDS = ["INSERT", "DELETE", "LOAD", "CLEAR", "DROP", "CREATE"]


def _normalize_question(question: str) -> str:
    """Normalize a question for cache lookup."""
    return question.strip().lower()


def _create_client() -> OpenAI:
    """Create an OpenAI client for GitHub Models."""
    endpoint = os.environ.get("LLM_ENDPOINT", DEFAULT_ENDPOINT)
    api_key = os.environ.get("GITHUB_TOKEN", "")
    if not api_key:
        raise ValueError("GITHUB_TOKEN environment variable is required for /api/ask")
    return OpenAI(base_url=endpoint, api_key=api_key)


def _call_llm(client: OpenAI, user_message: str, model: str) -> str:
    """Call the LLM and return the raw response text."""
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
        temperature=0,
    )
    return (response.choices[0].message.content or "").strip()


def validate_sparql(sparql: str) -> tuple[bool, str]:
    """Validate SPARQL syntax using RDFLib's parser.

    Returns (is_valid, error_message).
    """
    try:
        prepareQuery(sparql)
        return True, ""
    except Exception as e:
        return False, str(e)


def enforce_safety(sparql: str) -> tuple[bool, str, str]:
    """Check safety constraints on a SPARQL query.

    Returns (is_safe, sanitized_sparql, error_message).
    """
    upper = sparql.strip().upper()

    # Block mutating queries
    for kw in MUTATING_KEYWORDS:
        if kw in upper:
            return False, sparql, f"Mutating keyword '{kw}' is not allowed"

    # Inject LIMIT if missing
    if "LIMIT" not in upper and ("SELECT" in upper):
        sparql = sparql.rstrip().rstrip(";") + "\nLIMIT 100"

    return True, sparql, ""


def translate(
    question: str,
    model: str = DEFAULT_MODEL,
) -> tuple[str, str | None]:
    """Translate a natural language question to SPARQL.

    Returns (sparql_query, error_message).
    If error_message is not None, translation failed.
    """
    # Check cache
    cache_key = _normalize_question(question)
    if cache_key in _query_cache:
        logger.info("NL cache hit for: %s", question[:80])
        return _query_cache[cache_key], None

    try:
        client = _create_client()
    except ValueError as e:
        return "", str(e)

    user_message = f"Q: {question}\nA:"

    for attempt in range(MAX_RETRIES):
        try:
            raw = _call_llm(client, user_message, model)
        except RateLimitError:
            return "", "LLM rate limit exceeded. Try again later."
        except APIError as e:
            return "", f"LLM API error: {e}"

        # Check for CANNOT_ANSWER
        if raw.startswith("CANNOT_ANSWER"):
            return "", raw

        # Strip markdown fences if present
        sparql = _strip_code_fences(raw)

        # Validate syntax
        is_valid, err = validate_sparql(sparql)
        if is_valid:
            is_safe, sparql, safety_err = enforce_safety(sparql)
            if not is_safe:
                return "", safety_err
            _query_cache[cache_key] = sparql
            return sparql, None

        # Retry with error feedback
        if attempt < MAX_RETRIES - 1:
            logger.warning("SPARQL syntax error (attempt %d): %s", attempt + 1, err)
            user_message = (
                f"Q: {question}\n\n"
                f"Your previous SPARQL had a syntax error:\n{err}\n\n"
                f"Previous query:\n{sparql}\n\n"
                f"Please fix the syntax error and output only the corrected SPARQL query."
            )
        else:
            return "", f"Failed to generate valid SPARQL after {MAX_RETRIES} attempts: {err}"

    return "", "Translation failed"


def _strip_code_fences(text: str) -> str:
    """Remove markdown code fences from LLM output."""
    match = re.search(r"```(?:sparql)?\s*\n?(.*?)\n?\s*```", text, re.DOTALL)
    if match:
        return match.group(1).strip()
    return text.strip()
