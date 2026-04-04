"""Knowledge Graph build orchestrator.

Detects changed Markdown files, chunks them, extracts entities/relations
via LLM, post-processes, validates, and writes graph artifacts.
"""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from glob import glob

from tools.chunker import chunk_document, doc_id_from_path, parse_frontmatter
from tools.postprocess import (
    canonicalize_entities,
    deduplicate_assertions,
    build_jsonld,
    build_turtle,
    slugify,
)


def detect_changed_docs(repo_root: str, content_glob: str) -> list[str]:
    """Detect changed Markdown files via git diff.

    Falls back to listing all files if git diff fails (e.g., first build).
    """
    try:
        result = subprocess.run(
            ["git", "diff", "--name-only", "HEAD~1", "--", content_glob],
            capture_output=True,
            text=True,
            cwd=repo_root,
        )
        if result.returncode == 0 and result.stdout.strip():
            return [
                f for f in result.stdout.strip().split("\n")
                if f.endswith(".md")
            ]
    except Exception:
        pass

    # Fallback: all matching files
    pattern = str(Path(repo_root) / content_glob)
    return [str(Path(f).relative_to(repo_root)) for f in glob(pattern, recursive=True)]


def build_manifest(
    repo_root: str,
    model: str,
    prompt_version: str,
    doc_count: int,
    chunk_count: int,
    entity_count: int,
    assertion_count: int,
) -> dict:
    """Build a manifest dict with build metadata."""
    import datetime

    git_hash = "unknown"
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True, text=True, cwd=repo_root,
        )
        if result.returncode == 0:
            git_hash = result.stdout.strip()
    except Exception:
        pass

    return {
        "build_timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "git_commit": git_hash,
        "prompt_version": prompt_version,
        "model": model,
        "docs_processed": doc_count,
        "chunks_processed": chunk_count,
        "entities_extracted": entity_count,
        "assertions_extracted": assertion_count,
    }


def build_views(
    all_entities: list[dict],
    all_articles: list[dict],
    views_dir: Path,
) -> None:
    """Generate precomputed JSON views for static serving."""
    views_dir.mkdir(parents=True, exist_ok=True)

    # Entities index
    entities_view = [
        {"id": e["id"], "label": e["label"], "type": e["type"]}
        for e in all_entities
    ]
    (views_dir / "entities.json").write_text(
        json.dumps(entities_view, indent=2), encoding="utf-8"
    )

    # Articles by tag
    by_tag: dict[str, list] = {}
    for art in all_articles:
        for tag in art.get("tags", []):
            by_tag.setdefault(tag, []).append(
                {"id": art["id"], "title": art.get("title", "")}
            )
    (views_dir / "articles_by_tag.json").write_text(
        json.dumps(by_tag, indent=2), encoding="utf-8"
    )


