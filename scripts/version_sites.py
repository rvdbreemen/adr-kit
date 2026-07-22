#!/usr/bin/env python3
"""Read, validate and write the release version across every declared site.

`packaging/version-sites.json` is the single registry of where the version lives.
The bump writer, the release gate, the client-adapter generator and the tests all
go through this module, so a new version-bearing file is declared once instead of
being taught to three separate code paths that can drift apart.

Every function reports ALL findings rather than aborting on the first one: a
version bump should surface its complete work list in one pass.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

REGISTRY_RELPATH = "packaging/version-sites.json"
SEMVER = re.compile(r"^\d+\.\d+\.\d+$")


class VersionSiteError(RuntimeError):
    """Raised when the registry itself is unusable (missing file, bad shape)."""


@dataclass(frozen=True)
class Finding:
    label: str
    path: str
    found: str | None
    expected: str

    def __str__(self) -> str:
        found = "missing" if self.found is None else repr(self.found)
        return f"{self.label} ({self.path}) = {found}, expected {self.expected!r}"


def load_registry(root: Path) -> dict:
    path = root / REGISTRY_RELPATH
    if not path.is_file():
        raise VersionSiteError(f"version-site registry not found: {REGISTRY_RELPATH}")
    try:
        registry = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise VersionSiteError(f"invalid JSON in {REGISTRY_RELPATH}: {exc}") from exc
    for key in ("canonical", "sites"):
        if key not in registry:
            raise VersionSiteError(f"{REGISTRY_RELPATH} is missing '{key}'")
    return registry


# --- JSON pointer (RFC 6901), only the subset the registry needs ---------------

def _pointer_parts(pointer: str) -> list[str]:
    if not pointer.startswith("/"):
        raise VersionSiteError(f"JSON pointer must start with '/': {pointer!r}")
    return [p.replace("~1", "/").replace("~0", "~") for p in pointer[1:].split("/")]


def _pointer_get(doc: object, pointer: str) -> object | None:
    node = doc
    for part in _pointer_parts(pointer):
        if isinstance(node, list):
            if not part.isdigit() or int(part) >= len(node):
                return None
            node = node[int(part)]
        elif isinstance(node, dict):
            if part not in node:
                return None
            node = node[part]
        else:
            return None
    return node


def _pointer_set(doc: object, pointer: str, value: str) -> bool:
    parts = _pointer_parts(pointer)
    node = doc
    for part in parts[:-1]:
        if isinstance(node, list):
            if not part.isdigit() or int(part) >= len(node):
                return False
            node = node[int(part)]
        elif isinstance(node, dict):
            if part not in node:
                return False
            node = node[part]
        else:
            return False
    last = parts[-1]
    if isinstance(node, list):
        if not last.isdigit() or int(last) >= len(node):
            return False
        node[int(last)] = value
    elif isinstance(node, dict):
        if last not in node:
            return False
        node[last] = value
    else:
        return False
    return True


# --- reading ------------------------------------------------------------------

def read_canonical(root: Path, registry: dict | None = None) -> str | None:
    """Return the version from the canonical source (the CHANGELOG heading)."""
    registry = registry or load_registry(root)
    canonical = registry["canonical"]
    path = root / canonical["path"]
    if not path.is_file():
        return None
    pattern = re.compile(canonical["pattern"], re.MULTILINE)
    match = pattern.search(path.read_text(encoding="utf-8"))
    return match.group(1) if match else None


def _read_site(root: Path, site: dict) -> list[str | None]:
    """Return every version value the site currently carries (may be several)."""
    path = root / site["path"]
    if not path.is_file():
        return [None]
    kind = site["kind"]
    if kind == "json":
        try:
            doc = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return [None]
        value = _pointer_get(doc, site["pointer"])
        return [value if isinstance(value, str) else None]
    if kind in {"regex", "regex_all"}:
        matches = re.findall(site["pattern"], path.read_text(encoding="utf-8"))
        if not matches:
            return [None]
        # Each match is a tuple of capture groups; group 2 is the version.
        values = [m[1] if isinstance(m, tuple) else m for m in matches]
        return values if kind == "regex_all" else values[:1]
    raise VersionSiteError(f"unknown site kind {kind!r} for {site['path']}")


def read_all(root: Path, registry: dict | None = None) -> list[tuple[dict, list[str | None]]]:
    registry = registry or load_registry(root)
    return [(site, _read_site(root, site)) for site in registry["sites"]]


# --- validating ---------------------------------------------------------------

def check(root: Path, expected: str, registry: dict | None = None) -> list[Finding]:
    """Return EVERY mismatch, never aborting on the first one."""
    registry = registry or load_registry(root)
    findings: list[Finding] = []

    canonical = read_canonical(root, registry)
    if canonical != expected:
        findings.append(
            Finding(registry["canonical"]["label"], registry["canonical"]["path"], canonical, expected)
        )

    for site, values in read_all(root, registry):
        for value in values:
            if value != expected:
                findings.append(Finding(site["label"], site["path"], value, expected))

    for rule in registry.get("must_not_carry_version", []):
        path = root / rule["path"]
        if not path.is_file():
            continue
        try:
            doc = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        value = _pointer_get(doc, rule["pointer"])
        if value is not None:
            findings.append(
                Finding(f"{rule['label']} must not carry a version", rule["path"], str(value), "absent")
            )
    return findings


# --- writing ------------------------------------------------------------------

def _write_site(root: Path, site: dict, version: str) -> bool:
    """Write the version into one site. Returns True when the file changed."""
    path = root / site["path"]
    if not path.is_file():
        raise VersionSiteError(f"declared version site is missing: {site['path']}")
    original = path.read_text(encoding="utf-8")
    kind = site["kind"]

    if kind == "json":
        doc = json.loads(original)
        if not _pointer_set(doc, site["pointer"], version):
            raise VersionSiteError(f"pointer {site['pointer']} not found in {site['path']}")
        updated = json.dumps(doc, indent=2, ensure_ascii=False) + "\n"
    else:
        pattern = re.compile(site["pattern"])
        if not pattern.search(original):
            raise VersionSiteError(
                f"pattern for {site['label']} did not match anything in {site['path']}"
            )
        count = 0 if kind == "regex_all" else 1
        updated = pattern.sub(lambda m: f"{m.group(1)}{version}{m.group(3) if m.lastindex and m.lastindex >= 3 else ''}", original, count=count)

    if updated == original:
        return False
    path.write_text(updated, encoding="utf-8", newline="\n")
    return True


def write_all(root: Path, version: str, registry: dict | None = None) -> list[str]:
    """Write the version to every declared site. Returns the changed paths."""
    if not SEMVER.match(version):
        raise VersionSiteError(f"not a MAJOR.MINOR.PATCH version: {version!r}")
    registry = registry or load_registry(root)
    changed: list[str] = []
    for site in registry["sites"]:
        if _write_site(root, site, version):
            changed.append(f"{site['path']} ({site['label']})")
    return changed


def format_findings(findings: Iterable[Finding]) -> str:
    return "\n".join(f"  - {f}" for f in findings)
