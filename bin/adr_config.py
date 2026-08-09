"""Shared, stdlib-only validation for adr-kit project configuration."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List


class ConfigValidationError(ValueError):
    """Raised when .adr-kit.json is malformed or violates its schema."""


# Keys the schema once declared and no code ever read. Removing them outright
# would fail every existing config that sets one, so they are accepted and
# ignored instead: the value never took effect, and breaking the file over a
# setting that was already inert would be a worse trade than a warning.
# A caller that wants to surface them uses retired_keys_present().
RETIRED_KEYS: Dict[str, str] = {
    "$.judge.llm_timeout_ms": (
        "never read; judge.llm_timeout_seconds is the timeout that applies"
    ),
    "$.judge.pre_push_timeout_ms": (
        "never read; adr-kit ships no pre-push hook for it to bound"
    ),
    "$.policy.regex_compile_checks": (
        "never read; adr-lint always compiles Enforcement patterns"
    ),
    "$.policy.pattern_warnings": (
        "never read; adr-lint always emits anti-pattern advisories"
    ),
    "$.context.weights": (
        "never read; the index-first scorer replaced weighted signals in v0.40.0"
    ),
    "$.context.weights.exact_keyword": "part of the retired context.weights block",
    "$.context.weights.domain_tag": "part of the retired context.weights block",
    "$.context.weights.related_decisions": (
        "part of the retired context.weights block"
    ),
    "$.context.weights.acceptance_status": (
        "part of the retired context.weights block"
    ),
    "$.context.weights.recency": "part of the retired context.weights block",
}

# Keys that DID something and no longer do (ADR-036). Unlike RETIRED_KEYS,
# these are refused rather than ignored: a config naming one made a real
# choice once - a backend, a model, a command - and silently dropping that
# choice would be the exact drift the kit exists to prevent. Each entry is
# the sentence "unknown property" cannot say: what replaced the key.
REMOVED_KEYS: Dict[str, str] = {
    "$.judge.openrouter_model": (
        "the openrouter backend was retired by ADR-036; the judge runs on the "
        "host client's own model. Remove the key; operators can override per "
        "run with ADR_KIT_LLM_CMD / --llm-cmd."
    ),
    "$.judge.ollama_model": (
        "the ollama backend was retired by ADR-036; the judge runs on the "
        "host client's own model. Remove the key; operators can override per "
        "run with ADR_KIT_LLM_CMD / --llm-cmd."
    ),
    "$.judge.openai_model": (
        "the openai-compatible backend was retired by ADR-036; the judge runs "
        "on the host client's own model. Remove the key; operators can "
        "override per run with ADR_KIT_LLM_CMD / --llm-cmd."
    ),
    "$.judge.llm_cmd": (
        "ignored since ADR-017 and removed by ADR-036: repository-tracked "
        "configuration may never supply a command. Remove the key; operators "
        "use ADR_KIT_LLM_CMD / --llm-cmd."
    ),
    "$.judge.llm_model": (
        "ignored since ADR-017 and removed by ADR-036: the host backend "
        "passes no model flag, so each CLI resolves the model its own user "
        "configured. Remove the key."
    ),
    "$.judge.llm_default": (
        "removed by ADR-036; judge.llm_enabled is the per-commit switch. "
        "Remove the key."
    ),
    "$.suggest.llm_cmd": (
        "ignored since ADR-017 and removed by ADR-036: repository-tracked "
        "configuration may never supply a command. Remove the key; operators "
        "use ADR_KIT_LLM_CMD / --llm-cmd."
    ),
    "$.suggest.llm_model": (
        "ignored since ADR-017 and removed by ADR-036: adr-suggest resolves "
        "the same host backend as the judge. Remove the key."
    ),
}


def retired_keys_present(config: Any) -> List[str]:
    """Return the dotted paths of retired keys this config still sets.

    Callers print these as a warning. The values are inert either way.
    """
    found: List[str] = []

    def walk(value: Any, path: str) -> None:
        if not isinstance(value, dict):
            return
        for key, item in value.items():
            child = _path(path, str(key))
            if child in RETIRED_KEYS:
                found.append(child)
                continue
            walk(item, child)

    walk(config, "$")
    return sorted(found)


def _type_matches(value: Any, expected: str) -> bool:
    if expected == "object":
        return isinstance(value, dict)
    if expected == "array":
        return isinstance(value, list)
    if expected == "string":
        return isinstance(value, str)
    if expected == "boolean":
        return isinstance(value, bool)
    if expected == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if expected == "null":
        return value is None
    return True


def _path(parent: str, key: str) -> str:
    if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", key):
        return f"{parent}.{key}"
    return f"{parent}[{json.dumps(key, ensure_ascii=False)}]"


def _validate(value: Any, schema: Dict[str, Any], path: str) -> List[str]:
    issues: List[str] = []

    if "oneOf" in schema:
        matches = [
            candidate
            for candidate in schema["oneOf"]
            if not _validate(value, candidate, path)
        ]
        if len(matches) != 1:
            issues.append(f"{path}: must match exactly one allowed schema")
        return issues

    expected = schema.get("type")
    if isinstance(expected, str) and not _type_matches(value, expected):
        issues.append(f"{path}: expected {expected}, got {type(value).__name__}")
        return issues

    if "enum" in schema and value not in schema["enum"]:
        issues.append(
            f"{path}: must be one of {', '.join(repr(item) for item in schema['enum'])}"
        )

    if isinstance(value, str):
        min_length = schema.get("minLength")
        if isinstance(min_length, int) and len(value) < min_length:
            issues.append(f"{path}: must contain at least {min_length} character(s)")
        pattern = schema.get("pattern")
        if isinstance(pattern, str) and re.search(pattern, value) is None:
            issues.append(f"{path}: does not match required pattern {pattern!r}")

    if isinstance(value, list):
        min_items = schema.get("minItems")
        if isinstance(min_items, int) and len(value) < min_items:
            issues.append(f"{path}: must contain at least {min_items} item(s)")
        item_schema = schema.get("items")
        if isinstance(item_schema, dict):
            for index, item in enumerate(value):
                issues.extend(_validate(item, item_schema, f"{path}[{index}]"))

    if isinstance(value, (int, float)) and not isinstance(value, bool):
        minimum = schema.get("minimum")
        maximum = schema.get("maximum")
        if isinstance(minimum, (int, float)) and value < minimum:
            issues.append(f"{path}: must be >= {minimum}")
        if isinstance(maximum, (int, float)) and value > maximum:
            issues.append(f"{path}: must be <= {maximum}")

    if isinstance(value, dict):
        properties = schema.get("properties", {})
        pattern_properties = schema.get("patternProperties", {})
        required = schema.get("required", [])
        for key in required:
            if key not in value:
                issues.append(f"{_path(path, key)}: required property is missing")
        for key, item in value.items():
            child_path = _path(path, str(key))
            if key in properties:
                issues.extend(_validate(item, properties[key], child_path))
                continue
            matching = [
                child_schema
                for pattern, child_schema in pattern_properties.items()
                if re.search(pattern, str(key))
            ]
            if matching:
                for child_schema in matching:
                    issues.extend(_validate(item, child_schema, child_path))
                continue
            if child_path in RETIRED_KEYS:
                continue
            if child_path in REMOVED_KEYS:
                issues.append(f"{child_path}: {REMOVED_KEYS[child_path]}")
                continue
            additional = schema.get("additionalProperties", True)
            if additional is False:
                issues.append(f"{child_path}: unknown property")
            elif isinstance(additional, dict):
                issues.extend(_validate(item, additional, child_path))

    return issues


def validate_project_config(config: Any, schema_path: Path) -> Dict[str, Any]:
    """Validate config against the checked-in schema and return it as a dict."""
    try:
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ConfigValidationError(
            f"cannot load configuration schema {schema_path}: {exc}"
        ) from exc
    issues = _validate(config, schema, "$")
    if issues:
        raise ConfigValidationError("; ".join(issues))
    return config


def load_project_config(path: Path, schema_path: Path) -> Dict[str, Any]:
    """Read and validate one .adr-kit.json file; missing files mean defaults."""
    if not path.exists():
        return {}
    try:
        config = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ConfigValidationError(f"cannot read {path}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise ConfigValidationError(
            f"{path}: invalid JSON ({exc.msg} at line {exc.lineno})"
        ) from exc
    try:
        return validate_project_config(config, schema_path)
    except ConfigValidationError as exc:
        raise ConfigValidationError(f"{path}: schema validation failed: {exc}") from exc


DEFAULT_CONFIG_SCHEMA = (
    Path(__file__).resolve().parent.parent / "schemas" / "adr-kit-config.schema.json"
)


def load_validated_config(path: Path | None) -> Dict[str, Any]:
    """Read and schema-validate .adr-kit.json against the shipped schema.

    Callers that need their own error type catch ConfigValidationError and
    re-raise. A missing path or file yields defaults.
    """
    if path is None:
        return {}
    return load_project_config(path, DEFAULT_CONFIG_SCHEMA)


def load_json_config(path: Path) -> Dict[str, Any]:
    """Read a JSON config object tolerantly; anything unusable yields {}.

    The fail-open reader used by the advisory hook entry points, where a broken
    config must never interrupt an edit or a session start.
    """
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}