def main():
    parser = argparse.ArgumentParser(description="Build knowledge graph from Markdown")
    parser.add_argument("--repo-root", default=".", help="Repository root directory")
    parser.add_argument("--content-glob", default="content/**/*.md", help="Glob for Markdown files")
    parser.add_argument("--out-dir", default="graph", help="Output directory for graph artifacts")
    parser.add_argument("--base-url", default="https://example.com", help="Base URL for entity IDs")
    parser.add_argument("--model", default=None, help="LLM model (default: from env or openai/gpt-4o-mini)")
    parser.add_argument("--batch-size", type=int, default=3, help="Chunks per LLM request")
    parser.add_argument("--dry-run", action="store_true", help="Chunk only, no LLM calls")
    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve()
    out_dir = repo_root / args.out_dir
    model = args.model or os.environ.get("LLM_MODEL", "openai/gpt-4o-mini")
    base_url = args.base_url

    # Detect changed documents
    changed = detect_changed_docs(str(repo_root), args.content_glob)
    if not changed:
        print("No changed documents detected. Nothing to do.")
        return

    print(f"Processing {len(changed)} document(s)...")

    all_entities = []
    all_assertions = []
    all_articles = []
    all_chunks = []

    for doc_path in changed:
        full_path = repo_root / doc_path
        if not full_path.exists():
            print(f"  Skipping deleted file: {doc_path}")
            continue

        content = full_path.read_text(encoding="utf-8")
        meta, _ = parse_frontmatter(content)
        doc_id = meta.get("canonical_url") or doc_id_from_path(doc_path, base_url)

        print(f"  {doc_path} → {doc_id}")

        # Chunk
        chunks = chunk_document(content, doc_id, token_target=int(os.environ.get("CHUNK_TOKEN_TARGET", "750")))
        all_chunks.extend([c.to_dict() for c in chunks])
        print(f"    {len(chunks)} chunk(s)")

        if args.dry_run:
            continue

        # Extract via LLM
        try:
            from tools.llm_client import create_client, extract_from_chunks

            client = create_client()
            chunk_dicts = [c.to_dict() for c in chunks]

            # Process in batches
            for i in range(0, len(chunk_dicts), args.batch_size):
                batch = chunk_dicts[i : i + args.batch_size]
                results = extract_from_chunks(
                    client, batch, doc_id,
                    model=model,
                    cache_dir=out_dir / "cache",
                )
                for r in results:
                    all_entities.extend(r.entities)
                    all_assertions.extend(r.assertions)
                    cache_status = "cached" if r.cached else "extracted"
                    print(f"    chunk {r.chunk_id}: {cache_status}")
        except Exception as e:
            print(f"    LLM extraction failed: {e}")
            print("    Continuing with empty extraction...")

        # Track article metadata
        all_articles.append({
            "id": doc_id,
            "title": meta.get("title", ""),
            "tags": meta.get("tags", []),
        })

    if args.dry_run:
        print(f"\nDry run complete. {len(all_chunks)} chunks from {len(changed)} docs.")
        # Write chunks for inspection
        intermediate_dir = out_dir / "intermediate"
        intermediate_dir.mkdir(parents=True, exist_ok=True)
        with open(intermediate_dir / "chunks.jsonl", "w", encoding="utf-8") as f:
            for chunk in all_chunks:
                f.write(json.dumps(chunk) + "\n")
        print(f"Wrote chunks to {intermediate_dir / 'chunks.jsonl'}")
        return

    # Post-process
    print("\nPost-processing...")
    entities = canonicalize_entities(all_entities, base_url)
    assertions = deduplicate_assertions(all_assertions)
    print(f"  {len(entities)} unique entities, {len(assertions)} unique assertions")

    # Write outputs
    articles_dir = out_dir / "articles"
    articles_dir.mkdir(parents=True, exist_ok=True)

    for art_meta in all_articles:
        doc_id = art_meta["id"]
        slug = slugify(art_meta.get("title", "untitled"))

        # Collect assertions for this article
        art_assertions = [
            a for a in assertions
            if a.get("s", "").startswith(doc_id) or any(
                a.get("s", "") == e["id"] for e in entities
            )
        ]

        jsonld = build_jsonld(doc_id, art_meta, entities, art_assertions)
        ttl = build_turtle(doc_id, art_meta, entities, art_assertions)

        (articles_dir / f"{slug}.jsonld").write_text(
            json.dumps(jsonld, indent=2), encoding="utf-8"
        )
        (articles_dir / f"{slug}.ttl").write_text(ttl, encoding="utf-8")

    # Write intermediate chunks
    intermediate_dir = out_dir / "intermediate"
    intermediate_dir.mkdir(parents=True, exist_ok=True)
    with open(intermediate_dir / "chunks.jsonl", "w", encoding="utf-8") as f:
        for chunk in all_chunks:
            f.write(json.dumps(chunk) + "\n")

    # Write views
    build_views(entities, all_articles, out_dir / "views")

    # Write manifest
    from tools.llm_client import PROMPT_VERSION
    manifest = build_manifest(
        str(repo_root), model, PROMPT_VERSION,
        len(changed), len(all_chunks),
        len(entities), len(assertions),
    )
    (out_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )

    print(f"\nBuild complete:")
    print(f"  {len(changed)} docs → {len(all_chunks)} chunks")
    print(f"  {len(entities)} entities, {len(assertions)} assertions")
    print(f"  Artifacts written to {out_dir}/")


if __name__ == "__main__":
    main()
