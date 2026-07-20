"""Deterministic global/project settings resolution for ADR Kit."""

from __future__ import annotations

import json
import os
import stat
import tempfile
import urllib.error
import urllib.request
from copy import deepcopy
from pathlib import Path
from typing import Any, Iterable


DEFAULTS: dict[str, Any] = {
    "pre_commit": {"enabled": True},
    "update": {
        "policy": "verified-stable-auto",
        "trigger": "project-setup",
        "frequency_hours": 24,
        "offline": False,
        "pinned_version": None,
    },
    "clients": {
        "claude": {"enabled": None},
        "codex": {"enabled": None},
        "copilot": {"enabled": None},
    },
    "judgment": {
        "local": {
            "enabled": True,
            "provider": None,
            "model": None,
        },
        "cloud": {"enabled": False},
    },
    "doctor": {
        "auto_repair": True,
        "check_only": False,
    },
}

ALLOWED_KEYS = frozenset()


class SettingsError(RuntimeError):
    """Raised when a settings document or key is invalid."""


def _flatten(value: dict[str, Any], prefix: str = "") -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, item in value.items():
        dotted = f"{prefix}.{key}" if prefix else key
        if isinstance(item, dict):
            result.update(_flatten(item, dotted))
        else:
            result[dotted] = item
    return result


ALLOWED_KEYS = frozenset(_flatten(DEFAULTS))


