"""Every key the config schema declares must be read by something.

A setting that accepts a value and ignores it is worse than a missing one: the
user changes it, sees no effect, and plans around a bound that is not in force.
Nine such keys shipped before this gate existed (TASK-131). They are recorded in
adr_config.RETIRED_KEYS rather than deleted, so an existing .adr-kit.json that
still sets one keeps loading.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SCHEMA = ROOT / "schemas" / "adr-kit-config.schema.json"

# Where a config key may plausibly be read. Excludes the mirrors, which are
# byte-copies of these trees, and tests, which would let a key be "read" by a
# test that only asserts it exists.
SEARCH_ROOTS = ("bin", "hooks", "templates", "scripts", "clients")

# Keys whose reader resolves them dynamically, so a literal search cannot find
# them. Each entry needs a reason; an empty reason is not an exemption.
DYNAMIC_READERS: dict[str, str] = {}


def _declared_keys() -> dict[str, str]:
    """Map every declared property to its dotted path."""
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    found: dict[str, str] = {}

    def walk(node: object, path: str) -> None:
        if not isinstance(node, dict):
            return
        for key, child in (node.get("properties") or {}).items():
            found[key] = f"{path}.{key}"
            walk(child, f"{path}.{key}")
        for keyword in ("items", "additionalProperties"):
            if isinstance(node.get(keyword), dict):
                walk(node[keyword], f"{path}[]")
        for keyword in ("allOf", "anyOf", "oneOf"):
            for sub in node.get(keyword) or []:
                walk(sub, path)

    walk(schema, "$")
    return found


def _has_reader(key: str) -> bool:
    result = subprocess.run(
        ["git", "grep", "-l", "--", key, "--", *SEARCH_ROOTS],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    return bool(result.stdout.strip())


def test_every_declared_config_key_is_read_somewhere():
    orphans = sorted(
        f"{path} (declared in {SCHEMA.name}, read by nothing under {'/, '.join(SEARCH_ROOTS)}/)"
        for key, path in _declared_keys().items()
        if key not in DYNAMIC_READERS and not _has_reader(key)
    )
    assert not orphans, (
        "config keys with no reader:\n  "
        + "\n  ".join(orphans)
        + "\n\nWire each key to the code path it names, or remove it from the "
        "schema and add it to adr_config.RETIRED_KEYS so existing configs "
        "keep loading."
    )


def test_retired_keys_are_absent_from_the_schema():
    """A retired key must not also be declared -- that would be both at once."""
    sys.path.insert(0, str(ROOT / "bin"))
    from adr_config import RETIRED_KEYS

    declared = set(_declared_keys().values())
    both = sorted(set(RETIRED_KEYS) & declared)
    assert not both, f"declared and retired at the same time: {both}"


def test_a_retired_key_loads_with_a_warning_rather_than_failing(tmp_path):
    """An existing config that sets a retired key must keep working."""
    sys.path.insert(0, str(ROOT / "bin"))
    from adr_config import load_project_config, retired_keys_present

    config = {"judge": {"llm_timeout_ms": 30000, "llm_timeout_seconds": 60}}
    path = tmp_path / ".adr-kit.json"
    path.write_text(json.dumps(config), encoding="utf-8")

    loaded = load_project_config(path, SCHEMA)
    assert loaded["judge"]["llm_timeout_seconds"] == 60
    assert retired_keys_present(loaded) == ["$.judge.llm_timeout_ms"]


def test_adr_lint_accepts_a_config_that_still_sets_a_retired_key(tmp_path):
    """adr-lint validates with a real schema engine, which does not know about
    RETIRED_KEYS on its own. If it disagreed with adr_config, removing a key
    nothing read would newly FAIL every project that still sets one -- the exact
    breakage the retirement list exists to prevent.
    """
    adr_dir = tmp_path / "docs" / "adr"
    adr_dir.mkdir(parents=True)
    (adr_dir / ".adr-kit.json").write_text(
        json.dumps(
            {
                "judge": {"llm_timeout_ms": 30000, "pre_push_timeout_ms": 15000},
                "context": {"weights": {"exact_keyword": 0.4, "recency": 0.6}},
            }
        ),
        encoding="utf-8",
    )
    result = subprocess.run(
        [sys.executable, str(ROOT / "bin" / "adr-lint"), "--gates", "all", str(adr_dir)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    assert "schema validation failed" not in result.stdout, result.stdout[-1500:]
    assert "unknown" not in result.stdout.lower(), result.stdout[-1500:]


def test_an_unknown_key_that_was_never_retired_still_fails(tmp_path):
    """The retirement list must not become a hole for typos."""
    sys.path.insert(0, str(ROOT / "bin"))
    from adr_config import ConfigValidationError, load_project_config

    path = tmp_path / ".adr-kit.json"
    path.write_text(json.dumps({"judge": {"llm_timeuot_seconds": 60}}), encoding="utf-8")

    with pytest.raises(ConfigValidationError, match="unknown property"):
        load_project_config(path, SCHEMA)
