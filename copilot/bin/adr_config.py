"""Shared, stdlib-only validation for adr-kit project configuration."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List


class ConfigValidationError(ValueError):
    """Raised when .adr-kit.json is malformed or violates its schema."""


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
