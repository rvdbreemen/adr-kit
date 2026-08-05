"""Read-only, registry-driven ADR Kit client detection."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Sequence

from .contracts import CLIENT_IDS, SPECS, DetectedClient


@dataclass(frozen=True)
class Client:
    name: str
    executable: str
    version: str


Runner = Callable[[Sequence[str]], subprocess.CompletedProcess[str]]


def run_version(command: Sequence[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        list(command),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=10,
    )


def detect_client(
    name: str,
    *,
    which: Callable[[str], str | None] = shutil.which,
    runner: Runner = run_version,
) -> Client | None:
    spec = SPECS.get(name)
    if spec is None:
        raise ValueError(f"unsupported client: {name}")
    try:
        executable = which(name)
        if not executable:
            return None
        result = runner([executable, "--version"])
    except (OSError, subprocess.SubprocessError):
        return None
    version = (result.stdout + result.stderr).strip()
    if result.returncode != 0 or spec.version_marker.casefold() not in version.casefold():
        return None
    return Client(name, str(Path(executable).resolve()), version.splitlines()[0])


def detect_clients(
    *,
    which: Callable[[str], str | None] = shutil.which,
    runner: Runner = run_version,
) -> dict[str, Client]:
    return {
        name: client
        for name in CLIENT_IDS
        if (client := detect_client(name, which=which, runner=runner)) is not None
    }


def sha256_file(path: Path) -> str | None:
    if not path.is_file():
        return None
    digest = hashlib.sha256()
    try:
        with path.open("rb") as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(block)
    except OSError:
        return None
    return digest.hexdigest()


def _marker_roots(install_root: Path) -> list[tuple[Path, dict]]:
    found: list[tuple[Path, dict]] = []
    if not install_root.is_dir():
        return found
    for marker in sorted(install_root.glob("*/.adr-kit-prepared-source.json")):
        try:
            payload = json.loads(marker.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError):
            payload = {}
        found.append((marker.parent.resolve(), payload if isinstance(payload, dict) else {}))
    return found


def detailed_detection(
    clients: dict[str, Client],
    *,
    install_root: Path,
    effective_settings: dict,
    env: dict[str, str] | None = None,
) -> dict[str, DetectedClient]:
    """Enrich executable detection without invoking plugin managers or writing."""
    values = os.environ if env is None else env
    roots = _marker_roots(install_root)
    current = roots[-1] if roots else None
    duplicate_roots = tuple(str(root) for root, _ in roots[:-1])
    result: dict[str, DetectedClient] = {}
    for name, client in clients.items():
        spec = SPECS[name]
        enabled = effective_settings["clients"][name]["enabled"]
        override_key = {
            "claude": "CLAUDE_CONFIG_DIR",
            "codex": "CODEX_HOME",
            "copilot": "COPILOT_HOME",
        }[name]
        marker = current[1] if current else {}
        source = marker.get("source") if isinstance(marker.get("source"), str) else None
        result[name] = DetectedClient(
            id=spec.id,
            executable=client.executable,
            version=client.version,
            config_override=values.get(override_key),
            native_manager_available=True,
            installed_version=(
                marker.get("version")
                if isinstance(marker.get("version"), str)
                else None
            ),
            source=source,
            source_sha256=sha256_file(Path(source) / spec.manifest) if source else None,
            legacy_footprints=tuple(
                str(path)
                for path in (
                    install_root.parent / "cache",
                    install_root.parent / "plugins",
                )
                if path.exists()
            ),
            disabled=enabled is False,
            trusted=None,
            duplicate_roots=duplicate_roots,
        )
    return result
