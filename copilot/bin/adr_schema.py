"""Shared ADR frontmatter schema helpers.

This module intentionally stays stdlib-only and YAML-subset-only. adr-kit
frontmatter is rendered in a simple shape that this parser can round-trip:
scalar fields plus string lists.
"""

from __future__ import annotations

import importlib.machinery
import importlib.util
import json
import re
import sys
from datetime import date
from pathlib import Path
from typing import Dict, List, Optional, Tuple

_BIN_DIR = Path(__file__).resolve().parent


def _load_sibling(name: str):
    """Import bin/<name>.py by explicit path, WITHOUT touching sys.path.

    SEC-HIGH (TASK-62): this module used to `sys.path.insert(0, _BIN_DIR)`.
    That made bin/ shadow the standard library for every subsequent import in
    whatever process loaded it -- including the executables that load this
    module by explicit path precisely to avoid that -- and it re-added the
    directory CPython's -P / PYTHONSAFEPATH removes. See bin/adr-judge for the
    full rationale. Registering under the bare name lets the plain
    `from adr_format import ...` below resolve from sys.modules.
    """
    cached = sys.modules.get(name)
    if cached is not None:
        return cached
    loader = importlib.machinery.SourceFileLoader(name, str(_BIN_DIR / f"{name}.py"))
    spec = importlib.util.spec_from_loader(name, loader)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    loader.exec_module(module)
    return module


_load_sibling("adr_format")

from adr_format import SUPPORTED_PROFILES

FRONTMATTER_FIELD_ORDER = (
    "id",
    "title",
    "status",
    "date",
    "binding",
    "gate",
    "documents_shipped",
    "verified_in",
    "supersedes",
    "superseded_by",
)

OPTIONAL_FRONTMATTER_FIELD_ORDER = (
    "topics",
    "aliases",
    "components",
    "symbols",
    "context_scope",
    "format",
)

VALID_STATUSES = {"Proposed", "Accepted", "Deprecated", "Superseded", "Amended", "Rejected"}
VALID_CONTEXT_SCOPES = {"global", "selective"}

ADR_ID_RE = re.compile(r"\bADR-(\d{1,4})\b", re.IGNORECASE)
ADR_FILENAME_RE = re.compile(r"(?i)^ADR-(\d{1,4})-")
LEGACY_FILENAME_RE = re.compile(
    r"(?i)^(?:ADR[-_ ]?)?0*(\d{1,4})[-_. ]+(.+?)\.md$"
)
TITLE_RE = re.compile(r"^#\s+ADR-\d{1,4}\s+(.+?)\s*$", re.MULTILINE | re.IGNORECASE)
LEGACY_TITLE_RE = re.compile(
    r"^#\s+(?:ADR[-_ ]?)?0*\d{1,4}[.:\s-]+(.+?)\s*$",
    re.MULTILINE | re.IGNORECASE,
)
STATUS_SECTION_RE = re.compile(
    r"^##\s+Status(?!\s+History)\s*$\n+([^\n]+)",
    re.IGNORECASE | re.MULTILINE,
)
DATE_RE = re.compile(r"\b(\d{4}-\d{2}-\d{2})\b")
SUPERSEDES_RE = re.compile(r"\bSupersedes\s+ADR-(\d{1,4})\b", re.IGNORECASE)
SUPERSEDED_BY_RE = re.compile(r"\bSuperseded\s+by\s+ADR-(\d{1,4})\b", re.IGNORECASE)


class FrontmatterError(Exception):
    """Raised when frontmatter uses unsupported syntax."""


def _normalize_adr_id(raw: str) -> str:
    match = ADR_ID_RE.search(raw)
    if not match:
        return raw
    return f"ADR-{int(match.group(1)):03d}"


def split_frontmatter(text: str) -> Tuple[Optional[str], str]:
    """Return (raw_frontmatter, markdown_body).

    If no leading frontmatter block exists, raw_frontmatter is None and body is
    the original text unchanged.
    """
    lines = text.splitlines(keepends=True)
    if not lines or lines[0].strip() != "---":
        return None, text
    for idx in range(1, len(lines)):
        if lines[idx].strip() == "---":
            return "".join(lines[1:idx]), "".join(lines[idx + 1 :])
    return None, text


def _parse_scalar(raw: str):
    value = raw.strip()
    if value == "":
        return ""
    if value == "null":
        return None
    if value == "true":
        return True
    if value == "false":
        return False
    if value == "[]":
        return []
    if len(value) >= 2 and value[0] == value[-1] == '"':
        try:
            return json.loads(value)
        except json.JSONDecodeError as exc:
            raise FrontmatterError(f"invalid quoted scalar {value!r}: {exc}") from exc
    if len(value) >= 2 and value[0] == value[-1] == "'":
        return value[1:-1].replace("''", "'")
    return value


