"""Deterministic, read-only ADR readiness and implementation-link analysis."""

from __future__ import annotations

import fnmatch
import re
from datetime import date
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence

from adr_catalog import build_relationships, load_adr_records, normalize_adr_id


READINESS_SCHEMA_VERSION = 1
READINESS_CLASSES = (
    "not-an-adr",
    "needs-human-input",
    "needs-mechanical-fix",
    "ready-for-confirmation",
    "accepted",
    "rejected",
    "supersession-required",
)
FINDING_CODES = (
    "ADR_FILE_CHANGED",
    "ADR_ID_EXPLICIT",
    "ARCHITECTURE_REVIEW_RECOMMENDED",
    "DECISION_MISSING",
    "ENFORCEMENT_SCOPE_CHANGED",
    "FORMAT_UNKNOWN",
    "FRONTMATTER_MALFORMED",
    "OPEN_QUESTION",
    "STATUS_UNKNOWN",
    "SUPERSESSION_STATE_INCONSISTENT",
    "VERIFIED_IN_CHANGED",
)

_ADR_TOKEN_RE = re.compile(r"\bADR-0*(\d{1,4})\b", re.IGNORECASE)
_ARCHITECTURE_PATH_RE = re.compile(
    r"(^|/)(?:architecture|infra(?:structure)?|migrations?|schemas?|"
    r"api|contracts?|config|deploy|security)(?:/|[-_.])|"
    r"(^|/)(?:dockerfile|compose\.ya?ml|pyproject\.toml|package\.json|"
    r"Cargo\.toml|go\.mod)$",
    re.IGNORECASE,
)


class ReadinessError(ValueError):
    """Raised when readiness input cannot be analyzed safely."""


def normalize_path(value: str) -> str:
    """Return a portable repository-relative path representation."""
    normalized = value.replace("\\", "/").strip()
    while normalized.startswith("./"):
        normalized = normalized[2:]
    return re.sub(r"/+", "/", normalized)


def explicit_adr_ids(text: str) -> List[str]:
    return sorted(
        {f"ADR-{int(match.group(1)):03d}" for match in _ADR_TOKEN_RE.finditer(text)}
    )


def _path_matches(path: str, pattern: str) -> bool:
    path = normalize_path(path)
    pattern = normalize_path(pattern)
    if not pattern:
        return False
    if any(char in pattern for char in "*?["):
        return fnmatch.fnmatchcase(path.casefold(), pattern.casefold())
    return path.casefold() == pattern.casefold() or path.casefold().startswith(
        pattern.rstrip("/").casefold() + "/"
    )


def implementation_evidence(
    record: Dict,
    changed_paths: Sequence[str],
    source_text: str = "",
    *,
    paths_normalized: bool = False,
    path_pairs: Optional[Sequence[tuple[str, str]]] = None,
    cited_ids: Optional[Sequence[str]] = None,
) -> Dict:
    """Return explicit, inspectable evidence for one ADR implementation link."""
    adr_id = record["adr_id"]
    paths = (
        list(changed_paths)
        if paths_normalized
        else sorted(
            {normalize_path(path) for path in changed_paths if path}, key=str.casefold
        )
    )
    pairs = (
        list(path_pairs)
        if path_pairs is not None
        else [(path, path.casefold()) for path in paths]
    )
    referenced_ids = (
        set(cited_ids) if cited_ids is not None else set(explicit_adr_ids(source_text))
    )
    adr_filename = str(record["path"]).replace("\\", "/").rsplit("/", 1)[-1].casefold()
    adr_file_changed = any(
        path.rsplit("/", 1)[-1].casefold() == adr_filename for path in paths
    )
    verified_targets = tuple(
        normalize_path(str(target)) for target in record.get("verified_in", [])
    )
    scope_targets = tuple(normalize_path(str(target)) for target in record.get("scope", []))

    def matches(targets: Sequence[str]) -> List[str]:
        exact = tuple(
            (target.casefold(), target.rstrip("/").casefold() + "/")
            for target in targets
            if target and not any(char in target for char in "*?[")
        )
        patterns = tuple(
            target.casefold()
            for target in targets
            if target and any(char in target for char in "*?[")
        )
        result = []
        for path, folded in pairs:
            if any(folded == target or folded.startswith(prefix) for target, prefix in exact):
                result.append(path)
            elif any(fnmatch.fnmatchcase(folded, pattern) for pattern in patterns):
                result.append(path)
        return result

    verified_matches = matches(verified_targets)
    scope_matches = matches(scope_targets)
    implementation_paths = sorted(
        {
            path
            for path in verified_matches + scope_matches
            if not path.casefold().startswith("docs/adr/")
        },
        key=str.casefold,
    )
    explicit_reference = adr_id in referenced_ids
    linked = bool(
        implementation_paths
        and (explicit_reference or adr_file_changed or verified_matches)
    )
    evidence: List[Dict[str, object]] = []
    if explicit_reference:
        evidence.append(
            {"code": "ADR_ID_EXPLICIT", "adr_id": adr_id, "source": "diff-context"}
        )
    if adr_file_changed:
        evidence.append(
            {"code": "ADR_FILE_CHANGED", "path": normalize_path(str(record["path"]))}
        )
    for path in verified_matches:
        evidence.append({"code": "VERIFIED_IN_CHANGED", "path": path})
    for path in scope_matches:
        evidence.append({"code": "ENFORCEMENT_SCOPE_CHANGED", "path": path})
    evidence.sort(
        key=lambda item: (
            str(item.get("code", "")),
            str(item.get("path", "")),
            str(item.get("adr_id", "")),
        )
    )
    return {
        "linked": linked,
        "implemented": bool(implementation_paths),
        "blocking_proposed": linked and record.get("status") == "Proposed",
        "changed_paths": implementation_paths,
        "evidence": evidence,
    }


