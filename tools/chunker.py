"""Deterministic Markdown chunker.

Splits Markdown documents into chunks at heading boundaries,
packing paragraphs up to a target token count. Produces stable
chunk IDs via sha256 hashing.
"""

import hashlib
import re
import yaml
from dataclasses import dataclass, field, asdict
from pathlib import Path


@dataclass
class Chunk:
    doc_id: str
    chunk_id: str
    heading_path: list[str]
    text: str
    char_start: int
    char_end: int

    def to_dict(self) -> dict:
        return asdict(self)


def _estimate_tokens(text: str) -> int:
    """Rough token estimate: ~4 chars per token for English."""
    return len(text) // 4


def _normalize_text(text: str) -> str:
    """Normalize whitespace for stable hashing."""
    return re.sub(r"\s+", " ", text).strip()


def _compute_chunk_id(text: str) -> str:
    """Deterministic chunk ID from normalized text content."""
    normalized = _normalize_text(text)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:16]


def parse_frontmatter(content: str) -> tuple[dict, str]:
    """Extract YAML frontmatter and return (metadata, body)."""
    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            try:
                meta = yaml.safe_load(parts[1]) or {}
            except yaml.YAMLError:
                meta = {}
            body = parts[2]
            return meta, body
    return {}, content


def _split_into_sections(body: str) -> list[tuple[str, str, int]]:
    """Split body into (heading, text, char_offset) tuples at H1/H2 boundaries."""
    heading_pattern = re.compile(r"^(#{1,2})\s+(.+)$", re.MULTILINE)
    sections = []
    last_end = 0
    last_heading = ""

    for m in heading_pattern.finditer(body):
        if last_end < m.start():
            text = body[last_end : m.start()]
            if text.strip():
                sections.append((last_heading, text, last_end))
        last_heading = m.group(2).strip()
        last_end = m.end()

    # Remaining text after last heading
    if last_end < len(body):
        text = body[last_end:]
        if text.strip():
            sections.append((last_heading, text, last_end))

    return sections


def chunk_document(
    content: str,
    doc_id: str,
    token_target: int = 750,
) -> list[Chunk]:
    """Chunk a Markdown document into pieces suitable for LLM extraction.

    Args:
        content: Full Markdown file content (with frontmatter).
        doc_id: Canonical document identifier (URL or path-based).
        token_target: Target token count per chunk.

    Returns:
        List of Chunk objects with stable IDs.
    """
    meta, body = parse_frontmatter(content)
    sections = _split_into_sections(body)

    if not sections:
        # Single-section document
        text = body.strip()
        if not text:
            return []
        chunk_id = _compute_chunk_id(text)
        return [
            Chunk(
                doc_id=doc_id,
                chunk_id=chunk_id,
                heading_path=[],
                text=text,
                char_start=0,
                char_end=len(content),
            )
        ]

    chunks = []
    current_text = ""
    current_heading_path: list[str] = []
    current_start = 0

    # Account for frontmatter offset
    _, body_text = parse_frontmatter(content)
    fm_offset = content.index(body_text) if body_text in content else 0

    for heading, text, offset in sections:
        abs_offset = fm_offset + offset

        if current_text and _estimate_tokens(current_text + text) > token_target:
            # Flush current buffer
            chunk_id = _compute_chunk_id(current_text)
            chunks.append(
                Chunk(
                    doc_id=doc_id,
                    chunk_id=chunk_id,
                    heading_path=list(current_heading_path),
                    text=current_text.strip(),
                    char_start=current_start,
                    char_end=current_start + len(current_text),
                )
            )
            current_text = ""
            current_start = abs_offset

        if not current_text:
            current_start = abs_offset
            current_heading_path = [heading] if heading else []
        elif heading and heading not in current_heading_path:
            current_heading_path.append(heading)

        current_text += text

    # Flush final buffer
    if current_text.strip():
        chunk_id = _compute_chunk_id(current_text)
        chunks.append(
            Chunk(
                doc_id=doc_id,
                chunk_id=chunk_id,
                heading_path=list(current_heading_path),
                text=current_text.strip(),
                char_start=current_start,
                char_end=current_start + len(current_text),
            )
        )

    return chunks


def doc_id_from_path(file_path: str, base_url: str = "https://example.com") -> str:
    """Derive a canonical document ID from file path.

    content/2026/04/my-article.md → https://example.com/2026/04/my-article/
    """
    p = Path(file_path)
    # Strip content/ prefix if present
    parts = list(p.parts)
    if parts and parts[0] == "content":
        parts = parts[1:]
    slug = p.stem
    path_parts = parts[:-1]  # directories only
    canonical = "/".join(path_parts + [slug])
    return f"{base_url}/{canonical}/"
