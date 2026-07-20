"""Atomic, marker-owned ADR Kit project setup primitives."""

from __future__ import annotations

import difflib
import hashlib
import os
import re
import stat
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


MARKER_RE = re.compile(
    r"<!-- ADR-KIT (?P<label>[A-Z-]+) (?P<edge>START|END) -->"
)
CLIENT_FILES = {
    "codex": (Path("AGENTS.md"), "CODEX"),
    "claude": (Path("CLAUDE.md"), "CLAUDE"),
    "copilot": (Path(".github/copilot-instructions.md"), "COPILOT"),
}
LEGACY_GUIDES = {
    "codex": Path(".agents/adr-kit-guide.md"),
    "claude": Path(".claude/adr-kit-guide.md"),
}


class SetupError(RuntimeError):
    """Raised before setup writes when ownership or project state is unsafe."""


@dataclass(frozen=True)
class PlannedChange:
    path: Path
    old: bytes | None
    new: bytes | None
    action: str
    mode: int | None = None


def marker_block(client: str) -> str:
    label = CLIENT_FILES[client][1]
    commands = {
        "codex": (
            "Use `$adr-kit:context` before implementation, `$adr-kit:adr` for "
            "new decisions, and `$adr-kit:judge` before commit."
        ),
        "claude": (
            "Use `/adr-kit:context` before implementation, `/adr-kit:adr` for "
            "new decisions, and `/adr-kit:judge` before commit."
        ),
        "copilot": (
            "Use the ADR Kit context, ADR authoring, and judge prompts before "
            "implementation, architectural decisions, and commit."
        ),
    }
    return (
        f"<!-- ADR-KIT {label} START -->\n"
        "## ADR Kit\n\n"
        "Read `.adr-kit/ADR-guide.md` before architectural changes. "
        "Architecture decisions live in `docs/adr/`. "
        f"{commands[client]}\n"
        f"<!-- ADR-KIT {label} END -->"
    )


def _decode(data: bytes | None) -> tuple[str, str, bool]:
    if data is None:
        return "", "\n", False
    bom = data.startswith(b"\xef\xbb\xbf")
    text = data.decode("utf-8-sig")
    newline = "\r\n" if "\r\n" in text else "\n"
    return text, newline, bom


def _encode(text: str, newline: str, bom: bool) -> bytes:
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    payload = normalized.replace("\n", newline).encode("utf-8")
    return (b"\xef\xbb\xbf" + payload) if bom else payload


def validate_markers(text: str, path: Path) -> dict[str, tuple[int, int]]:
    markers: dict[str, dict[str, list[re.Match[str]]]] = {}
    for match in MARKER_RE.finditer(text):
        label = match.group("label")
        edge = match.group("edge")
        markers.setdefault(label, {"START": [], "END": []})[edge].append(match)

    intervals: dict[str, tuple[int, int]] = {}
    for label, edges in markers.items():
        starts, ends = edges["START"], edges["END"]
        if len(starts) != 1 or len(ends) != 1:
            raise SetupError(
                f"{path}: malformed or duplicate ADR Kit markers for {label}"
            )
        if starts[0].start() >= ends[0].start():
            raise SetupError(f"{path}: reversed ADR Kit markers for {label}")
        intervals[label] = (starts[0].start(), ends[0].end())

    ordered = sorted((start, end, label) for label, (start, end) in intervals.items())
    for index, (start, end, label) in enumerate(ordered):
        for other_start, other_end, other_label in ordered[index + 1 :]:
            if other_start < end:
                raise SetupError(
                    f"{path}: nested ADR Kit markers for {label}/{other_label}"
                )
            if other_start >= end:
                break
    return intervals


