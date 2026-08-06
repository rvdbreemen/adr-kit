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
import os
import re
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

REGISTRY_RELPATH = "packaging/version-sites.json"
SEMVER = re.compile(r"^\d+\.\d+\.\d+$")

#: Every `kind` this module can read and write. A registry entry declaring
#: anything else is a hard error at both ends: verified-but-never-written is the
#: exact failure mode ADR-013 exists to prevent.
SITE_KINDS = frozenset({"json", "regex", "regex_all"})


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
    raise VersionSiteError(_unknown_kind_message(kind, site["path"]))


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

def _unknown_kind_message(kind: object, path: str) -> str:
    return (
        f"unknown site kind {kind!r} for {path}; this module implements "
        f"{sorted(SITE_KINDS)}. A kind nothing writes would leave the site "
        "verified but never bumped, which is the drift ADR-013 exists to stop."
    )


def _rewrite(site: dict, text: str, version: str) -> str:
    """Return `text` with the version substituted. Pure: touches no file."""
    kind = site["kind"]

    if kind == "json":
        try:
            doc = json.loads(text)
        except json.JSONDecodeError as exc:
            raise VersionSiteError(f"invalid JSON in {site['path']}: {exc}") from exc
        if not _pointer_set(doc, site["pointer"], version):
            raise VersionSiteError(f"pointer {site['pointer']} not found in {site['path']}")
        return json.dumps(doc, indent=2, ensure_ascii=False) + "\n"

    if kind in {"regex", "regex_all"}:
        pattern = re.compile(site["pattern"])
        if not pattern.search(text):
            raise VersionSiteError(
                f"pattern for {site['label']} did not match anything in {site['path']}"
            )
        count = 0 if kind == "regex_all" else 1
        return pattern.sub(
            lambda m: f"{m.group(1)}{version}{m.group(3) if m.lastindex and m.lastindex >= 3 else ''}",
            text,
            count=count,
        )

    raise VersionSiteError(_unknown_kind_message(kind, site["path"]))


def plan_writes(
    root: Path,
    version: str,
    registry: dict | None = None,
    overrides: dict[Path, str] | None = None,
) -> dict[Path, bytes]:
    """Compute the post-image of every declared site without touching the disk.

    `overrides` seeds a file's pre-image with text the caller has already
    computed, instead of reading it from disk. The bump writer needs this for
    CHANGELOG.md: it inserts the release heading and rewrites the compare-link
    block, and the registry *also* declares the `[Unreleased]` link line as a
    site. Without a shared pre-image the two are computed from the same stale
    bytes and the caller has to pick one, which is how the link block came to be
    written by a tool the runbook does not name (TASK-139). One image, folded in
    order, is the only version of this that cannot silently drop half the edit.

    Planning the whole registry before the first byte is written is what makes an
    undeclarable site loud instead of silent: a `kind` this module does not
    implement, a pattern that matches nothing or a pointer that does not resolve
    aborts the entire bump, rather than being skipped or leaving the sites ahead
    of it written and the rest stale.

    Every planning failure is collected and reported together, because a release
    should surface its complete work list in one pass (ADR-013) instead of one
    error per run.

    Sites are folded into a shared working image in registry order, because two
    sites may declare the same path -- README.md carries both version pins -- and
    the second substitution must see the first one's edit rather than the stale
    bytes on disk.

    Returns only the paths whose content actually changes.
    """
    registry = registry or load_registry(root)
    originals: dict[Path, str] = {}
    working: dict[Path, str] = {}
    missing: set[Path] = set()
    errors: list[str] = []

    # An override still compares against the bytes on disk, so a file the caller
    # rewrote is reported as changed even when no declared site matched in it.
    for path, text in (overrides or {}).items():
        originals[path] = path.read_text(encoding="utf-8") if path.is_file() else ""
        working[path] = text

    for site in registry["sites"]:
        path = root / site["path"]
        if path in missing:
            continue
        if path not in originals:
            if not path.is_file():
                missing.add(path)
                errors.append(f"declared version site is missing: {site['path']}")
                continue
            originals[path] = path.read_text(encoding="utf-8")
            working[path] = originals[path]
        try:
            working[path] = _rewrite(site, working[path], version)
        except VersionSiteError as exc:
            errors.append(str(exc))

    if errors:
        raise VersionSiteError(
            "cannot write the version to every declared site:\n"
            + "\n".join(f"  - {message}" for message in errors)
        )
    return {
        path: text.encode("utf-8")
        for path, text in working.items()
        if text != originals[path]
    }


def _atomic_write_bytes(path: Path, content: bytes) -> None:
    """Replace `path` in one step, so no reader ever sees a half-written file."""
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
            temp_path = Path(handle.name)
        os.replace(temp_path, path)
        temp_path = None
    finally:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)


def apply_transaction(changes: dict[Path, bytes]) -> None:
    """Write every planned change, restoring all of them if any write fails.

    A release tool that leaves half the manifests bumped is worse than one that
    misses a file: the tree then carries two versions and no tool can tell which
    is intended. Only the paths already written are restored -- `_atomic_write_bytes`
    replaces in one step, so a failed write left its target untouched, and
    rewriting it could only invent a second failure.
    """
    originals = {path: path.read_bytes() for path in changes}
    written: list[Path] = []
    try:
        for path, content in changes.items():
            _atomic_write_bytes(path, content)
            written.append(path)
    except BaseException as exc:
        rollback_errors = []
        for path in written:
            try:
                _atomic_write_bytes(path, originals[path])
            except BaseException as rollback_exc:  # pragma: no cover - catastrophic
                rollback_errors.append(f"{path}: {rollback_exc}")
        if rollback_errors:
            raise VersionSiteError(
                f"release write failed ({exc}); rollback also failed: "
                + "; ".join(rollback_errors)
            ) from exc
        raise VersionSiteError(
            f"release write failed; all targets were rolled back: {exc}"
        ) from exc


def describe_changes(root: Path, changes: dict, registry: dict | None = None) -> list[str]:
    """Render a planned change set as `path (label, label)` lines, in registry order."""
    registry = registry or load_registry(root)
    labels: dict[str, list[str]] = {}
    for site in registry["sites"]:
        if (root / site["path"]) in changes:
            labels.setdefault(site["path"], []).append(site["label"])
    return [f"{path} ({', '.join(names)})" for path, names in labels.items()]


def write_all(root: Path, version: str, registry: dict | None = None) -> list[str]:
    """Write the version to every declared site. Returns the changed paths."""
    if not SEMVER.match(version):
        raise VersionSiteError(f"not a MAJOR.MINOR.PATCH version: {version!r}")
    registry = registry or load_registry(root)
    changes = plan_writes(root, version, registry)
    apply_transaction(changes)
    return describe_changes(root, changes, registry)


def format_findings(findings: Iterable[Finding]) -> str:
    return "\n".join(f"  - {f}" for f in findings)
