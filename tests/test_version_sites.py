"""The version-site registry is the single source of truth for the release version.

These tests keep the registry honest: every declared site must exist, the repo
must be self-consistent, and the registry must still cover the manifests the
client-adapter generator independently validates. That last check is what stops
the two lists from drifting apart, which is how a bump previously leaked past one
tool and got caught by another several minutes later.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from version_sites import (  # noqa: E402
    check,
    load_registry,
    read_all,
    read_canonical,
)


@pytest.fixture(scope="module")
def registry() -> dict:
    return load_registry(REPO_ROOT)


def test_every_declared_site_exists(registry):
    missing = [
        site["path"]
        for site in registry["sites"]
        if not (REPO_ROOT / site["path"]).is_file()
    ]
    assert not missing, f"declared version sites do not exist: {missing}"


def test_every_site_yields_a_version(registry):
    empty = [
        site["path"]
        for site, values in read_all(REPO_ROOT, registry)
        if not values or any(v is None for v in values)
    ]
    assert not empty, f"declared version sites yielded no version: {empty}"


def test_repository_is_version_consistent(registry):
    canonical = read_canonical(REPO_ROOT, registry)
    assert canonical, "CHANGELOG.md has no release heading"
    findings = check(REPO_ROOT, canonical, registry)
    assert not findings, "version drift:\n" + "\n".join(f"  - {f}" for f in findings)


def test_registry_covers_the_manifests_the_generator_validates(registry):
    # scripts/client_generation_artifacts.validate_manifests() checks these five
    # manifests independently. If it ever grows a sixth, the registry must learn
    # about it too, otherwise bump-version.py would silently leave it stale.
    generator_checked = {
        ".claude-plugin/plugin.json",
        "codex/.codex-plugin/plugin.json",
        "copilot/plugin.json",
        ".claude-plugin/marketplace.json",
        ".github/plugin/marketplace.json",
    }
    declared = {site["path"] for site in registry["sites"]}
    assert generator_checked <= declared, (
        "registry is missing manifests the generator validates: "
        f"{sorted(generator_checked - declared)}"
    )


def test_codex_local_marketplace_does_not_carry_a_version(registry):
    rules = registry.get("must_not_carry_version", [])
    assert rules, "expected the Codex local-marketplace inheritance rule"
    for rule in rules:
        doc = json.loads((REPO_ROOT / rule["path"]).read_text(encoding="utf-8"))
        plugins = doc.get("plugins") or []
        assert plugins, f"{rule['path']} has no plugins entry"
        assert "version" not in plugins[0], (
            f"{rule['label']} must inherit the plugin version: {rule['reason']}"
        )


def test_bump_version_check_passes_for_the_current_version(registry):
    version = read_canonical(REPO_ROOT, registry)
    proc = subprocess.run(
        [sys.executable, str(REPO_ROOT / "scripts" / "bump-version.py"), version, "--check"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