def architecture_advisories(changed_paths: Sequence[str]) -> List[Dict[str, str]]:
    """Return non-blocking review signals; heuristics never prove ADR linkage."""
    paths = sorted({normalize_path(path) for path in changed_paths if path}, key=str.casefold)
    return [
        {
            "code": "ARCHITECTURE_REVIEW_RECOMMENDED",
            "path": path,
            "classification": "not-an-adr",
            "message": "Architecture-sensitive path changed; review whether a durable decision is present.",
            "next_command": f'/adr-kit:grill --source "{path.replace(chr(34), chr(92) + chr(34))}"',
        }
        for path in paths
        if _ARCHITECTURE_PATH_RE.search(path)
    ]


def _mechanical_findings(record: Dict) -> List[Dict[str, str]]:
    findings: List[Dict[str, str]] = list(record.get("metadata_findings", []))
    if not str(record.get("decision_text", "")).strip():
        findings.append(
            {
                "code": "DECISION_MISSING",
                "message": "Record the chosen decision before confirmation.",
            }
        )
    if record.get("superseded_by") and record.get("status") != "Superseded":
        findings.append(
            {
                "code": "SUPERSESSION_STATE_INCONSISTENT",
                "message": "Align superseded_by with lifecycle status.",
            }
        )
    return sorted(findings, key=lambda item: item["code"])


def _classification(
    record: Dict,
    mechanical: Sequence[Dict[str, str]],
    human: Sequence[Dict[str, str]],
) -> str:
    status = str(record.get("status", "")).casefold()
    if status == "accepted":
        return "accepted"
    if status == "rejected":
        return "rejected"
    if status in {"superseded", "deprecated", "amended"} or record.get("superseded_by"):
        return "supersession-required"
    if mechanical:
        return "needs-mechanical-fix"
    if human:
        return "needs-human-input"
    if status == "proposed":
        return "ready-for-confirmation"
    return "not-an-adr"


