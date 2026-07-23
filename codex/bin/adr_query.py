"""Deterministic index-first ADR retrieval.

``index-first-retrieval`` is the named verification gate for ADR-014.
Markdown ADRs remain authoritative; this module queries their generated graph
projection and uses the semantic Markdown loader only as a visible fallback.
"""

from __future__ import annotations

import fnmatch
import json
import re
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

INDEX_FIRST_RETRIEVAL_GATE = "index-first-retrieval"
SUPPORTED_SCHEMA_VERSIONS = {1, 2}
SUPPORTED_STATUSES = {
    "Accepted",
    "Proposed",
    "Superseded",
    "Rejected",
    "Deprecated",
    "Amended",
    "Unknown",
}
SUPPORTED_AUTHORITIES = {"governing", "advisory", "historical"}
HISTORICAL_STATUSES = {
    "Superseded",
    "Rejected",
    "Deprecated",
    "Amended",
    "Unknown",
}
FIELD_WEIGHTS = {
    "path": 1.0,
    "symbols": 0.95,
    "components": 0.90,
    "topics": 0.75,
    "aliases": 0.70,
    "title": 0.60,
    "decision_contract": 0.50,
    "decision_summary": 0.40,
}
MAX_SUPPORTING_RESULTS = 2


class IndexQueryError(RuntimeError):
    """Raised when strict index retrieval cannot use the generated graph."""


def extract_keywords(value: str) -> List[str]:
    return sorted(
        {
            token
            for token in re.split(r"[^a-z0-9_.:/-]+", value.casefold())
            if len(token) >= 3
        }
    )


def _normalized_text(value: object) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip().casefold()


def _string_list(value: object) -> List[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str) and item.strip()]


def _empty_contract() -> Dict[str, List[str]]:
    return {
        "must": [],
        "must_not": [],
        "exceptions": [],
        "verification": [],
    }


def _normalize_contract(value: object) -> Dict[str, List[str]]:
    contract = _empty_contract()
    if not isinstance(value, dict):
        return contract
    for key in contract:
        contract[key] = _string_list(value.get(key))[:20]
    return contract


def _validate_node(node: object, version: int) -> Dict:
    if not isinstance(node, dict):
        raise IndexQueryError("ADR graph contains a non-object ADR record")
    required = {
        "id",
        "title",
        "path",
        "format",
        "status",
        "date",
        "decision_summary",
        "scope",
        "metadata",
    }
    missing = sorted(required - set(node))
    if missing:
        raise IndexQueryError(
            "ADR graph record is missing required field(s): " + ", ".join(missing)
        )
    adr_id = node.get("id")
    if not isinstance(adr_id, str) or not re.fullmatch(r"ADR-\d{3,4}", adr_id):
        raise IndexQueryError(f"ADR graph record has invalid id: {adr_id!r}")
    if not isinstance(node.get("title"), str) or not isinstance(node.get("path"), str):
        raise IndexQueryError(f"{adr_id} title/path must be strings")
    if not isinstance(node.get("scope"), dict) or not isinstance(
        node["scope"].get("path_globs"), list
    ):
        raise IndexQueryError(f"{adr_id} scope.path_globs must be a list")
    if not isinstance(node.get("metadata"), dict):
        raise IndexQueryError(f"{adr_id} metadata must be an object")

    normalized = dict(node)
    if version == 2:
        retrieval_required = {
            "topics",
            "aliases",
            "components",
            "symbols",
            "context_scope",
            "decision_contract",
        }
        missing_retrieval = sorted(retrieval_required - set(node))
        if missing_retrieval:
            raise IndexQueryError(
                f"{adr_id} schema-v2 retrieval field(s) missing: "
                + ", ".join(missing_retrieval)
            )
    for field in ("topics", "aliases", "components", "symbols"):
        value = node.get(field, [])
        if version == 2 and (
            not isinstance(value, list)
            or not all(isinstance(item, str) and item for item in value)
        ):
            raise IndexQueryError(f"{adr_id} {field} must be a list")
        normalized[field] = _string_list(value)
    context_scope = node.get("context_scope", "selective")
    if version == 2 and context_scope not in {"global", "selective"}:
        raise IndexQueryError(f"{adr_id} context_scope is invalid")
    normalized["context_scope"] = (
        context_scope if context_scope in {"global", "selective"} else "selective"
    )
    contract = node.get("decision_contract")
    if version == 2:
        contract_keys = {"must", "must_not", "exceptions", "verification"}
        if (
            not isinstance(contract, dict)
            or set(contract) != contract_keys
            or any(
                not isinstance(contract.get(key), list)
                or not all(
                    isinstance(item, str) and item
                    for item in contract.get(key, [])
                )
                for key in contract_keys
            )
        ):
            raise IndexQueryError(f"{adr_id} decision_contract is invalid")
    normalized["decision_contract"] = _normalize_contract(contract)
    return normalized


