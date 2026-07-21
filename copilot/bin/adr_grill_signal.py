"""Bounded index-only grilling advisories for hooks and pre-commit."""

from __future__ import annotations

import fnmatch
import re
import shlex
from pathlib import Path
from typing import Sequence


SIGNAL_SCHEMA_VERSION = 1
MAX_SIGNALS = 3
_ADR_RE = re.compile(r"\bADR-0*(\d{1,4})\b", re.IGNORECASE)
_SENSITIVE_RE = re.compile(
    r"(^|/)(?:architecture|infra(?:structure)?|migrations?|schemas?|"
    r"api|contracts?|config|deploy|security)(?:/|[-_.])|"
    r"(^|/)(?:dockerfile|compose\.ya?ml|pyproject\.toml|package\.json|"
    r"Cargo\.toml|go\.mod)$",
    re.IGNORECASE,
)


def normalize_path(value: object) -> str:
    normalized = str(value).replace("\\", "/").strip()
    normalized = re.sub(r"[\x00-\x1f\x7f]+", " ", normalized)
    normalized = normalized.replace("::", "__")
    while normalized.startswith("./"):
        normalized = normalized[2:]
    return re.sub(r"/+", "/", normalized)


def _matches(path: str, target: str) -> bool:
    path = normalize_path(path).casefold()
    target = normalize_path(target).casefold()
    if not target:
        return False
    if any(char in target for char in "*?["):
        return fnmatch.fnmatchcase(path, target)
    return path == target or path.startswith(target.rstrip("/") + "/")


def _quote(value: str, shell: str) -> str:
    clean = re.sub(r"[\r\n\x00-\x1f]+", " ", value)[:4096]
    if shell == "powershell":
        return "'" + clean.replace("'", "''") + "'"
    return shlex.quote(clean)


def analyze_index(
    index: dict,
    changed_paths: Sequence[str],
    source_text: str,
    *,
    shell: str = "posix",
) -> dict:
    paths = sorted({normalize_path(path) for path in changed_paths if path}, key=str.casefold)
    cited = {f"ADR-{int(match.group(1)):03d}" for match in _ADR_RE.finditer(source_text)}
    linked = []
    for record in index.get("adrs", []):
        if not isinstance(record, dict) or record.get("status") != "Proposed":
            continue
        adr_id = str(record.get("id", ""))
        metadata = record.get("metadata", {})
        verified = metadata.get("verified_in", []) if isinstance(metadata, dict) else []
        scope = record.get("scope", {})
        globs = scope.get("path_globs", []) if isinstance(scope, dict) else []
        verified_matches = sorted(
            {path for path in paths for target in verified if _matches(path, str(target))},
            key=str.casefold,
        )
        scope_matches = sorted(
            {path for path in paths for target in globs if _matches(path, str(target))},
            key=str.casefold,
        )
        adr_changed = any(Path(path).name == str(record.get("path", "")) for path in paths)
        implementation = sorted(
            {
                path
                for path in verified_matches + scope_matches
                if not path.casefold().startswith("docs/adr/")
            },
            key=str.casefold,
        )
        if not implementation or not (
            verified_matches or adr_changed or adr_id in cited
        ):
            continue
        evidence = []
        if adr_id in cited:
            evidence.append("ADR_ID_EXPLICIT")
        if adr_changed:
            evidence.append("ADR_FILE_CHANGED")
        if verified_matches:
            evidence.append("VERIFIED_IN_CHANGED")
        if scope_matches:
            evidence.append("ENFORCEMENT_SCOPE_CHANGED")
        linked.append(
            {
                "code": "LINKED_PROPOSED_IMPLEMENTATION",
                "adr_id": adr_id,
                "paths": implementation,
                "evidence": sorted(set(evidence)),
                "command": f"/adr-kit:grill {adr_id}",
            }
        )
    linked.sort(key=lambda item: item["adr_id"])
    linked_paths = {path for item in linked for path in item["paths"]}
    suspected = [
        {
            "code": "ARCHITECTURE_REVIEW_RECOMMENDED",
            "path": path,
            "command": f"/adr-kit:grill --source {_quote(path, shell)}",
        }
        for path in paths
        if path not in linked_paths and _SENSITIVE_RE.search(path)
    ]
    return {
        "schema_version": SIGNAL_SCHEMA_VERSION,
        "linked_proposed": linked[:MAX_SIGNALS],
        "suspected_decisions": suspected[:MAX_SIGNALS],
        "signal_count": min(MAX_SIGNALS, len(linked) + len(suspected)),
    }
