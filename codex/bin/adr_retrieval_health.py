"""Read-only selective-context probes and retrieval metadata health."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Sequence

from adr_query import IndexQueryError, load_index_graph, query_records

MAX_PROBES = 100
MAX_EXPECTATIONS = 20
DEFAULT_PROBE_FILE = "adr-context-probes.json"


class ProbeConfigError(ValueError):
    """Raised when a project retrieval-probe file is malformed."""


def _string_array(
    value: object,
    field: str,
    *,
    maximum: int,
    adr_ids: bool = False,
) -> List[str]:
    if not isinstance(value, list) or len(value) > maximum:
        raise ProbeConfigError(f"{field} must be an array with at most {maximum} items")
    result: List[str] = []
    for item in value:
        if not isinstance(item, str) or not item.strip() or len(item) > 240:
            raise ProbeConfigError(f"{field} entries must be non-empty strings")
        if adr_ids and not re.fullmatch(r"ADR-\d{3,4}", item):
            raise ProbeConfigError(f"{field} contains invalid ADR id {item!r}")
        result.append(item)
    if len({item.casefold() for item in result}) != len(result):
        raise ProbeConfigError(f"{field} entries must be unique")
    return result


def load_probes(path: Path) -> Dict:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ProbeConfigError(f"cannot read retrieval probes: {exc}") from exc
    if not isinstance(payload, dict) or payload.get("schema_version") != 1:
        raise ProbeConfigError("retrieval probes require schema_version 1")
    allowed_root = {"$schema", "schema_version", "probes"}
    if set(payload) - allowed_root:
        raise ProbeConfigError(
            "unknown retrieval-probe root field(s): "
            + ", ".join(sorted(set(payload) - allowed_root))
        )
    probes = payload.get("probes")
    if not isinstance(probes, list) or len(probes) > MAX_PROBES:
        raise ProbeConfigError(f"probes must be an array with at most {MAX_PROBES} items")
    ids = set()
    normalized = []
    allowed_probe = {
        "id",
        "query",
        "paths",
        "components",
        "symbols",
        "topics",
        "limit",
        "expect",
    }
    for raw in probes:
        if not isinstance(raw, dict) or set(raw) - allowed_probe:
            raise ProbeConfigError("each retrieval probe must be a known-field object")
        probe_id = raw.get("id")
        query = raw.get("query")
        limit = raw.get("limit", 3)
        expect = raw.get("expect")
        if (
            not isinstance(probe_id, str)
            or not re.fullmatch(r"[a-z][a-z0-9-]{0,79}", probe_id)
            or probe_id in ids
        ):
            raise ProbeConfigError(f"invalid or duplicate probe id {probe_id!r}")
        if not isinstance(query, str) or not query.strip() or len(query) > 1000:
            raise ProbeConfigError(f"{probe_id}: query must be a non-empty string")
        if not isinstance(limit, int) or isinstance(limit, bool) or not 1 <= limit <= 20:
            raise ProbeConfigError(f"{probe_id}: limit must be between 1 and 20")
        if (
            not isinstance(expect, dict)
            or set(expect) - {"include", "exclude"}
        ):
            raise ProbeConfigError(f"{probe_id}: expect must contain include/exclude")
        include = _string_array(
            expect.get("include", []),
            f"{probe_id}.expect.include",
            maximum=MAX_EXPECTATIONS,
            adr_ids=True,
        )
        exclude = _string_array(
            expect.get("exclude", []),
            f"{probe_id}.expect.exclude",
            maximum=MAX_EXPECTATIONS,
            adr_ids=True,
        )
        if set(include) & set(exclude):
            raise ProbeConfigError(f"{probe_id}: include and exclude overlap")
        ids.add(probe_id)
        normalized.append(
            {
                "id": probe_id,
                "query": query.strip(),
                "paths": _string_array(
                    raw.get("paths", []), f"{probe_id}.paths", maximum=32
                ),
                "components": _string_array(
                    raw.get("components", []), f"{probe_id}.components", maximum=32
                ),
                "symbols": _string_array(
                    raw.get("symbols", []), f"{probe_id}.symbols", maximum=32
                ),
                "topics": _string_array(
                    raw.get("topics", []), f"{probe_id}.topics", maximum=32
                ),
                "limit": limit,
                "expect": {"include": include, "exclude": exclude},
            }
        )
    return {"schema_version": 1, "probes": normalized}


def _metadata_findings(records: Sequence[Dict], strict: bool) -> List[Dict]:
    findings = []
    for record in records:
        metadata = record.get("metadata", {})
        if (
            record.get("status") != "Accepted"
            or not isinstance(metadata, dict)
            or metadata.get("binding") is not True
        ):
            continue
        contract = record.get("decision_contract", {})
        has_contract = isinstance(contract, dict) and any(
            isinstance(values, list) and any(str(value).strip() for value in values)
            for values in contract.values()
        )
        has_selective_data = any(
            isinstance(record.get(field), list) and record.get(field)
            for field in ("topics", "aliases", "components", "symbols")
        )
        if (
            record.get("context_scope") != "global"
            and not has_selective_data
            and not has_contract
        ):
            findings.append(
                {
                    "type": "selective_context_metadata",
                    "level": "FAIL" if strict else "ADVISORY",
                    "adr_id": record.get("id"),
                    "file": record.get("path"),
                    "message": (
                        "Accepted binding ADR has no selective retrieval metadata; "
                        "add topics, aliases, components, symbols, a Decision Contract, "
                        "or explicitly mark context_scope: global"
                    ),
                }
            )
    return findings


def evaluate_probes(
    records: Sequence[Dict],
    relationships: Sequence[Dict],
    schema_version: int,
    adr_dir: Path,
    probes: Sequence[Dict],
) -> Dict:
    results = []
    passed = 0
    for probe in probes:
        ranked = query_records(
            records,
            relationships,
            probe["query"],
            adr_dir,
            limit=probe["limit"],
            include_history=False,
            paths=probe["paths"],
            components=probe["components"],
            symbols=probe["symbols"],
            topics=probe["topics"],
            source=f"index-v{schema_version}",
            schema_version=schema_version,
        )
        actual = [
            {
                "rank": rank,
                "adr_id": item["adr_id"],
                "authority": item["authority"],
                "role": item["role"],
                "score": item["score"],
                "matches": item["matches"],
            }
            for rank, item in enumerate(ranked, start=1)
        ]
        actual_ids = [item["adr_id"] for item in actual]
        missing = [
            adr_id
            for adr_id in probe["expect"]["include"]
            if adr_id not in actual_ids
        ]
        unexpected = [
            adr_id
            for adr_id in probe["expect"]["exclude"]
            if adr_id in actual_ids
        ]
        historical = [
            item["adr_id"]
            for item in actual
            if item["authority"] == "historical"
        ]
        ok = not missing and not unexpected and not historical
        passed += int(ok)
        results.append(
            {
                "id": probe["id"],
                "status": "pass" if ok else "fail",
                "query": probe["query"],
                "inputs": {
                    "paths": probe["paths"],
                    "components": probe["components"],
                    "symbols": probe["symbols"],
                    "topics": probe["topics"],
                    "limit": probe["limit"],
                },
                "expected": probe["expect"],
                "actual": actual,
                "missing": missing,
                "unexpected": unexpected,
                "historical_leakage": historical,
            }
        )
    return {
        "configured": bool(probes),
        "summary": {
            "total": len(probes),
            "pass": passed,
            "fail": len(probes) - passed,
        },
        "results": results,
    }


def _load_config(adr_dir: Path) -> Dict:
    path = adr_dir / ".adr-kit.json"
    if not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def run_retrieval_health(
    adr_dir: Path,
    *,
    probe_path: Optional[Path] = None,
    config: Optional[Dict] = None,
) -> Dict:
    cfg = config if isinstance(config, dict) else _load_config(adr_dir)
    context_cfg = cfg.get("context", {}) if isinstance(cfg, dict) else {}
    mode = context_cfg.get("retrieval_completeness", "advisory")
    if mode not in {"off", "advisory", "strict"}:
        mode = "advisory"
    configured_path = probe_path or adr_dir / str(
        context_cfg.get("probes_file", DEFAULT_PROBE_FILE)
    )
    configured_path = configured_path.resolve()
    try:
        configured_path.relative_to(adr_dir.resolve())
    except ValueError:
        return {
            "status": "fail",
            "source": None,
            "schema_version": None,
            "probe_file": configured_path.as_posix(),
            "probe_error": "retrieval probe file must stay within the ADR directory",
            "index_error": None,
            "metadata_mode": mode,
            "metadata_findings": [],
            "probes": {
                "configured": False,
                "summary": {"total": 0, "pass": 0, "fail": 1},
                "results": [],
            },
        }
    try:
        records, relationships, version = load_index_graph(adr_dir)
    except IndexQueryError as exc:
        return {
            "status": "degraded",
            "source": None,
            "schema_version": None,
            "probe_file": configured_path.as_posix(),
            "index_error": str(exc),
            "metadata_mode": mode,
            "metadata_findings": [],
            "probes": {
                "configured": configured_path.is_file(),
                "summary": {"total": 0, "pass": 0, "fail": 0},
                "results": [],
            },
        }
    try:
        probe_payload = (
            load_probes(configured_path)
            if configured_path.is_file()
            else {"schema_version": 1, "probes": []}
        )
        probes = evaluate_probes(
            records,
            relationships,
            version,
            adr_dir,
            probe_payload["probes"],
        )
        probe_error = None
    except ProbeConfigError as exc:
        probes = {
            "configured": True,
            "summary": {"total": 0, "pass": 0, "fail": 1},
            "results": [],
        }
        probe_error = str(exc)
    metadata = [] if mode == "off" else _metadata_findings(records, mode == "strict")
    failed = (
        bool(probe_error)
        or probes["summary"]["fail"] > 0
        or any(item["level"] == "FAIL" for item in metadata)
    )
    return {
        "status": "fail" if failed else "pass",
        "source": f"index-v{version}",
        "schema_version": version,
        "probe_file": configured_path.as_posix(),
        "probe_error": probe_error,
        "index_error": None,
        "metadata_mode": mode,
        "metadata_findings": metadata,
        "probes": probes,
    }


def render_retrieval_health(payload: Dict) -> str:
    probe_summary = payload["probes"]["summary"]
    lines = [
        "ADR selective-context health:",
        f"  status={payload['status']} source={payload.get('source') or 'unavailable'}",
        (
            "  probes="
            f"{probe_summary['pass']} pass/{probe_summary['fail']} fail/"
            f"{probe_summary['total']} total"
        ),
        (
            "  retrieval_metadata="
            f"{len(payload.get('metadata_findings', []))} finding(s) "
            f"[{payload.get('metadata_mode', 'advisory')}]"
        ),
    ]
    if payload.get("index_error"):
        lines.append(f"  index_error={payload['index_error']}")
    if payload.get("probe_error"):
        lines.append(f"  probe_error={payload['probe_error']}")
    for result in payload["probes"]["results"]:
        if result["status"] == "fail":
            actual = ", ".join(
                f"{item['adr_id']}({item['authority']})"
                for item in result["actual"]
            ) or "none"
            lines.append(
                f"  FAIL {result['id']}: query={result['query']!r}; "
                f"missing={result['missing']}; unexpected={result['unexpected']}; "
                f"actual={actual}"
            )
    return "\n".join(lines)