def update_instruction(
    path: Path,
    old: bytes | None,
    client: str,
) -> PlannedChange | None:
    text, newline, bom = _decode(old)
    intervals = validate_markers(text, path)
    label = CLIENT_FILES[client][1]
    candidates = [item for item in (label, "STUB" if client == "claude" else "") if item]
    present = [item for item in candidates if item in intervals]
    if len(present) > 1:
        raise SetupError(f"{path}: both legacy and current ADR Kit blocks exist")

    block = marker_block(client)
    if present:
        start, end = intervals[present[0]]
        updated = text[:start] + block + text[end:]
        action = "migrate-marker" if present[0] == "STUB" else "refresh-marker"
    else:
        separator = "" if not text else ("" if text.endswith(("\n", "\r")) else newline)
        updated = text + separator + (newline if text else "") + block + newline
        action = "create-marker"
    new = _encode(updated, newline, bom)
    if new == old:
        return None
    return PlannedChange(path, old, new, action)


def _backup_path(root: Path, source: Path, old: bytes, kind: str) -> Path:
    digest = hashlib.sha256(old).hexdigest()[:12]
    safe_name = source.as_posix().replace("/", "__")
    return root / ".adr-kit" / "backups" / f"{safe_name}.{digest}.{kind}.bak"


def _backup_change(path: Path, payload: bytes, action: str) -> PlannedChange | None:
    existing = path.read_bytes() if path.exists() else None
    if existing == payload:
        return None
    if existing is not None:
        raise SetupError(f"backup collision with different content: {path}")
    return PlannedChange(path, None, payload, action)


def _git(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(root), *args],
        text=True,
        capture_output=True,
        check=False,
        timeout=5,
    )


def _pre_commit_changes(
    root: Path,
    template: Path,
    enabled: bool,
) -> tuple[list[PlannedChange], bool]:
    git_dir = _git(root, "rev-parse", "--git-dir")
    if git_dir.returncode != 0:
        return [], False
    hooks_path_result = _git(root, "config", "--get", "core.hooksPath")
    hooks_path = (
        hooks_path_result.stdout.strip()
        if hooks_path_result.returncode == 0
        else ""
    )
    if enabled and hooks_path not in {"", ".githooks"}:
        raise SetupError(
            f"custom core.hooksPath is owned by the user: {hooks_path}"
        )

    hook = root / ".githooks" / "pre-commit"
    old = hook.read_bytes() if hook.exists() else None
    owned = old is not None and b"adr-kit pre-commit hook" in old
    if enabled:
        new = template.read_bytes()
        if old is not None and old != new and not owned:
            raise SetupError(f"refusing to replace user pre-commit hook: {hook}")
        change = (
            None
            if old == new
            else PlannedChange(hook, old, new, "install-pre-commit", 0o755)
        )
        return ([change] if change else []), hooks_path == ""
    if owned:
        return [PlannedChange(hook, old, None, "disable-pre-commit")], False
    return [], False


def collect_changes(
    root: Path,
    plugin_root: Path,
    clients: Iterable[str],
    *,
    pre_commit_enabled: bool,
) -> tuple[list[PlannedChange], bool]:
    selected = list(dict.fromkeys(clients))
    unknown = sorted(set(selected) - set(CLIENT_FILES))
    if unknown:
        raise SetupError(f"unknown clients: {', '.join(unknown)}")

    guide_source = plugin_root / "instructions" / "ADR-guide.md"
    hook_source = plugin_root / "templates" / "githooks" / "pre-commit"
    if not guide_source.is_file() or not hook_source.is_file():
        raise SetupError(f"ADR Kit source is incomplete: {plugin_root}")

    changes: list[PlannedChange] = []
    guide = root / ".adr-kit" / "ADR-guide.md"
    guide_old = guide.read_bytes() if guide.exists() else None
    guide_new = guide_source.read_bytes()
    if guide_old != guide_new:
        if guide_old is not None:
            backup = _backup_path(root, Path("ADR-guide.md"), guide_old, "generated")
            backup_change = _backup_change(backup, guide_old, "backup-guide")
            if backup_change:
                changes.append(backup_change)
        changes.append(
            PlannedChange(
                guide,
                guide_old,
                guide_new,
                "create-guide" if guide_old is None else "replace-guide",
            )
        )

    for client in selected:
        relative, _ = CLIENT_FILES[client]
        path = root / relative
        old = path.read_bytes() if path.exists() else None
        change = update_instruction(path, old, client)
        if change:
            if old is not None:
                backup = _backup_path(root, relative, old, "instruction")
                backup_change = _backup_change(
                    backup, old, "backup-instruction"
                )
                if backup_change:
                    changes.append(backup_change)
            changes.append(change)

    for client, legacy_relative in LEGACY_GUIDES.items():
        if client not in selected:
            continue
        legacy = root / legacy_relative
        if not legacy.exists():
            continue
        payload = legacy.read_bytes()
        backup = _backup_path(root, legacy_relative, payload, "legacy")
        backup_change = _backup_change(backup, payload, "backup-legacy-guide")
        if backup_change:
            changes.append(backup_change)
        changes.append(
            PlannedChange(legacy, payload, None, "remove-legacy-guide")
        )

    hook_changes, configure_hooks_path = _pre_commit_changes(
        root, hook_source, pre_commit_enabled
    )
    changes.extend(hook_changes)
    return changes, configure_hooks_path


