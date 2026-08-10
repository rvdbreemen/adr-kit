"""Read what each client's OWN registration says is installed.

Detection cannot do this itself. It is mirrored into the generated codex/ and
copilot/ trees, where it must stay stdlib-only and free of per-client quirks,
and it promises in its own docstring not to invoke plugin managers. So the
quirks live here and the answer is handed to ``detailed_detection`` as data.

Every client stores this somewhere different, in a different shape, and one of
the three does not store it at all:

* claude  - ``installed_plugins.json``, strict JSON, a list of scope-tagged
  entries per plugin id, each carrying ``version``.
* copilot - ``config.json``, which is JSONC: it opens with ``//`` banner lines
  that ``json.loads`` rejects.
* codex   - ``config.toml`` records that the plugin is enabled and nothing
  more. There is no version in that file, and ``tomllib`` is 3.11+ against a
  declared floor of 3.10, so the version comes from the client's own
  ``plugin list --json`` instead.

Every reader is fail-soft: an unreadable, missing or malformed registration
means "unknown", never a crash and never a fabricated version. Reporting a
version nobody read is the defect this module exists to remove (TASK-166).
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Callable, Mapping, Sequence

from .contracts import SPECS
from .detection import Client

Runner = Callable[[Sequence[str]], subprocess.CompletedProcess[str]]

MARKETPLACES = {name: SPECS[name].marketplace for name in SPECS}


def _home(env: Mapping[str, str] | None, key: str, default: str) -> Path:
    values = os.environ if env is None else env
    override = values.get(key)
    return Path(override) if override else Path.home() / default


def _strip_line_comments(text: str) -> str:
    """Drop whole ``//`` lines so JSONC parses.

    Only whole comment lines go: a ``//`` inside a string value, such as a URL,
    is left alone.
    """
    return "\n".join(
        "" if line.lstrip().startswith("//") else line for line in text.splitlines()
    )


def _load_json(path: Path, *, jsonc: bool = False) -> dict:
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return {}
    try:
        document = json.loads(_strip_line_comments(text) if jsonc else text)
    except json.JSONDecodeError:
        return {}
    return document if isinstance(document, dict) else {}


def claude_installed_version(env: Mapping[str, str] | None = None) -> str | None:
    document = _load_json(
        _home(env, "CLAUDE_CONFIG_DIR", ".claude") / "plugins" / "installed_plugins.json"
    )
    plugins = document.get("plugins")
    entries = plugins.get(f"adr-kit@{MARKETPLACES['claude']}") if isinstance(plugins, dict) else None
    for entry in entries or []:
        if isinstance(entry, dict) and entry.get("scope", "user") == "user":
            version = entry.get("version")
            return version if isinstance(version, str) and version else None
    return None


def copilot_installed_version(env: Mapping[str, str] | None = None) -> str | None:
    document = _load_json(_home(env, "COPILOT_HOME", ".copilot") / "config.json", jsonc=True)
    for entry in document.get("installedPlugins") or []:
        if isinstance(entry, dict) and entry.get("name") == "adr-kit":
            version = entry.get("version")
            return version if isinstance(version, str) and version else None
    return None


def codex_installed_version(client: Client | None, runner: Runner) -> str | None:
    """Ask codex, because its config.toml records enablement but not a version."""
    if client is None:
        return None
    try:
        result = runner([client.executable, "plugin", "list", "--json"])
    except (OSError, subprocess.SubprocessError):
        return None
    if result.returncode:
        return None
    try:
        document = json.loads(result.stdout or "{}")
    except json.JSONDecodeError:
        return None
    # Codex answers {"installed": [{"pluginId": ..., "version": ...}]}; the
    # other spellings are accepted so a CLI rename does not silently read as
    # "not installed", which is the failure this module exists to prevent.
    entries: object = document
    if isinstance(document, dict):
        for key in ("installed", "plugins"):
            if isinstance(document.get(key), list):
                entries = document[key]
                break
    for entry in entries if isinstance(entries, list) else []:
        if not isinstance(entry, dict):
            continue
        identifier = entry.get("pluginId") or entry.get("id") or entry.get("name") or ""
        if "adr-kit" in str(identifier):
            version = entry.get("version")
            return version if isinstance(version, str) and version else None
    return None


def read_installed_versions(
    clients: Mapping[str, Client],
    *,
    runner: Runner,
    env: Mapping[str, str] | None = None,
) -> dict[str, str | None]:
    """What each detected client reports for itself; None where unknown."""
    return {
        "claude": claude_installed_version(env),
        "codex": codex_installed_version(clients.get("codex"), runner),
        "copilot": copilot_installed_version(env),
    }
