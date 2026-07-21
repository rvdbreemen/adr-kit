"""Release allowlisting and warm-state cache for client generation."""

from __future__ import annotations

import fnmatch
import hashlib
import json
import os
import stat
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Iterable

from client_generation_model import (
    CACHE_VERSION,
    SOURCE_FILES,
    GenerationError,
    Stats,
    encoded_json,
)


def _safe_release_path(path: str, allowlist: dict) -> bool:
    normalized = path.replace("\\", "/")
    if normalized.startswith("./"):
        normalized = normalized[2:]
    segments = set(normalized.split("/"))
    for forbidden in allowlist.get("forbidden_segments", []):
        token = forbidden.replace("\\", "/").strip("/")
        if "/" not in token and token in segments:
            return False
        if normalized == token or normalized.startswith(token + "/"):
            return False
    for pattern in allowlist.get("forbidden_globs", []):
        portable = pattern.replace("\\", "/")
        if fnmatch.fnmatchcase(normalized, portable):
            return False
        if portable.startswith("**/") and fnmatch.fnmatchcase(
            normalized, portable[3:]
        ):
            return False
    return any(
        normalized == item or normalized.startswith(item.rstrip("/") + "/")
        for item in allowlist.get("include_roots", [])
    )


def validate_release_paths(paths: Iterable[str], allowlist: dict) -> list[str]:
    return sorted(path for path in paths if not _safe_release_path(path, allowlist))


def collect_release_files(root: Path, allowlist: dict) -> list[str]:
    """Collect only declared public files without traversing the repository root."""
    files: set[str] = set()
    invalid_roots = validate_release_paths(
        allowlist.get("include_roots", []),
        allowlist,
    )
    if invalid_roots:
        raise GenerationError(
            "forbidden public root selected: " + ", ".join(invalid_roots)
        )
    for declared in sorted(allowlist.get("include_roots", [])):
        path = root / declared
        if not path.exists():
            raise GenerationError(f"missing public artifact: {declared}")
        candidates = [path] if path.is_file() else path.rglob("*")
        for candidate in candidates:
            if candidate.is_symlink():
                raise GenerationError(
                    f"public artifact symlink is not allowed: "
                    f"{candidate.relative_to(root).as_posix()}"
                )
            if candidate.is_file():
                relative = candidate.relative_to(root).as_posix()
                if not validate_release_paths([relative], allowlist):
                    files.add(relative)
    return sorted(files)


def _cache_path(output_root: Path) -> Path:
    key = hashlib.sha256(str(output_root).encode("utf-8")).hexdigest()[:24]
    return Path(tempfile.gettempdir()) / "adr-kit-client-generation" / f"{key}.json"


def _source_stamps(source_root: Path, source_paths: list[Path]) -> list[list[object]]:
    paths = [source_root / name for name in SOURCE_FILES]
    paths.extend(
        (
            source_root / "CHANGELOG.md",
            source_root / "scripts/build-client-adapters.py",
            source_root / "scripts/client_generation.py",
            source_root / "scripts/client_generation_artifacts.py",
            source_root / "scripts/client_generation_model.py",
            source_root / "scripts/client_generation_state.py",
        )
    )
    paths.extend(source_paths)
    ordered = sorted(set(paths), key=lambda item: item.as_posix())

    def stamp(path: Path) -> list[object]:
        info = path.stat()
        return [
            path.relative_to(source_root).as_posix(),
            info.st_size,
            info.st_mtime_ns,
            stat.S_IMODE(info.st_mode),
        ]

    with ThreadPoolExecutor(max_workers=min(16, max(1, len(ordered)))) as pool:
        return list(pool.map(stamp, ordered))


def load_early_state(
    source_root: Path,
    output_root: Path,
    source_paths: list[Path],
    stats: Stats,
) -> bool:
    try:
        state = json.loads(_cache_path(output_root).read_text(encoding="utf-8"))
        if not isinstance(state, dict) or state.get("schema_version") != CACHE_VERSION:
            return False
        if state.get("sources") != _source_stamps(source_root, source_paths):
            return False
        files = state.get("files")
        if not isinstance(files, dict):
            return False
        ordered_files = sorted(files.items())

        def current_stamp(item: tuple[str, object]) -> list[object]:
            current = (output_root / item[0]).stat()
            return [
                current.st_size,
                current.st_mtime_ns,
                stat.S_IMODE(current.st_mode),
            ]

        with ThreadPoolExecutor(
            max_workers=min(16, max(1, len(ordered_files)))
        ) as pool:
            current_stamps = list(pool.map(current_stamp, ordered_files))
        if any(
            current != recorded
            for current, (_relative, recorded) in zip(
                current_stamps, ordered_files
            )
        ):
                return False
        directories = state.get("directories")
        if not isinstance(directories, dict):
            return False
        for relative, recorded in directories.items():
            path = output_root / relative
            current = path.stat().st_mtime_ns if path.is_dir() else None
            if current != recorded:
                return False
        stats.unchanged = len(files)
        return True
    except (
        GenerationError,
        FileNotFoundError,
        OSError,
        ValueError,
        TypeError,
        json.JSONDecodeError,
    ):
        return False


def _expected_fingerprint(expected: dict[str, tuple[bytes, int | None]]) -> str:
    digest = hashlib.sha256(b"adr-kit-client-generation-v1\0")
    for relative, (content, mode) in sorted(expected.items()):
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(str(mode).encode("ascii"))
        digest.update(b"\0")
        digest.update(content)
    return digest.hexdigest()


def load_fast_state(
    output_root: Path,
    expected: dict[str, tuple[bytes, int | None]],
    generated_roots: list[str],
) -> bool:
    try:
        state = json.loads(_cache_path(output_root).read_text(encoding="utf-8"))
        if state.get("fingerprint") != _expected_fingerprint(expected):
            return False
        files = state.get("files")
        if not isinstance(files, dict) or set(files) != set(expected):
            return False
        for relative, recorded in files.items():
            current = (output_root / relative).stat()
            if [
                current.st_size,
                current.st_mtime_ns,
                stat.S_IMODE(current.st_mode),
            ] != recorded:
                return False
        directories = state.get("directories")
        if not isinstance(directories, dict):
            return False
        for relative in generated_roots:
            path = output_root / relative
            current = path.stat().st_mtime_ns if path.is_dir() else None
            if directories.get(relative) != current:
                return False
        return True
    except (FileNotFoundError, OSError, ValueError, TypeError, json.JSONDecodeError):
        return False


def save_fast_state(
    source_root: Path,
    output_root: Path,
    source_paths: list[Path],
    expected: dict[str, tuple[bytes, int | None]],
    generated_roots: list[str],
) -> None:
    files = {}
    for relative in expected:
        current = (output_root / relative).stat()
        files[relative] = [
            current.st_size,
            current.st_mtime_ns,
            stat.S_IMODE(current.st_mode),
        ]
    directories = {}
    for relative in generated_roots:
        path = output_root / relative
        directories[relative] = path.stat().st_mtime_ns if path.is_dir() else None
    state = {
        "schema_version": CACHE_VERSION,
        "sources": _source_stamps(source_root, source_paths),
        "fingerprint": _expected_fingerprint(expected),
        "files": files,
        "directories": directories,
    }
    destination = _cache_path(output_root)
    destination.parent.mkdir(parents=True, exist_ok=True)
    content = encoded_json(state)
    try:
        if destination.read_bytes() == content:
            return
    except FileNotFoundError:
        pass
    descriptor, temporary = tempfile.mkstemp(prefix=".state.", dir=destination.parent)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(content)
        os.replace(temporary, destination)
    except BaseException:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise
