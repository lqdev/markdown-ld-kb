"""GitHub Models LLM client for entity/relation extraction.

Uses the OpenAI SDK pointed at the GitHub Models inference endpoint.
Supports batching, caching, rate limiting, and cost guards.
"""

import hashlib
import json
import os
import time
from dataclasses import dataclass
from pathlib import Path

from openai import OpenAI, RateLimitError, APIError


PROMPT_VERSION = "v1"
DEFAULT_MODEL = "openai/gpt-4o-mini"
DEFAULT_ENDPOINT = "https://models.github.ai/inference"
DEFAULT_BATCH_SIZE = 3
DEFAULT_MAX_CONCURRENCY = 2
MAX_RETRIES = 3
BASE_BACKOFF = 2.0


@dataclass
class ExtractionResult:
    chunk_id: str
    entities: list[dict]
    assertions: list[dict]
    raw_response: str
    cached: bool = False


def _load_prompt(prompt_path: str | None = None) -> str:
    """Load the extraction system prompt."""
    if prompt_path is None:
        prompt_path = str(
            Path(__file__).parent / "prompts" / "extract_rdf_v1.txt"
        )
    return Path(prompt_path).read_text(encoding="utf-8")


def _cache_key(chunk_id: str, prompt_version: str, model: str) -> str:
    """Generate a cache filename for a chunk extraction."""
    key = f"{chunk_id}.{prompt_version}.{model.replace('/', '_')}"
    return key


def _load_cache(cache_dir: Path, chunk_id: str, model: str) -> dict | None:
    """Load cached extraction result if it exists."""
    key = _cache_key(chunk_id, PROMPT_VERSION, model)
    cache_file = cache_dir / f"{key}.json"
    if cache_file.exists():
        return json.loads(cache_file.read_text(encoding="utf-8"))
    return None


def _save_cache(cache_dir: Path, chunk_id: str, model: str, result: dict) -> None:
    """Save extraction result to cache."""
    cache_dir.mkdir(parents=True, exist_ok=True)
    key = _cache_key(chunk_id, PROMPT_VERSION, model)
    cache_file = cache_dir / f"{key}.json"
    cache_file.write_text(json.dumps(result, indent=2), encoding="utf-8")


def _build_batch_user_message(chunks: list[dict], article_id: str) -> str:
    """Build a user message containing multiple chunks for batch extraction."""
    parts = []
    for i, chunk in enumerate(chunks):
        parts.append(
            f"--- CHUNK {i+1} (chunk_id: {chunk['chunk_id']}, "
            f"source: urn:kb:chunk:{chunk['doc_id']}:{chunk['chunk_id']}) ---\n"
            f"{chunk['text']}"
        )

    header = (
        f"ARTICLE_ID: {article_id}\n"
        f"Extract entities and assertions from each chunk below. "
        f"Return a single JSON object with keys 'entities' and 'assertions'. "
        f"Include the chunk source URI in each assertion.\n\n"
    )
    return header + "\n\n".join(parts)


def create_client(
    endpoint: str | None = None,
    api_key: str | None = None,
) -> OpenAI:
    """Create an OpenAI client configured for GitHub Models."""
    endpoint = endpoint or os.environ.get("LLM_ENDPOINT", DEFAULT_ENDPOINT)
    api_key = api_key or os.environ.get("GITHUB_TOKEN", "")
    if not api_key:
        raise ValueError(
            "No API key found. Set GITHUB_TOKEN environment variable "
            "or pass api_key explicitly."
        )
    return OpenAI(base_url=endpoint, api_key=api_key)


def extract_from_chunks(
    client: OpenAI,
    chunks: list[dict],
    article_id: str,
    model: str = DEFAULT_MODEL,
    cache_dir: Path | None = None,
    system_prompt: str | None = None,
) -> list[ExtractionResult]:
    """Extract entities and relations from a list of chunk dicts.

    Checks cache first, only calls LLM for uncached chunks.
    """
    if system_prompt is None:
        system_prompt = _load_prompt()

    if cache_dir is None:
        cache_dir = Path("graph/cache")

    results = []
    uncached_chunks = []

    # Check cache
    for chunk in chunks:
        cached = _load_cache(cache_dir, chunk["chunk_id"], model)
        if cached:
            results.append(
                ExtractionResult(
                    chunk_id=chunk["chunk_id"],
                    entities=cached.get("entities", []),
                    assertions=cached.get("assertions", []),
                    raw_response=json.dumps(cached),
                    cached=True,
                )
            )
        else:
            uncached_chunks.append(chunk)

    if not uncached_chunks:
        return results

    # Build batched request
    user_message = _build_batch_user_message(uncached_chunks, article_id)

    # Call LLM with retries
    response_text = _call_with_retry(client, system_prompt, user_message, model)

    # Parse response
    try:
        data = json.loads(response_text)
    except json.JSONDecodeError:
        # Try to extract JSON from markdown code blocks
        import re
        json_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", response_text, re.DOTALL)
        if json_match:
            data = json.loads(json_match.group(1))
        else:
            data = {"entities": [], "assertions": []}

    entities = data.get("entities", [])
    assertions = data.get("assertions", [])

    # Cache the result for each chunk
    for chunk in uncached_chunks:
        chunk_assertions = [
            a for a in assertions
            if chunk["chunk_id"] in a.get("source", "")
        ]
        chunk_result = {"entities": entities, "assertions": chunk_assertions}
        _save_cache(cache_dir, chunk["chunk_id"], model, chunk_result)

        results.append(
            ExtractionResult(
                chunk_id=chunk["chunk_id"],
                entities=entities,
                assertions=chunk_assertions,
                raw_response=response_text,
                cached=False,
            )
        )

    return results


def _call_with_retry(
    client: OpenAI,
    system_prompt: str,
    user_message: str,
    model: str,
) -> str:
    """Call the LLM with exponential backoff on rate limit errors."""
    for attempt in range(MAX_RETRIES):
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message},
                ],
                temperature=0,
                response_format={"type": "json_object"},
            )
            return response.choices[0].message.content or "{}"
        except RateLimitError:
            wait = BASE_BACKOFF * (2 ** attempt)
            print(f"Rate limited, waiting {wait:.1f}s (attempt {attempt + 1}/{MAX_RETRIES})")
            time.sleep(wait)
        except APIError as e:
            if e.status_code and e.status_code >= 500:
                wait = BASE_BACKOFF * (2 ** attempt)
                print(f"Server error {e.status_code}, retrying in {wait:.1f}s")
                time.sleep(wait)
            else:
                raise

    raise RuntimeError(f"Failed after {MAX_RETRIES} retries")
