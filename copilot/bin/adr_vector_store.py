"""The precomputed vector store ADR-018 permits (gate adr-vector-store-v1).

Lexical retrieval misses on vocabulary. A developer asks "should the commit hook
still run when the model is unreachable?" and the governing ADR says "fail open
on tooling drift"; no token overlaps, so the decision is not retrieved and the
agent proceeds without it. That miss is the reason this file exists.

The boundary ADR-018 draws, restated where the code lives:

**Built in an explicit step, read everywhere else.** `build()` may call a model.
`load()` and `search()` do arithmetic on a file and nothing else - no model, no
daemon, no network, no third-party import. That is what keeps the hook path
inside the 2 s budget of ADR-015 and the zero-dependency posture of ADR-016.

**Staleness is detectable, never silent.** Every entry carries the identity of
the model that produced it, the vector dimension, and a content hash of the ADR
it came from. Any mismatch marks the store stale, and a stale store falls back
to lexical ranking with a visible reason. A wrong answer that announces itself
is worth more than a right answer that might not be.

**Similarity generates candidates; it never confers authority.** Lifecycle
status decides what governs, exactly as ADR-014 specified and ADR-018 kept.
Status and the superseded-by link travel with each entry so a historical
decision stays findable and stays non-governing.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import tempfile
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

STORE_NAME = ".adr-kit-vectors.json"
SCHEMA_VERSION = 1

# Enough of the record to carry meaning without embedding the whole file: the
# decision plus the metadata a reader would match on. Embedding the entire ADR
# would dilute the vector with boilerplate every record shares.
EMBED_SECTIONS = ("title", "topics", "aliases", "components", "decision")


def content_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def _atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    handle = tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", newline="", dir=path.parent,
        prefix=f".{path.name}.", suffix=".tmp", delete=False,
    )
    try:
        with handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(handle.name, path)
    except BaseException:
        Path(handle.name).unlink(missing_ok=True)
        raise


def store_path(adr_dir: Path) -> Path:
    return Path(adr_dir) / STORE_NAME


def embed_text(record: Dict) -> str:
    """The text that represents one ADR to the embedder."""
    parts: List[str] = []
    for field in EMBED_SECTIONS:
        value = record.get(field)
        if isinstance(value, str) and value.strip():
            parts.append(value.strip())
        elif isinstance(value, list) and value:
            parts.append(" ".join(str(item) for item in value))
    return "\n".join(parts)


def build_entries(records: Iterable[Dict], vectors: List[List[float]]) -> List[Dict]:
    entries: List[Dict] = []
    for record, vector in zip(records, vectors):
        entries.append(
            {
                "adr_id": record.get("adr_id") or record.get("id"),
                "title": record.get("title", ""),
                "path": record.get("path", ""),
                "status": record.get("status", "Unknown"),
                "superseded_by": record.get("superseded_by"),
                "content_hash": content_hash(embed_text(record)),
                "vector": vector,
            }
        )
    return entries


def write_store(
    adr_dir: Path, entries: List[Dict], model: str, backend: str, built_at: str
) -> Path:
    dimension = len(entries[0]["vector"]) if entries else 0
    document = {
        "schema_version": SCHEMA_VERSION,
        "model": model,
        "backend": backend,
        "dimension": dimension,
        "built_at": built_at,
        "entries": entries,
    }
    path = store_path(adr_dir)
    _atomic_write(path, json.dumps(document, ensure_ascii=False) + "\n")
    return path


def load_store(adr_dir: Path) -> Tuple[Optional[Dict], Optional[str]]:
    """Return (store, reason_it_is_unusable). Never raises."""
    path = store_path(adr_dir)
    if not path.exists():
        return None, "no vector store present"
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        return None, f"vector store is unreadable ({exc})"
    if not isinstance(document, dict):
        return None, "vector store is not a JSON object"
    if document.get("schema_version") != SCHEMA_VERSION:
        return None, (
            f"vector store schema {document.get('schema_version')!r} is not "
            f"{SCHEMA_VERSION}; rebuild it"
        )
    entries = document.get("entries")
    if not isinstance(entries, list):
        return None, "vector store has no entries"
    dimension = document.get("dimension")
    for entry in entries:
        vector = (entry or {}).get("vector")
        if not isinstance(vector, list) or len(vector) != dimension:
            return None, (
                f"vector store entry {entry.get('adr_id')!r} has the wrong "
                f"dimension; the model likely changed. Rebuild it."
            )
    return document, None


def staleness(store: Dict, records: Iterable[Dict]) -> Dict:
    """Compare a loaded store against the ADRs as they are now."""
    by_id = {entry.get("adr_id"): entry for entry in store.get("entries", [])}
    changed: List[str] = []
    missing: List[str] = []
    seen = set()
    for record in records:
        adr_id = record.get("adr_id") or record.get("id")
        seen.add(adr_id)
        entry = by_id.get(adr_id)
        if entry is None:
            missing.append(adr_id)
            continue
        if entry.get("content_hash") != content_hash(embed_text(record)):
            changed.append(adr_id)
    removed = sorted(set(by_id) - seen)
    return {
        "changed": sorted(changed),
        "missing": sorted(missing),
        "removed": removed,
        "stale": bool(changed or missing or removed),
    }


def cosine(left: List[float], right: List[float]) -> float:
    """Plain-stdlib cosine.

    No numpy: ADR-016 makes zero runtime dependencies load-bearing, and an ADR
    set is small enough that a dot product in Python is not the bottleneck. A
    few hundred records at a few hundred dimensions is well inside the budget.
    """
    dot = 0.0
    left_norm = 0.0
    right_norm = 0.0
    for a, b in zip(left, right):
        dot += a * b
        left_norm += a * a
        right_norm += b * b
    if left_norm <= 0.0 or right_norm <= 0.0:
        return 0.0
    return dot / (math.sqrt(left_norm) * math.sqrt(right_norm))


def search(
    store: Dict,
    query_vector: List[float],
    limit: int = 10,
    include_historical: bool = False,
) -> List[Dict]:
    """Rank candidates by similarity, carrying lifecycle status untouched.

    Historical decisions are excluded by default and never promoted by a score:
    ADR-014's rule that relevance and authority are different axes survives here
    unchanged. Ask for them explicitly and they arrive clearly marked.
    """
    historical = {"Superseded", "Rejected", "Deprecated"}
    scored: List[Dict] = []
    for entry in store.get("entries", []):
        status = entry.get("status", "Unknown")
        if status in historical and not include_historical:
            continue
        scored.append(
            {
                "adr_id": entry.get("adr_id"),
                "title": entry.get("title", ""),
                "path": entry.get("path", ""),
                "status": status,
                "superseded_by": entry.get("superseded_by"),
                "authority": "governing" if status == "Accepted" else (
                    "advisory" if status == "Proposed" else "historical"
                ),
                "similarity": round(cosine(query_vector, entry.get("vector") or []), 6),
            }
        )
    scored.sort(key=lambda row: (-row["similarity"], str(row["adr_id"])))
    return scored[:limit]
