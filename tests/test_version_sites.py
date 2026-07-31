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
    SITE_KINDS,
    VersionSiteError,
    check,
    load_registry,
    plan_writes,
    read_all,
    read_canonical,
    write_all,
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


def test_every_declared_kind_is_one_the_engine_implements(registry):
    """A kind nothing writes would be verified but never bumped -- TASK-71's shape."""
    unknown = sorted(
        {
            site["kind"]
            for site in registry["sites"]
            if site.get("kind") not in SITE_KINDS
        }
    )
    assert not unknown, f"registry declares kinds the writer cannot handle: {unknown}"


def test_own_pre_commit_wrapper_is_a_declared_site(registry):
    """`.githooks/pre-commit` used to be written by bin/bump-version but declared
    nowhere, so nothing verified it. It is this repo's own copy of the wrapper
    whose stamp adr-guardian compares against the plugin version, so a stale one
    makes the staleness detector itself wrong.
    """
    declared = {site["path"] for site in registry["sites"]}
    assert ".githooks/pre-commit" in declared


# --- the write engine ---------------------------------------------------------

def _mini_repo(tmp_path: Path, version: str = "0.1.0") -> Path:
    root = tmp_path / "repo"
    (root / "packaging").mkdir(parents=True)
    (root / "CHANGELOG.md").write_text(f"# Changelog\n\n## [{version}] - 2026-01-01\n", encoding="utf-8")
    (root / "manifest.json").write_text(
        json.dumps({"name": "x", "version": version}, indent=2) + "\n", encoding="utf-8"
    )
    (root / "pins.md").write_text(
        f"first pin: adr-judge@v{version}\nsecond pin: rev: v{version}\n", encoding="utf-8"
    )
    return root


def _mini_registry(root: Path, extra_sites: list | None = None) -> dict:
    registry = {
        "schema_version": 1,
        "canonical": {
            "path": "CHANGELOG.md",
            "kind": "changelog_heading",
            "pattern": r"^## \[(\d+\.\d+\.\d+)\]",
            "label": "CHANGELOG top release heading",
        },
        "sites": [
            {"path": "manifest.json", "kind": "json", "pointer": "/version", "label": "manifest"},
            {
                "path": "pins.md",
                "kind": "regex",
                "pattern": r"(adr-judge@v)(\d+\.\d+\.\d+)",
                "label": "first pin",
            },
            {
                "path": "pins.md",
                "kind": "regex",
                "pattern": r"(rev: v)(\d+\.\d+\.\d+)",
                "label": "second pin",
            },
        ]
        + (extra_sites or []),
    }
    (root / "packaging" / "version-sites.json").write_text(
        json.dumps(registry, indent=2) + "\n", encoding="utf-8"
    )
    return registry


def test_two_sites_sharing_one_path_both_get_written(tmp_path):
    """Both README pins live in one file, so the second substitution must see the
    first one's edit. Planning against the on-disk bytes for every site would
    silently discard whichever edit was computed first.
    """
    root = _mini_repo(tmp_path)
    registry = _mini_registry(root)
    write_all(root, "0.2.0", registry)
    pins = (root / "pins.md").read_text(encoding="utf-8")
    assert "adr-judge@v0.2.0" in pins
    assert "rev: v0.2.0" in pins
    assert "0.1.0" not in pins


def test_unknown_kind_aborts_before_any_site_is_written(tmp_path):
    """Criteria #2 and #5: loud failure, and nothing on disk when it fires."""
    root = _mini_repo(tmp_path)
    registry = _mini_registry(
        root,
        extra_sites=[
            {"path": "manifest.json", "kind": "toml_table", "pointer": "/v", "label": "bogus"}
        ],
    )
    before = {p: p.read_bytes() for p in root.rglob("*") if p.is_file()}

    with pytest.raises(VersionSiteError) as excinfo:
        write_all(root, "0.2.0", registry)

    assert "toml_table" in str(excinfo.value)
    after = {p: p.read_bytes() for p in root.rglob("*") if p.is_file()}
    assert after == before, "an unimplemented site kind left files written"


def test_planning_reports_every_broken_site_in_one_pass(tmp_path):
    """ADR-013's 'report everything, abort never' applies to writing too."""
    root = _mini_repo(tmp_path)
    registry = _mini_registry(root)
    (root / "manifest.json").write_text('{"name": "x"}\n', encoding="utf-8")
    (root / "pins.md").write_text("no pins here\n", encoding="utf-8")

    with pytest.raises(VersionSiteError) as excinfo:
        plan_writes(root, "0.2.0", registry)

    message = str(excinfo.value)
    assert "/version" in message
    assert "first pin" in message
    assert "second pin" in message


def test_apply_transaction_rolls_back_when_a_write_fails(tmp_path, monkeypatch):
    """Criterion #5 at the engine level: a mid-run failure leaves nothing bumped."""
    import version_sites

    root = _mini_repo(tmp_path)
    registry = _mini_registry(root)
    before = {p: p.read_bytes() for p in root.rglob("*") if p.is_file()}

    real_write = version_sites._atomic_write_bytes
    calls = 0

    def fail_second(path, content):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError("injected release write failure")
        real_write(path, content)

    monkeypatch.setattr(version_sites, "_atomic_write_bytes", fail_second)

    with pytest.raises(VersionSiteError) as excinfo:
        write_all(root, "0.2.0", registry)

    assert "rolled back" in str(excinfo.value)
    after = {p: p.read_bytes() for p in root.rglob("*") if p.is_file()}
    assert after == before
    assert not list(root.glob(".*.tmp"))


def test_write_all_is_idempotent(tmp_path):
    root = _mini_repo(tmp_path)
    registry = _mini_registry(root)
    assert write_all(root, "0.2.0", registry)
    assert write_all(root, "0.2.0", registry) == []


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