def _validate_relationship(value: object) -> Dict:
    if not isinstance(value, dict):
        raise IndexQueryError("ADR graph contains a non-object relationship")
    required = {"source", "target", "type", "resolved"}
    if not required <= set(value):
        raise IndexQueryError("ADR graph relationship is incomplete")
    if not all(isinstance(value.get(key), str) for key in ("source", "target", "type")):
        raise IndexQueryError("ADR graph relationship identifiers must be strings")
    if not isinstance(value.get("resolved"), bool):
        raise IndexQueryError("ADR graph relationship resolved must be boolean")
    return dict(value)


def _index_path(adr_dir: Path) -> Path:
    return adr_dir / "ADR-INDEX.json"


def _is_stale(index_path: Path, adr_dir: Path) -> bool:
    try:
        index_mtime = index_path.stat().st_mtime_ns
        source_mtimes = (
            path.stat().st_mtime_ns
            for path in adr_dir.glob("ADR-*.md")
            if re.match(r"ADR-\d{1,4}-.*\.md$", path.name, re.IGNORECASE)
        )
        return any(mtime > index_mtime for mtime in source_mtimes)
    except OSError as exc:
        raise IndexQueryError(f"cannot inspect ADR graph freshness: {exc}") from exc


def load_index_graph(adr_dir: Path) -> Tuple[List[Dict], List[Dict], int]:
    path = _index_path(adr_dir)
    if not path.is_file():
        raise IndexQueryError(f"generated ADR graph is missing: {path}")
    if _is_stale(path, adr_dir):
        raise IndexQueryError(f"generated ADR graph is stale: {path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise IndexQueryError(f"generated ADR graph is invalid: {exc}") from exc
    if not isinstance(payload, dict):
        raise IndexQueryError("generated ADR graph root must be an object")
    version = payload.get("schema_version")
    if version not in SUPPORTED_SCHEMA_VERSIONS:
        raise IndexQueryError(
            f"unsupported ADR graph schema_version {version!r}; "
            "supported versions are 1 and 2"
        )
    adrs = payload.get("adrs")
    relationships = payload.get("relationships")
    if not isinstance(adrs, list) or not isinstance(relationships, list):
        raise IndexQueryError("generated ADR graph requires adrs and relationships arrays")
    records = [_validate_node(node, version) for node in adrs]
    ids = [record["id"] for record in records]
    if len(ids) != len(set(ids)):
        raise IndexQueryError("generated ADR graph contains duplicate ADR ids")
    edges = [_validate_relationship(edge) for edge in relationships]
    return records, edges, version


def _markdown_graph(adr_dir: Path) -> Tuple[List[Dict], List[Dict]]:
    # Keep the semantic Markdown stack off the healthy index hot path. Its
    # format/frontmatter imports are paid only for an explicit fallback.
    from adr_catalog import build_relationships, load_adr_records, public_adr_node

    records = load_adr_records(adr_dir)
    return (
        [public_adr_node(record) for record in records],
        build_relationships(records),
    )


def _contract_values(record: Dict) -> List[str]:
    contract = record.get("decision_contract", {})
    if not isinstance(contract, dict):
        return []
    return [
        item
        for key in ("must", "must_not", "exceptions", "verification")
        for item in _string_list(contract.get(key))
    ]


def _explicit_matches(values: Iterable[str], explicit: Sequence[str]) -> List[str]:
    requested = {_normalized_text(value) for value in explicit if str(value).strip()}
    return sorted(
        {
            value
            for value in values
            if _normalized_text(value) in requested
        },
        key=lambda item: (item.casefold(), item),
    )


def _lexical_matches(
    values: Iterable[str],
    normalized_query: str,
    query_keywords: Sequence[str],
) -> Tuple[List[str], int]:
    query_set = set(query_keywords)
    matched_values: List[str] = []
    matched_tokens = set()
    for value in values:
        normalized = _normalized_text(value)
        direct = bool(
            normalized
            and normalized_query
            and (
                normalized in normalized_query
                or normalized_query in normalized
            )
        )
        overlap = set() if direct else query_set & set(extract_keywords(normalized))
        if direct or overlap:
            matched_values.append(value)
            matched_tokens.update(query_set if direct else overlap)
    return (
        sorted(set(matched_values), key=lambda item: (item.casefold(), item)),
        len(matched_tokens),
    )


def _path_matches(globs: Iterable[str], paths: Sequence[str]) -> List[str]:
    matches = set()
    for raw_path in paths:
        normalized_path = str(raw_path).replace("\\", "/")
        for glob in globs:
            normalized_glob = str(glob).replace("\\", "/")
            if fnmatch.fnmatchcase(normalized_path.casefold(), normalized_glob.casefold()):
                matches.add(str(glob))
    return sorted(matches, key=lambda item: (item.casefold(), item))


def score_record(
    record: Dict,
    query: str,
    *,
    paths: Sequence[str] = (),
    symbols: Sequence[str] = (),
    components: Sequence[str] = (),
    topics: Sequence[str] = (),
    _query_keywords: Optional[Sequence[str]] = None,
    _normalized_query_value: Optional[str] = None,
) -> Dict:
    """Score one graph node from positive field evidence only."""
    query_keywords = list(_query_keywords or extract_keywords(query))
    normalized_query = (
        _normalized_query_value
        if _normalized_query_value is not None
        else _normalized_text(query)
    )
    denominator = max(1, len(query_keywords))
    signals: Dict[str, float] = {}
    matches: List[Dict[str, object]] = []

    path_hits = _path_matches(
        record.get("scope", {}).get("path_globs", []),
        paths,
    )
    if path_hits:
        signals["path"] = FIELD_WEIGHTS["path"]
        matches.append({"field": "path", "values": path_hits})

    fields = (
        ("symbols", _string_list(record.get("symbols")), symbols),
        ("components", _string_list(record.get("components")), components),
        ("topics", _string_list(record.get("topics")), topics),
        ("aliases", _string_list(record.get("aliases")), ()),
        ("title", [str(record.get("title", ""))], ()),
        ("decision_contract", _contract_values(record), ()),
        ("decision_summary", [str(record.get("decision_summary", ""))], ()),
    )
    for field, values, explicit in fields:
        explicit_hits = _explicit_matches(values, explicit)
        lexical_hits, matched_token_count = _lexical_matches(
            values, normalized_query, query_keywords
        )
        hits = sorted(
            set(explicit_hits + lexical_hits),
            key=lambda item: (item.casefold(), item),
        )
        if not hits:
            continue
        coverage = 1.0 if explicit_hits else matched_token_count / denominator
        if coverage <= 0:
            coverage = 1.0
        signals[field] = round(FIELD_WEIGHTS[field] * min(1.0, coverage), 4)
        matches.append({"field": field, "values": hits})
        if (
            not paths
            and not symbols
            and not components
            and not topics
            and sum(signals.values()) >= 1.0
        ):
            break

    total = round(min(1.0, sum(signals.values())), 4)
    return {"total": total, "signals": signals, "matches": matches}


def _authority(status: str) -> str:
    if status == "Accepted":
        return "governing"
    if status == "Proposed":
        return "advisory"
    return "historical"


def _adr_sort_key(adr_id: str) -> Tuple[int, str]:
    match = re.search(r"\d+", adr_id)
    return (int(match.group(0)) if match else 0, adr_id)


def _related_ids(record_id: str, relationships: Sequence[Dict]) -> List[str]:
    related = set()
    for edge in relationships:
        if edge.get("type") != "related" or edge.get("resolved") is not True:
            continue
        if edge.get("source") == record_id:
            related.add(str(edge.get("target")))
        elif edge.get("target") == record_id:
            related.add(str(edge.get("source")))
    return sorted(related, key=_adr_sort_key)


def _successor_id(record: Dict, relationships: Sequence[Dict]) -> Optional[str]:
    successor = record.get("metadata", {}).get("superseded_by")
    if isinstance(successor, str) and successor:
        return successor
    for edge in relationships:
        if (
            edge.get("source") == record.get("id")
            and edge.get("type") == "superseded-by"
            and edge.get("resolved") is True
        ):
            return str(edge.get("target"))
    return None


def _public_result(
    record: Dict,
    score: Dict,
    adr_dir: Path,
    *,
    source: str,
    schema_version: int,
    role: str = "primary",
    redirected_from: Optional[str] = None,
    related_ids: Sequence[str] = (),
) -> Dict:
    raw_path = Path(str(record["path"]))
    path = raw_path if raw_path.is_absolute() else adr_dir / raw_path
    metadata = dict(record.get("metadata", {}))
    engine = "index-first" if source.startswith("index-") else "markdown-fallback"
    return {
        "adr_id": record["id"],
        "title": record["title"],
        "path": path.as_posix(),
        "status": record["status"],
        "is_accepted": record["status"] == "Accepted",
        "authority": _authority(record["status"]),
        "role": role,
        "format": record["format"],
        "decision_summary": record["decision_summary"],
        "scope": record.get("scope", {}).get("path_globs", []),
        "related_ids": list(related_ids),
        "metadata": metadata,
        "topics": _string_list(record.get("topics")),
        "aliases": _string_list(record.get("aliases")),
        "components": _string_list(record.get("components")),
        "symbols": _string_list(record.get("symbols")),
        "context_scope": record.get("context_scope", "selective"),
        "decision_contract": _normalize_contract(record.get("decision_contract")),
        "score": score["total"],
        "signals": score["signals"],
        "matches": score["matches"],
        "source": source,
        "engine": engine,
        "schema_version": schema_version,
        "redirected_from": redirected_from,
    }


def query_records(
    records: Sequence[Dict],
    relationships: Sequence[Dict],
    query: str,
    adr_dir: Path,
    *,
    limit: int = 5,
    min_score: float = 0.1,
    include_history: bool = False,
    statuses: Sequence[str] = (),
    authorities: Sequence[str] = (),
    paths: Sequence[str] = (),
    symbols: Sequence[str] = (),
    components: Sequence[str] = (),
    topics: Sequence[str] = (),
    source: str = "index-v2",
    schema_version: int = 2,
) -> List[Dict]:
    by_id = {record["id"]: record for record in records}
    candidates: Dict[str, Dict] = {}
    redirected: Dict[str, str] = {}
    query_keywords = extract_keywords(query)
    normalized_query = _normalized_text(query)
    status_filter = set(statuses)
    authority_filter = set(authorities)

    def selected(record: Dict) -> bool:
        status = str(record.get("status"))
        return (
            (not status_filter or status in status_filter)
            and (not authority_filter or _authority(status) in authority_filter)
        )

    for record in records:
        if not selected(record):
            continue
        score = score_record(
            record,
            query,
            paths=paths,
            symbols=symbols,
            components=components,
            topics=topics,
            _query_keywords=query_keywords,
            _normalized_query_value=normalized_query,
        )
        if score["total"] < min_score:
            continue
        status = str(record.get("status"))
        if status == "Superseded" and not include_history:
            successor_id = _successor_id(record, relationships)
            successor = by_id.get(successor_id or "")
            if successor and successor.get("status") in {"Accepted", "Proposed"}:
                redirected_score = {
                    "total": score["total"],
                    "signals": dict(score["signals"]),
                    "matches": list(score["matches"])
                    + [
                        {
                            "field": "successor_redirect",
                            "values": [record["id"]],
                        }
                    ],
                }
                existing = candidates.get(successor["id"])
                if existing is None or score["total"] > existing["total"]:
                    candidates[successor["id"]] = redirected_score
                    redirected[successor["id"]] = record["id"]
            continue
        if status in HISTORICAL_STATUSES and not include_history:
            continue
        existing = candidates.get(record["id"])
        if existing is None or score["total"] > existing["total"]:
            candidates[record["id"]] = score

    ordered = sorted(
        candidates,
        key=lambda adr_id: (-candidates[adr_id]["total"], _adr_sort_key(adr_id)),
    )
    primary_ids = ordered[: max(0, limit)]
    results = [
        _public_result(
            by_id[adr_id],
            candidates[adr_id],
            adr_dir,
            source=source,
            schema_version=schema_version,
            redirected_from=redirected.get(adr_id),
            related_ids=_related_ids(adr_id, relationships),
        )
        for adr_id in primary_ids
    ]

    supporting_ids: List[str] = []
    for primary_id in primary_ids:
        for related_id in _related_ids(primary_id, relationships):
            if related_id in primary_ids or related_id in supporting_ids:
                continue
            related = by_id.get(related_id)
            if related is None:
                continue
            if not selected(related):
                continue
            if related.get("status") in HISTORICAL_STATUSES and not include_history:
                continue
            supporting_ids.append(related_id)
            if len(supporting_ids) >= MAX_SUPPORTING_RESULTS:
                break
        if len(supporting_ids) >= MAX_SUPPORTING_RESULTS:
            break

    for supporting_id in supporting_ids:
        if len(results) >= limit:
            break
        results.append(
            _public_result(
                by_id[supporting_id],
                {
                    "total": 0.0,
                    "signals": {},
                    "matches": [
                        {
                            "field": "relationship",
                            "values": ["one-hop supporting ADR"],
                        }
                    ],
                },
                adr_dir,
                source=source,
                schema_version=schema_version,
                role="supporting",
                related_ids=_related_ids(supporting_id, relationships),
            )
        )
    return results


def query_adr_context(
    query: str,
    adr_dir: Path,
    *,
    limit: int = 5,
    min_score: float = 0.1,
    strict_index: bool = False,
    include_history: bool = False,
    statuses: Sequence[str] = (),
    authorities: Sequence[str] = (),
    paths: Sequence[str] = (),
    symbols: Sequence[str] = (),
    components: Sequence[str] = (),
    topics: Sequence[str] = (),
) -> Dict:
    if not isinstance(query, str) or not query.strip():
        raise ValueError("query must be a non-empty string")
    if not isinstance(limit, int) or isinstance(limit, bool) or not 1 <= limit <= 100:
        raise ValueError("limit must be an integer between 1 and 100")
    if (
        not isinstance(min_score, (int, float))
        or isinstance(min_score, bool)
        or not 0 <= float(min_score) <= 1
    ):
        raise ValueError("min_score must be a number between 0 and 1")
    invalid_statuses = sorted(set(statuses) - SUPPORTED_STATUSES)
    if invalid_statuses:
        raise ValueError("unsupported status filter(s): " + ", ".join(invalid_statuses))
    invalid_authorities = sorted(set(authorities) - SUPPORTED_AUTHORITIES)
    if invalid_authorities:
        raise ValueError(
            "unsupported authority filter(s): " + ", ".join(invalid_authorities)
        )
    for name, values in (
        ("paths", paths),
        ("symbols", symbols),
        ("components", components),
        ("topics", topics),
    ):
        if len(values) > 32 or any(
            not isinstance(value, str) or not value.strip() or len(value) > 240
            for value in values
        ):
            raise ValueError(
                f"{name} must contain at most 32 non-empty strings of 240 characters"
            )
    warnings: List[str] = []
    try:
        records, relationships, version = load_index_graph(adr_dir)
        source = f"index-v{version}"
    except IndexQueryError as exc:
        if strict_index:
            raise
        warning = f"[adr-context] WARN: {exc}; using Markdown compatibility fallback"
        warnings.append(warning)
        records, relationships = _markdown_graph(adr_dir)
        version = 2
        source = "markdown-fallback"
    results = query_records(
        records,
        relationships,
        query,
        adr_dir,
        limit=limit,
        min_score=min_score,
        include_history=include_history,
        statuses=statuses,
        authorities=authorities,
        paths=paths,
        symbols=symbols,
        components=components,
        topics=topics,
        source=source,
        schema_version=version,
    )
    return {
        "results": results,
        "warnings": warnings,
        "source": source,
        "engine": (
            "index-first" if source.startswith("index-") else "markdown-fallback"
        ),
        "schema_version": version,
    }