def readiness_for_record(
    record: Dict,
    *,
    evaluated_on: date,
    changed_paths: Sequence[str] = (),
    source_text: str = "",
    relationships: Sequence[Dict] = (),
    paths_normalized: bool = False,
    path_pairs: Optional[Sequence[tuple[str, str]]] = None,
    cited_ids: Optional[Sequence[str]] = None,
) -> Dict:
    mechanical = _mechanical_findings(record)
    human = [
        {
            "code": "OPEN_QUESTION",
            "message": question,
        }
        for question in record.get("open_questions", [])
    ]
    quality_checks = {
        "decision": bool(str(record.get("decision_text", "")).strip()),
        "evidence": bool(record.get("verified_in")),
        "open_questions_resolved": not bool(record.get("open_questions")),
    }
    quality_score = round(
        sum(1 for passed in quality_checks.values() if passed) / len(quality_checks), 3
    )
    classification = _classification(record, mechanical, human)
    link = implementation_evidence(
        record,
        changed_paths,
        source_text,
        paths_normalized=paths_normalized,
        path_pairs=path_pairs,
        cited_ids=cited_ids,
    )
    related = sorted(
        {
            edge["target"] if edge["source"] == record["adr_id"] else edge["source"]
            for edge in relationships
            if record["adr_id"] in {edge["source"], edge["target"]}
        }
    )
    next_commands = {
        "needs-human-input": f"/adr-kit:grill {record['adr_id']}",
        "needs-mechanical-fix": f"/adr-kit:grill {record['adr_id']}",
        "ready-for-confirmation": f"/adr-kit:grill {record['adr_id']}",
        "supersession-required": f"/adr-kit:grill --revalidate {record['adr_id']}",
    }
    return {
        "adr_id": record["adr_id"],
        "title": record["title"],
        "path": normalize_path(str(record["path"])),
        "status": record["status"],
        "format": record["format"],
        "evaluated_on": evaluated_on.isoformat(),
        "classification": classification,
        "mechanical_findings": mechanical,
        "human_findings": human,
        "mechanical_actions": [item["message"] for item in mechanical],
        "human_decisions": [item["message"] for item in human],
        "quality": {"score": quality_score, "checks": quality_checks},
        "open_questions": list(record.get("open_questions", [])),
        "documents_shipped": bool(record.get("documents_shipped")),
        "verified_in": sorted(
            {normalize_path(str(item)) for item in record.get("verified_in", [])},
            key=str.casefold,
        ),
        "implementation_link": link,
        "related_adrs": related,
        "next_command": next_commands.get(classification),
    }


def build_readiness_report(
    adr_dir: Path,
    *,
    evaluated_on: date,
    adr_id: Optional[str] = None,
    all_proposed: bool = False,
    changed_paths: Sequence[str] = (),
    source_text: str = "",
) -> Dict:
    records = load_adr_records(adr_dir)
    relationships = build_relationships(records)
    normalized_changed_paths = sorted(
        {normalize_path(path) for path in changed_paths if path}, key=str.casefold
    )
    path_pairs = [(path, path.casefold()) for path in normalized_changed_paths]
    cited_ids = explicit_adr_ids(source_text)
    normalized_id = normalize_adr_id(adr_id) if adr_id else None
    if adr_id and normalized_id is None:
        numeric = re.fullmatch(r"0*(\d{1,4})", str(adr_id).strip())
        normalized_id = f"ADR-{int(numeric.group(1)):03d}" if numeric else None
    if adr_id and normalized_id is None:
        raise ReadinessError(f"invalid ADR id: {adr_id}")
    selected = [
        record
        for record in records
        if (
            (normalized_id and record["adr_id"] == normalized_id)
            or (all_proposed and record["status"] == "Proposed")
            or (not normalized_id and not all_proposed)
        )
    ]
    if normalized_id and not selected:
        raise ReadinessError(f"ADR not found: {normalized_id}")
    reports = [
        readiness_for_record(
            record,
            evaluated_on=evaluated_on,
            changed_paths=normalized_changed_paths,
            source_text=source_text,
            relationships=relationships,
            paths_normalized=True,
            path_pairs=path_pairs,
            cited_ids=cited_ids,
        )
        for record in selected
    ]
    reports.sort(key=lambda item: item["adr_id"])
    blocking = [
        item["adr_id"]
        for item in reports
        if item["implementation_link"]["blocking_proposed"]
    ]
    advisories = architecture_advisories(normalized_changed_paths)
    return {
        "schema_version": READINESS_SCHEMA_VERSION,
        "evaluated_on": evaluated_on.isoformat(),
        "adr_dir": normalize_path(str(adr_dir)),
        "summary": {
            "total": len(reports),
            "blocking_proposed": blocking,
            "blocking_count": len(blocking),
            "advisory_count": len(advisories),
        },
        "advisories": advisories,
        "adrs": reports,
    }