def global_settings_path(env: dict[str, str] | None = None) -> Path:
    values = os.environ if env is None else env
    if values.get("ADR_KIT_GLOBAL_SETTINGS"):
        return Path(values["ADR_KIT_GLOBAL_SETTINGS"]).expanduser()
    if os.name == "nt":
        base = Path(values.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    else:
        base = Path(values.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return base / "adr-kit" / "settings.json"


def project_settings_path(project_root: Path) -> Path:
    return project_root / ".adr-kit" / "settings.json"


def load_document(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise SettingsError(f"cannot read settings {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise SettingsError(f"settings root must be an object: {path}")
    unknown = sorted(set(_flatten(value)) - ALLOWED_KEYS)
    if unknown:
        raise SettingsError(
            f"unknown settings in {path}: {', '.join(unknown)}"
        )
    for key, item in _flatten(value).items():
        _validate_value(key, item)
    return value


def _set_nested(target: dict[str, Any], dotted: str, value: Any) -> None:
    parts = dotted.split(".")
    cursor = target
    for part in parts[:-1]:
        child = cursor.setdefault(part, {})
        if not isinstance(child, dict):
            raise SettingsError(f"setting path is not an object: {dotted}")
        cursor = child
    cursor[parts[-1]] = value


def _delete_nested(target: dict[str, Any], dotted: str) -> None:
    parts = dotted.split(".")
    stack: list[tuple[dict[str, Any], str]] = []
    cursor = target
    for part in parts[:-1]:
        child = cursor.get(part)
        if not isinstance(child, dict):
            return
        stack.append((cursor, part))
        cursor = child
    cursor.pop(parts[-1], None)
    for parent, key in reversed(stack):
        child = parent.get(key)
        if isinstance(child, dict) and not child:
            parent.pop(key)


def resolve_settings(
    project_root: Path,
    *,
    global_path: Path | None = None,
) -> dict[str, Any]:
    global_file = global_path or global_settings_path()
    project_file = project_settings_path(project_root)
    values = deepcopy(DEFAULTS)
    sources = {key: "default" for key in ALLOWED_KEYS}

    for source, document in (
        ("global", load_document(global_file)),
        ("project", load_document(project_file)),
    ):
        for key, value in _flatten(document).items():
            _set_nested(values, key, value)
            sources[key] = source

    entries = [
        {"key": key, "value": value, "source": sources[key]}
        for key, value in sorted(_flatten(values).items())
    ]
    return {
        "values": values,
        "entries": entries,
        "paths": {
            "global": str(global_file),
            "project": str(project_file),
        },
    }


def parse_cli_value(raw: str) -> Any:
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return raw


def write_setting(
    project_root: Path,
    scope: str,
    key: str,
    value: Any = None,
    *,
    unset: bool = False,
    global_path: Path | None = None,
) -> Path:
    if key not in ALLOWED_KEYS:
        raise SettingsError(f"unknown setting: {key}")
    if scope not in {"global", "project"}:
        raise SettingsError(f"invalid scope: {scope}")
    if not unset:
        _validate_value(key, value)
    path = (
        (global_path or global_settings_path())
        if scope == "global"
        else project_settings_path(project_root)
    )
    document = load_document(path)
    if unset:
        _delete_nested(document, key)
    else:
        _set_nested(document, key, value)
    _atomic_json_write(path, document)
    return path


def _validate_value(key: str, value: Any) -> None:
    boolean_keys = {
        "pre_commit.enabled",
        "update.offline",
        "judgment.local.enabled",
        "judgment.cloud.enabled",
        "doctor.auto_repair",
        "doctor.check_only",
    }
    if key in boolean_keys and type(value) is not bool:
        raise SettingsError(f"{key} must be boolean")
    if key.startswith("clients.") and key.endswith(".enabled"):
        if value is not None and type(value) is not bool:
            raise SettingsError(f"{key} must be boolean or null")
    if key == "update.policy" and value not in {
        "verified-stable-auto",
        "notify",
        "manual",
        "pinned",
    }:
        raise SettingsError(f"invalid update policy: {value}")
    if key == "update.trigger" and value not in {
        "project-setup",
        "deferred-maintenance",
        "manual",
    }:
        raise SettingsError(f"invalid update trigger: {value}")
    if key == "update.frequency_hours":
        if type(value) is not int or value < 1:
            raise SettingsError("update.frequency_hours must be an integer >= 1")
    if key in {
        "update.pinned_version",
        "judgment.local.provider",
        "judgment.local.model",
    } and value is not None:
        if not isinstance(value, str) or not value.strip():
            raise SettingsError(f"{key} must be a non-empty string or null")


def _atomic_json_write(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(value, indent=2, sort_keys=True) + "\n"
    old_mode = stat.S_IMODE(path.stat().st_mode) if path.exists() else None
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as out:
            out.write(payload)
            out.flush()
            os.fsync(out.fileno())
        if old_mode is not None:
            os.chmod(temporary, old_mode)
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def discover_ollama_models(
    *,
    endpoint: str = "http://127.0.0.1:11434/api/tags",
    timeout: float = 0.25,
) -> list[tuple[str, str]]:
    request = urllib.request.Request(endpoint, headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (
        OSError,
        UnicodeError,
        json.JSONDecodeError,
        urllib.error.URLError,
    ):
        return []
    models = payload.get("models", []) if isinstance(payload, dict) else []
    names = sorted(
        {
            item.get("name")
            for item in models
            if isinstance(item, dict) and isinstance(item.get("name"), str)
        }
    )
    return [("ollama", name) for name in names]


def local_judgment_state(
    values: dict[str, Any],
    *,
    discovered: Iterable[tuple[str, str]] = (),
    probed: bool = False,
) -> dict[str, Any]:
    local = values["judgment"]["local"]
    enabled = bool(local["enabled"])
    configured = (local.get("provider"), local.get("model"))
    candidates = sorted(set(discovered))

    if not enabled:
        return _judgment_result("disabled", False, *configured, "Enable local judgment in settings.")
    if all(configured):
        if not probed:
            return _judgment_result(
                "configured-unverified",
                False,
                *configured,
                "Run settings with --probe-models or adr-doctor --deep.",
            )
        if configured in candidates:
            return _judgment_result("healthy", True, *configured, None)
        return _judgment_result(
            "degraded",
            False,
            *configured,
            "Configured provider/model was not found; choose an installed model.",
        )
    if not probed:
        return _judgment_result(
            "unconfigured",
            False,
            None,
            None,
            "Configure provider/model or run bounded local discovery.",
        )
    if len(candidates) == 1:
        provider, model = candidates[0]
        return _judgment_result("healthy-discovered", True, provider, model, None)
    if not candidates:
        return _judgment_result(
            "unavailable",
            False,
            None,
            None,
            "No compatible local provider/model was found.",
        )
    return _judgment_result(
        "ambiguous",
        False,
        None,
        None,
        "Multiple local models were found; configure one explicitly.",
    )


def _judgment_result(
    status: str,
    active: bool,
    provider: str | None,
    model: str | None,
    action: str | None,
) -> dict[str, Any]:
    return {
        "status": status,
        "active": active,
        "provider": provider,
        "model": model,
        "action": action,
        "hook_hot_path": False,
    }