def render_diff(changes: Iterable[PlannedChange], root: Path) -> str:
    output: list[str] = []
    for change in changes:
        old_text = _decode(change.old)[0].splitlines(keepends=True)
        new_text = _decode(change.new)[0].splitlines(keepends=True)
        relative = change.path.relative_to(root).as_posix()
        output.extend(
            difflib.unified_diff(
                old_text,
                new_text,
                fromfile=f"a/{relative}",
                tofile=f"b/{relative}",
            )
        )
    return "".join(output)


def plan_uninstall(root: Path, clients: Iterable[str]) -> list[PlannedChange]:
    """Remove generated guide/owned blocks while preserving all user guidance."""
    changes: list[PlannedChange] = []
    guide = root / ".adr-kit" / "ADR-guide.md"
    if guide.is_file():
        changes.append(PlannedChange(guide, guide.read_bytes(), None, "remove-guide"))
    for client in clients:
        relative, label = CLIENT_FILES[client]
        path = root / relative
        if not path.is_file():
            continue
        old = path.read_bytes()
        text, newline, bom = _decode(old)
        intervals = validate_markers(text, path)
        if label not in intervals:
            continue
        start, end = intervals[label]
        updated = (text[:start] + text[end:]).strip()
        new = _encode(updated + (newline if updated else ""), newline, bom)
        changes.append(PlannedChange(path, old, new or None, "remove-managed-block"))
    return changes


def apply_changes(
    root: Path,
    changes: Iterable[PlannedChange],
    *,
    configure_hooks_path: bool,
) -> None:
    pending = list(changes)
    if not pending and not configure_hooks_path:
        return
    state_dir = root / ".adr-kit"
    state_dir.mkdir(parents=True, exist_ok=True)
    lock = state_dir / "setup.lock"
    try:
        descriptor = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError as exc:
        raise SetupError(f"another ADR Kit setup owns {lock}") from exc
    try:
        os.close(descriptor)
        for change in pending:
            if change.new is None:
                change.path.unlink(missing_ok=True)
                continue
            _atomic_write(change.path, change.new, change.mode)
        if configure_hooks_path:
            result = _git(root, "config", "core.hooksPath", ".githooks")
            if result.returncode != 0:
                raise SetupError(
                    f"git config core.hooksPath failed: {result.stderr.strip()}"
                )
    finally:
        lock.unlink(missing_ok=True)


def _atomic_write(path: Path, payload: bytes, mode: int | None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    current_mode = stat.S_IMODE(path.stat().st_mode) if path.exists() else mode
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as out:
            out.write(payload)
            out.flush()
            os.fsync(out.fileno())
        if current_mode is not None:
            os.chmod(temporary, current_mode)
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)