def parse_frontmatter(raw: Optional[str]) -> Dict:
    """Parse adr-kit frontmatter rendered by render_frontmatter()."""
    if raw is None:
        return {}
    result: Dict = {}
    current_list_key: Optional[str] = None
    for lineno, line in enumerate(raw.splitlines(), start=1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.startswith("- "):
            if current_list_key is None:
                raise FrontmatterError(f"line {lineno}: list item without a key")
            result[current_list_key].append(_parse_scalar(stripped[2:]))
            continue
        if ":" not in line:
            raise FrontmatterError(f"line {lineno}: expected key: value")
        key, value = line.split(":", 1)
        key = key.strip()
        if not key:
            raise FrontmatterError(f"line {lineno}: empty key")
        if value.strip() == "":
            result[key] = []
            current_list_key = key
        else:
            result[key] = _parse_scalar(value)
            current_list_key = None
    return result


def infer_frontmatter(body: str, path: Optional[Path] = None) -> Dict:
    """Infer canonical frontmatter from legacy prose without editing the body."""
    filename_id = None
    if path is not None:
        match = ADR_FILENAME_RE.match(path.name)
        if match:
            filename_id = f"ADR-{int(match.group(1)):03d}"
        else:
            legacy_match = LEGACY_FILENAME_RE.match(path.name)
            if legacy_match:
                filename_id = f"ADR-{int(legacy_match.group(1)):03d}"
    heading_id = None
    heading_match = re.search(
        r"^#\s+(ADR-\d{1,4})\b", body, re.MULTILINE | re.IGNORECASE
    )
    if heading_match:
        heading_id = _normalize_adr_id(heading_match.group(1))
    else:
        legacy_heading = re.search(
            r"^#\s+(?:ADR[-_ ]?)?0*(\d{1,4})[.:\s-]+",
            body,
            re.MULTILINE | re.IGNORECASE,
        )
        if legacy_heading:
            heading_id = f"ADR-{int(legacy_heading.group(1)):03d}"
    adr_id = filename_id or heading_id or "ADR-000"

    title_match = TITLE_RE.search(body) or LEGACY_TITLE_RE.search(body)
    if title_match is None:
        generic_title = re.search(r"^#\s+(.+?)\s*$", body, re.MULTILINE)
        title_match = generic_title
    title = title_match.group(1).strip() if title_match else ""

    status_line = ""
    status_match = STATUS_SECTION_RE.search(body)
    if status_match:
        status_line = status_match.group(1).strip()
    status_word_match = re.match(r"([A-Za-z]+)", status_line)
    status = status_word_match.group(1).capitalize() if status_word_match else "Proposed"
    if status not in VALID_STATUSES:
        status = "Proposed"

    date_match = DATE_RE.search(status_line)
    status_date = date_match.group(1) if date_match else None

    supersedes = sorted({_normalize_adr_id(f"ADR-{n}") for n in SUPERSEDES_RE.findall(body)})
    superseded_by_match = SUPERSEDED_BY_RE.search(status_line)
    superseded_by = (
        _normalize_adr_id(f"ADR-{superseded_by_match.group(1)}")
        if superseded_by_match
        else None
    )

    return {
        "id": adr_id,
        "title": title,
        "status": status,
        "date": status_date,
        "binding": False,
        "gate": None,
        "documents_shipped": False,
        "verified_in": [],
        "supersedes": supersedes,
        "superseded_by": superseded_by,
    }


def _render_scalar(value) -> str:
    if value is None:
        return "null"
    if value is True:
        return "true"
    if value is False:
        return "false"
    return json.dumps(str(value), ensure_ascii=False)


def render_frontmatter(data: Dict) -> str:
    """Render canonical frontmatter with stable field order."""
    lines: List[str] = ["---"]
    rendered = set()
    for key in FRONTMATTER_FIELD_ORDER:
        value = data.get(key)
        rendered.add(key)
        if isinstance(value, list):
            if value:
                lines.append(f"{key}:")
                lines.extend(f"  - {_render_scalar(item)}" for item in value)
            else:
                lines.append(f"{key}: []")
        else:
            lines.append(f"{key}: {_render_scalar(value)}")
    for key in OPTIONAL_FRONTMATTER_FIELD_ORDER:
        if key not in data:
            continue
        value = data[key]
        rendered.add(key)
        if isinstance(value, list):
            if value:
                lines.append(f"{key}:")
                lines.extend(f"  - {_render_scalar(item)}" for item in value)
            else:
                lines.append(f"{key}: []")
        else:
            lines.append(f"{key}: {_render_scalar(value)}")
    for key in sorted(k for k in data if k not in rendered):
        value = data[key]
        if isinstance(value, list):
            if value:
                lines.append(f"{key}:")
                lines.extend(f"  - {_render_scalar(item)}" for item in value)
            else:
                lines.append(f"{key}: []")
        else:
            lines.append(f"{key}: {_render_scalar(value)}")
    lines.append("---")
    lines.append("")
    return "\n".join(lines)


def canonicalize_frontmatter(existing: Dict, inferred: Dict) -> Dict:
    """Return existing frontmatter completed with canonical inferred fields."""
    merged = dict(existing)
    for key in FRONTMATTER_FIELD_ORDER:
        if key not in merged:
            merged[key] = inferred.get(key)
    status = merged.get("status")
    if isinstance(status, str):
        normalized_status = {
            item.casefold(): item for item in VALID_STATUSES
        }.get(status.strip().casefold())
        if normalized_status is not None:
            merged["status"] = normalized_status
    return merged


def _normalize_legacy_heading(
    body: str,
    path: Optional[Path],
    inferred: Dict,
) -> str:
    """Normalize an identifiable legacy H1 without changing decision prose."""
    if path is None or ADR_FILENAME_RE.match(path.name):
        return body
    adr_id = inferred.get("id")
    title = inferred.get("title")
    if (
        not isinstance(adr_id, str)
        or adr_id == "ADR-000"
        or not isinstance(title, str)
        or not title.strip()
    ):
        return body
    heading = re.search(r"^#\s+.+?\s*$", body, re.MULTILINE)
    if heading is None:
        return body
    normalized = f"# {adr_id} {title.strip()}"
    return body[: heading.start()] + normalized + body[heading.end() :]


def validate_frontmatter(data: Dict) -> List[str]:
    """Return human-readable schema issues; empty list means valid."""
    issues: List[str] = []
    missing = [key for key in FRONTMATTER_FIELD_ORDER if key not in data]
    if missing:
        issues.append(f"missing canonical field(s): {', '.join(missing)}")

    adr_id = data.get("id")
    if not isinstance(adr_id, str) or not re.fullmatch(r"ADR-\d{3,4}", adr_id):
        issues.append("id must be an ADR-NNN string")

    title = data.get("title")
    if not isinstance(title, str) or not title.strip():
        issues.append("title must be a non-empty string")

    status = data.get("status")
    if status not in VALID_STATUSES:
        issues.append(f"status must be one of: {', '.join(sorted(VALID_STATUSES))}")

    status_date = data.get("date")
    if status_date is not None:
        if not isinstance(status_date, str):
            issues.append("date must be null or YYYY-MM-DD string")
        else:
            try:
                date.fromisoformat(status_date)
            except ValueError:
                issues.append("date must be null or YYYY-MM-DD string")

    if not isinstance(data.get("binding"), bool):
        issues.append("binding must be a boolean")

    gate = data.get("gate")
    if gate is not None and (not isinstance(gate, str) or not gate.strip()):
        issues.append("gate must be null or a non-empty string")

    if not isinstance(data.get("documents_shipped"), bool):
        issues.append("documents_shipped must be a boolean")

    for list_key in ("verified_in", "supersedes"):
        value = data.get(list_key)
        if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
            issues.append(f"{list_key} must be a list of strings")

    superseded_by = data.get("superseded_by")
    if superseded_by is not None and (
        not isinstance(superseded_by, str)
        or not re.fullmatch(r"ADR-\d{3,4}", superseded_by)
    ):
        issues.append("superseded_by must be null or an ADR-NNN string")

    for ref in data.get("supersedes", []) if isinstance(data.get("supersedes"), list) else []:
        if not re.fullmatch(r"ADR-\d{3,4}", ref):
            issues.append(f"supersedes entry {ref!r} must be an ADR-NNN string")

    profile = data.get("format")
    if profile is not None and profile not in SUPPORTED_PROFILES:
        issues.append("format must be one of: " + ", ".join(SUPPORTED_PROFILES))

    for list_key in ("topics", "aliases", "components", "symbols"):
        value = data.get(list_key)
        if value is None:
            continue
        if (
            not isinstance(value, list)
            or not all(
                isinstance(item, str) and 0 < len(item.strip()) <= 120
                for item in value
            )
            or len(value) > 32
        ):
            issues.append(
                f"{list_key} must be a list of at most 32 non-empty strings "
                "of at most 120 characters"
            )
        elif len({item.casefold() for item in value}) != len(value):
            issues.append(f"{list_key} entries must be unique ignoring case")

    context_scope = data.get("context_scope")
    if context_scope is not None and context_scope not in VALID_CONTEXT_SCOPES:
        issues.append("context_scope must be one of: global, selective")

    return issues


def migrate_text(text: str, path: Optional[Path] = None) -> Tuple[str, bool, List[str]]:
    """Add canonical metadata and normalize an identifiable legacy H1."""
    raw_frontmatter, body = split_frontmatter(text)
    inferred = infer_frontmatter(body, path)
    try:
        existing = parse_frontmatter(raw_frontmatter)
    except FrontmatterError as exc:
        return text, False, [str(exc)]
    data = canonicalize_frontmatter(existing, inferred)
    issues = validate_frontmatter(data)
    if issues:
        return text, False, issues
    rendered = render_frontmatter(data)
    normalized_body = _normalize_legacy_heading(body, path, inferred)
    new_text = f"{rendered}{normalized_body}"
    return new_text, new_text != text, []
