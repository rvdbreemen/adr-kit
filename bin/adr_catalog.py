"""Shared, deterministic ADR catalog and relationship graph helpers.

Markdown ADR files remain authoritative.  This module projects their invariant
frontmatter and format-aware semantic sections into records consumed by
``adr-index``, ``adr-context``, and ``adr-related``.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

from adr_format import SUPPORTED_PROFILES, detect_profile, section_text
from adr_schema import (
    FrontmatterError,
    infer_frontmatter,
    parse_frontmatter,
    split_frontmatter,
)


GRAPH_SCHEMA_VERSION = 1
GRAPH_SCHEMA_REF = "../../schemas/adr-index.schema.json"
DECISION_SUMMARY_MAX = 120

ADR_FILENAME_RE = re.compile(r"(?i)^ADR-(\d{1,4})-.*\.md$")
ADR_TOKEN_RE = re.compile(r"\bADR-(\d{1,4})\b", re.IGNORECASE)
AMENDED_BY_RE = re.compile(r"\bAmended\s+by\s+ADR-(\d{1,4})\b", re.IGNORECASE)
ENFORCEMENT_BLOCK_RE = re.compile(
    r"^##\s+Enforcement\s*$\n+.*?```json\s*\n(.*?)\n```",
    re.IGNORECASE | re.MULTILINE | re.DOTALL,
)


def normalize_adr_id(raw: object) -> Optional[str]:
    match = ADR_TOKEN_RE.search(str(raw))
    if not match:
        return None
    return f"ADR-{int(match.group(1)):03d}"


def discover_adr_files(adr_dir: Path) -> List[Path]:
    if not adr_dir.is_dir():
        return []
    return sorted(
        (
            path
            for path in adr_dir.glob("ADR-*.md")
            if ADR_FILENAME_RE.match(path.name)
        ),
        key=lambda path: path.name.casefold(),
    )


def enforcement_globs(text: str) -> List[str]:
    """Return the stable, de-duplicated path_glob scope from Enforcement."""
    match = ENFORCEMENT_BLOCK_RE.search(text)
    if not match:
        return []
    try:
        data = json.loads(match.group(1))
    except json.JSONDecodeError:
        return []
    if not isinstance(data, dict):
        return []

    globs: List[str] = []
    for kind in ("forbid_pattern", "forbid_import", "require_pattern"):
        rules = data.get(kind)
        if not isinstance(rules, list):
            continue
        for rule in rules:
            if not isinstance(rule, dict):
                continue
            path_glob = rule.get("path_glob")
            globs.append(path_glob if isinstance(path_glob, str) and path_glob else "**")
    return list(dict.fromkeys(globs))


def _plain_markdown(value: str) -> str:
    value = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", value)
    value = re.sub(r"<[^>]+>", " ", value)
    value = value.replace("`", "").replace("*", "").replace("_", "")
    value = re.sub(r"^\s*(?:[-+]|\d+[.)])\s+", "", value)
    return re.sub(r"\s+", " ", value).strip()


def decision_summary(text: str) -> str:
    """Return the first meaningful decision paragraph as bounded plain text."""
    decision = section_text(text, "decision")
    if not decision:
        return ""

    paragraph: List[str] = []
    for raw_line in decision.splitlines():
        line = raw_line.strip()
        if not line:
            if paragraph:
                break
            continue
        if line.startswith(("#", "```", "<!--", "-->")):
            if paragraph:
                break
            continue
        paragraph.append(line)

    summary = _plain_markdown(" ".join(paragraph))
    sentence_match = re.match(r"^(.+?[.!?])(?:\s|$)", summary)
    if sentence_match:
        summary = sentence_match.group(1)
    if len(summary) > DECISION_SUMMARY_MAX:
        summary = summary[: DECISION_SUMMARY_MAX - 3].rstrip() + "..."
    return summary


def _status_history(text: str) -> List[Dict[str, str]]:
    """Parse adr-kit's deliberately small status_history YAML subset."""
    history = section_text(text, "history")
    entries: List[Dict[str, str]] = []
    current: Optional[Dict[str, str]] = None
    for raw_line in history.splitlines():
        stripped = raw_line.strip()
        if stripped.startswith("- date:"):
            if current:
                entries.append(current)
            current = {"date": stripped.split(":", 1)[1].strip().strip("\"'")}
            continue
        if current is None or ":" not in stripped:
            continue
        key, value = stripped.split(":", 1)
        if key in {"status", "changed_by", "reason", "changed_via"}:
            current[key] = value.strip().strip("\"'")
    if current:
        entries.append(current)
    return entries


def _ids(values: object) -> List[str]:
    if values is None:
        return []
    items = values if isinstance(values, list) else [values]
    normalized = [normalize_adr_id(value) for value in items]
    return sorted({item for item in normalized if item})


def _strings(values: object) -> List[str]:
    if values is None:
        return []
    items = values if isinstance(values, list) else [values]
    return [str(item) for item in items if str(item)]


def _related_ids(text: str) -> List[str]:
    related = section_text(text, "related")
    return sorted(
        {
            f"ADR-{int(match.group(1)):03d}"
            for match in ADR_TOKEN_RE.finditer(related)
        }
    )


def load_adr_record(path: Path) -> Dict:
    """Load one ADR into the shared semantic record shape."""
    text = path.read_text(encoding="utf-8")
    raw_frontmatter, body = split_frontmatter(text)
    try:
        declared = parse_frontmatter(raw_frontmatter)
    except FrontmatterError:
        # Index and retrieval are tolerant readers. Strict lint reports the
        # malformed metadata; discovery still falls back to invariant prose.
        declared = {}
    inferred = infer_frontmatter(body, path)
    metadata = dict(inferred)
    metadata.update(declared)

    history = _status_history(text)
    latest = history[-1] if history else {}
    status = str(latest.get("status") or metadata.get("status") or "Unknown").capitalize()
    status_date = latest.get("date") or metadata.get("date")

    detected_format = detect_profile(text)
    declared_format = metadata.get("format")
    profile = (
        str(declared_format).casefold()
        if declared_format in SUPPORTED_PROFILES
        else detected_format
    )

    adr_id = normalize_adr_id(metadata.get("id")) or normalize_adr_id(path.name)
    if adr_id is None:
        adr_id = path.stem

    related_ids = [item for item in _related_ids(text) if item != adr_id]
    supersedes = [item for item in _ids(metadata.get("supersedes")) if item != adr_id]
    superseded_by = normalize_adr_id(metadata.get("superseded_by"))
    if superseded_by == adr_id:
        superseded_by = None
    amended_by = sorted(
        {
            f"ADR-{int(match.group(1)):03d}"
            for match in AMENDED_BY_RE.finditer(text)
            if f"ADR-{int(match.group(1)):03d}" != adr_id
        }
    )

    decision_text = section_text(text, "decision")
    return {
        "num": int(re.search(r"\d+", adr_id).group(0)) if normalize_adr_id(adr_id) else 0,
        "adr_id": adr_id,
        "title": str(metadata.get("title") or inferred.get("title") or path.stem),
        "path": path.name,
        "format": profile,
        "status": status,
        "date": str(status_date) if status_date else None,
        "decision": decision_summary(text),
        "decision_text": decision_text,
        "scope": enforcement_globs(text),
        "binding": bool(metadata.get("binding", False)),
        "gate": metadata.get("gate"),
        "documents_shipped": bool(metadata.get("documents_shipped", False)),
        "verified_in": _strings(metadata.get("verified_in")),
        "supersedes": supersedes,
        "superseded_by": superseded_by,
        "related_ids": related_ids,
        "amended_by": amended_by,
        "_source_path": path,
    }


def load_adr_records(adr_dir: Path) -> List[Dict]:
    records = [load_adr_record(path) for path in discover_adr_files(adr_dir)]
    records.sort(key=lambda row: (row["num"], row["adr_id"]))
    return records


def build_relationships(records: Iterable[Dict]) -> List[Dict]:
    """Return sorted, de-duplicated declared relationship edges."""
    record_list = list(records)
    known_ids = {record["adr_id"] for record in record_list}
    edge_keys = set()
    relationships: List[Dict] = []

    def add(source: str, target: Optional[str], kind: str) -> None:
        if not target or source == target:
            return
        key = (source, target, kind)
        if key in edge_keys:
            return
        edge_keys.add(key)
        relationships.append(
            {
                "source": source,
                "target": target,
                "type": kind,
                "resolved": target in known_ids,
            }
        )

    for record in record_list:
        source = record["adr_id"]
        for target in record.get("related_ids", []):
            add(source, target, "related")
        for target in record.get("supersedes", []):
            add(source, target, "supersedes")
        add(source, record.get("superseded_by"), "superseded-by")
        for target in record.get("amended_by", []):
            add(source, target, "amended-by")

    relationships.sort(key=lambda edge: (edge["source"], edge["target"], edge["type"]))
    return relationships


def public_adr_node(record: Dict) -> Dict:
    return {
        "id": record["adr_id"],
        "title": record["title"],
        "path": record["path"],
        "format": record["format"],
        "status": record["status"],
        "date": record["date"],
        "decision_summary": record["decision"],
        "scope": {"path_globs": record["scope"]},
        "metadata": {
            "binding": record["binding"],
            "gate": record["gate"],
            "documents_shipped": record["documents_shipped"],
            "verified_in": record["verified_in"],
            "supersedes": record["supersedes"],
            "superseded_by": record["superseded_by"],
        },
    }


def build_graph_document(
    records: Iterable[Dict],
    *,
    schema_ref: str = GRAPH_SCHEMA_REF,
) -> Dict:
    record_list = list(records)
    return {
        "$schema": schema_ref,
        "schema_version": GRAPH_SCHEMA_VERSION,
        "adrs": [public_adr_node(record) for record in record_list],
        "relationships": build_relationships(record_list),
    }
