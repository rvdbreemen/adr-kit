"""Tests for the release bump, driven through `bin/bump-version`.

`bin/bump-version` is a thin delegation to `scripts/bump-version.py`, the
canonical writer named by ADR-013 and docs/RELEASING.md. It is still the entry
point under test here because it is the one people have in their shell history,
and running it proves the delegation as well as the writer.

Until v0.47.0 the two were separate implementations of the same release step,
and they disagreed: only the unnamed one could write the CHANGELOG compare-link
block, so the runbook ran the weaker tool and the block went stale on every
release (TASK-139). Where the two contracts differed, the delegation takes the
canonical writer's -- exit 2 for a usage error, a leading `v` accepted and
stripped, and a TODO placeholder release section rather than promotion of the
Unreleased body. Each of those is asserted below.

Background: bump-version was a bash script that shelled out to python3 per
file edit. On Windows the `python3` Store alias routes through the Python
Install Manager, which scans argv for a script file and dispatches on ITS
shebang; passing the bash-shebanged pre-commit template as an argument made
the launcher exec bash instead of python (observed as cygheap fork crashes
during releases v0.27.0 through v0.29.0). The rewrite is pure stdlib Python:
no child processes at all, so there is nothing for a launcher to misroute.

The script resolves all paths relative to its own location, so the tests
copy it into a temp fixture tree and run the copy: the real repo is never
mutated.
"""
from __future__ import annotations

import json
import importlib.util
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
BUMP_VERSION = REPO_ROOT / "bin" / "bump-version"

PLUGIN = {"name": "adr-kit", "version": "0.30.0", "description": "x"}
CODEX_PLUGIN = {"name": "adr-kit", "version": "0.30.0", "description": "x"}
COPILOT_PLUGIN = {"name": "adr-kit", "version": "0.30.0", "description": "x"}
OPENCODE_PACKAGE = {
    "name": "@rvdbreemen/adr-kit-opencode",
    "version": "0.30.0",
    "description": "x",
}
MARKETPLACE = {"plugins": [{"name": "adr-kit", "version": "0.30.0"}]}
CHANGELOG = (
    "# Changelog\n\n## [Unreleased]\n\n### Added\n\n- thing.\n\n"
    "## [0.30.0] - 2026-06-12\n"
)
PRECOMMIT = (
    "#!/usr/bin/env bash\n"
    "# adr-kit pre-commit hook\n"
    'ADR_KIT_WRAPPER_VERSION="0.30.0"\n'
    "exit 0\n"
)
GUARDIAN_ENTRY = {
    "_remove_marker": "adr-guardian-session-start",
    "_wrapper_version": "0.30.0",
    "type": "command",
    "command": "adr-guardian check",
}
# Both README pins, the two sites the hard-coded path tuple used to miss
# (TASK-71). They are the snippets users paste into their own workflow and
# pre-commit config, so a stale pin ships a wrong version to every consumer.
README = (
    "# adr-kit\n"
    "\n"
    "```yaml\n"
    "      - uses: rvdbreemen/adr-kit/.github/actions/adr-judge@v0.30.0\n"
    "```\n"
    "\n"
    "```yaml\n"
    "  - repo: https://github.com/rvdbreemen/adr-kit\n"
    "    rev: v0.30.0\n"
    "```\n"
    "\n"
    "Introduced in v0.12.0 -- a history marker, deliberately not a version site.\n"
)


def _make_tree(tmp_path: Path) -> Path:
    """A miniature repo carrying every site the REAL registry declares.

    The fixture copies the real `packaging/version-sites.json` and the real
    engine rather than a minimal stand-in: the whole point of TASK-71 is that a
    declared site must be written, so the test has to exercise the actual site
    list. A site added to the registry without a file here fails loudly in
    `test_fixture_covers_every_declared_site` instead of quietly going unwritten.
    """
    root = tmp_path / "repo"
    (root / "bin").mkdir(parents=True)
    (root / "scripts").mkdir()
    (root / "packaging").mkdir()
    (root / ".claude-plugin").mkdir()
    (root / "codex" / ".codex-plugin").mkdir(parents=True)
    (root / "copilot").mkdir()
    (root / ".github" / "plugin").mkdir(parents=True)
    (root / "templates" / "githooks").mkdir(parents=True)
    (root / "templates" / "cc-settings").mkdir(parents=True)
    (root / ".githooks").mkdir()
    shutil.copy(str(BUMP_VERSION), str(root / "bin" / "bump-version"))
    shutil.copy(
        str(REPO_ROOT / "scripts" / "version_sites.py"),
        str(root / "scripts" / "version_sites.py"),
    )
    shutil.copy(
        str(REPO_ROOT / "scripts" / "bump-version.py"),
        str(root / "scripts" / "bump-version.py"),
    )
    shutil.copy(
        str(REPO_ROOT / "packaging" / "version-sites.json"),
        str(root / "packaging" / "version-sites.json"),
    )
    (root / "README.md").write_text(README, encoding="utf-8")
    (root / "package.json").write_text(
        json.dumps(OPENCODE_PACKAGE, indent=2) + "\n", encoding="utf-8"
    )
    (root / ".claude-plugin" / "plugin.json").write_text(
        json.dumps(PLUGIN, indent=2) + "\n", encoding="utf-8"
    )
    (root / "codex" / ".codex-plugin" / "plugin.json").write_text(
        json.dumps(CODEX_PLUGIN, indent=2) + "\n", encoding="utf-8"
    )
    (root / "copilot" / "plugin.json").write_text(
        json.dumps(COPILOT_PLUGIN, indent=2) + "\n", encoding="utf-8"
    )
    (root / ".github" / "plugin" / "marketplace.json").write_text(
        json.dumps(MARKETPLACE, indent=2) + "\n", encoding="utf-8"
    )
    (root / ".claude-plugin" / "marketplace.json").write_text(
        json.dumps(MARKETPLACE, indent=2) + "\n", encoding="utf-8"
    )
    (root / "CHANGELOG.md").write_text(CHANGELOG, encoding="utf-8")
    (root / "templates" / "githooks" / "pre-commit").write_text(
        PRECOMMIT, encoding="utf-8"
    )
    (root / ".githooks" / "pre-commit").write_text(PRECOMMIT, encoding="utf-8")
    (root / "templates" / "cc-settings" / "guardian-hook-entry.json").write_text(
        json.dumps(GUARDIAN_ENTRY, indent=2) + "\n", encoding="utf-8"
    )
    (root / "templates" / "adr-kit-guide.md").write_text(
        "<!-- adr-kit-guide v0.30.0 -->\n# Guide\n", encoding="utf-8"
    )
    return root


def _snapshot(root: Path) -> dict:
    """Every source byte under `root`, ignoring the interpreter's own bytecode cache."""
    return {
        path: path.read_bytes()
        for path in root.rglob("*")
        if path.is_file() and "__pycache__" not in path.parts
    }


def _run(root: Path, *args: str) -> "subprocess.CompletedProcess":
    return subprocess.run(
        [sys.executable, str(root / "bin" / "bump-version")] + list(args),
        capture_output=True,
        text=True,
        encoding="utf-8",
        cwd=str(root),
    )


def test_bump_updates_both_client_manifests_and_release_artifacts(tmp_path):
    root = _make_tree(tmp_path)
    proc = _run(root, "0.31.0")
    assert proc.returncode == 0, proc.stderr
    plugin = json.loads((root / ".claude-plugin" / "plugin.json").read_text())
    assert plugin["version"] == "0.31.0"
    codex_plugin = json.loads(
        (root / "codex" / ".codex-plugin" / "plugin.json").read_text()
    )
    assert codex_plugin["version"] == "0.31.0"
    copilot_plugin = json.loads((root / "copilot" / "plugin.json").read_text())
    assert copilot_plugin["version"] == "0.31.0"
    opencode_package = json.loads((root / "package.json").read_text())
    assert opencode_package["version"] == "0.31.0"
    copilot_marketplace = json.loads(
        (root / ".github" / "plugin" / "marketplace.json").read_text()
    )
    assert copilot_marketplace["plugins"][0]["version"] == "0.31.0"
    marketplace = json.loads(
        (root / ".claude-plugin" / "marketplace.json").read_text()
    )
    assert marketplace["plugins"][0]["version"] == "0.31.0"
    changelog = (root / "CHANGELOG.md").read_text(encoding="utf-8")
    # The canonical writer inserts a placeholder release section under the
    # marker and leaves the existing Unreleased body in place; the runbook then
    # has the author write the real notes into it. `bin/bump-version` used to
    # promote the Unreleased body into the release instead. The delegation
    # adopts the canonical writer's behaviour, which is what has been shipping.
    assert "## [Unreleased]" in changelog
    assert "## [0.31.0] - " in changelog
    assert changelog.index("## [Unreleased]") < changelog.index("## [0.31.0] - ")
    assert "## [0.30.0] - 2026-06-12" in changelog
    assert (
        "[Unreleased]: "
        "https://github.com/rvdbreemen/adr-kit/compare/v0.31.0...HEAD"
    ) in changelog
    assert (
        "[0.31.0]: "
        "https://github.com/rvdbreemen/adr-kit/compare/v0.30.0...v0.31.0"
    ) in changelog
    precommit = (root / "templates" / "githooks" / "pre-commit").read_text()
    assert 'ADR_KIT_WRAPPER_VERSION="0.31.0"' in precommit
    entry = json.loads(
        (root / "templates" / "cc-settings" / "guardian-hook-entry.json").read_text()
    )
    assert entry["_wrapper_version"] == "0.31.0"
    guide = (root / "templates" / "adr-kit-guide.md").read_text(encoding="utf-8")
    assert guide.splitlines()[0] == "<!-- adr-kit-guide v0.31.0 -->"


def test_fixture_covers_every_declared_site(tmp_path):
    """The fixture must carry a file for every site the real registry declares.

    Without this, adding a registry entry and forgetting the fixture file would
    make the bump abort inside every other test with a confusing error, or worse,
    quietly stop covering the new site.
    """
    root = _make_tree(tmp_path)
    registry = json.loads(
        (root / "packaging" / "version-sites.json").read_text(encoding="utf-8")
    )
    missing = sorted(
        {
            site["path"]
            for site in registry["sites"]
            if not (root / site["path"]).is_file()
        }
    )
    assert not missing, f"fixture is missing declared version sites: {missing}"


def test_bump_writes_every_registry_site_including_the_readme_pins(tmp_path):
    """TASK-71: declared sites were verified but never written.

    `bin/bump-version` carried its own hard-coded path tuple that omitted both
    README pins, so a release left the copy-paste snippets pointing at the
    previous version. The writer now reads the registry, so every declared site
    moves -- proven here against the real site list, not a stand-in.
    """
    root = _make_tree(tmp_path)
    proc = _run(root, "0.31.0")
    assert proc.returncode == 0, proc.stderr

    readme = (root / "README.md").read_text(encoding="utf-8")
    assert "adr-judge@v0.31.0" in readme
    assert "rev: v0.31.0" in readme
    assert "0.30.0" not in readme
    # The history marker records when a feature landed and must never move.
    assert "Introduced in v0.12.0" in readme

    # This repo dogfoods its own pre-commit wrapper; its stamp is a declared
    # site too, so the guardian's staleness check cannot go stale itself.
    own_wrapper = (root / ".githooks" / "pre-commit").read_text(encoding="utf-8")
    assert 'ADR_KIT_WRAPPER_VERSION="0.31.0"' in own_wrapper

    # Checked through the engine rather than by scanning for the old string.
    # CHANGELOG.md is a declared site now (the `[Unreleased]` compare link), and
    # the old version legitimately survives in it -- in the previous release
    # heading, and inside the new `v0.30.0...v0.31.0` compare link, which is the
    # whole point of a compare link. A substring scan calls both of those stale.
    sys.path.insert(0, str(REPO_ROOT / "scripts"))
    from version_sites import read_all  # noqa: E402

    stale = [
        site["path"]
        for site, values in read_all(root)
        if any(value != "0.31.0" for value in values)
    ]
    assert not stale, f"declared sites left at the old version: {stale}"

    changelog = (root / "CHANGELOG.md").read_text(encoding="utf-8")
    assert "## [0.30.0] - 2026-06-12" in changelog, "release history was rewritten"
    assert "v0.30.0...v0.31.0" in changelog, "the compare link lost its base"


def test_a_site_added_to_the_registry_is_bumped_without_touching_the_writer(tmp_path):
    """Criterion #3: declaring a site is sufficient; no code change needed.

    This is the test that stops the next added site inheriting the old trap.
    """
    root = _make_tree(tmp_path)
    registry_path = root / "packaging" / "version-sites.json"
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    (root / "docs").mkdir()
    (root / "docs" / "install.md").write_text(
        "Install adr-kit:\n\n    pip install adr-kit==0.30.0\n", encoding="utf-8"
    )
    registry["sites"].append(
        {
            "path": "docs/install.md",
            "kind": "regex",
            "pattern": "(pip install adr-kit==)(\\d+\\.\\d+\\.\\d+)",
            "label": "temporary install-doc pin",
        }
    )
    registry_path.write_text(json.dumps(registry, indent=2) + "\n", encoding="utf-8")

    proc = _run(root, "0.31.0")
    assert proc.returncode == 0, proc.stderr
    assert "pip install adr-kit==0.31.0" in (
        root / "docs" / "install.md"
    ).read_text(encoding="utf-8")
    assert "docs/install.md" in proc.stdout


def test_unknown_site_kind_fails_loudly_and_writes_nothing(tmp_path):
    """Criteria #2 and #5 together: a kind the writer cannot handle aborts the bump.

    Silent skipping is exactly how the README pins drifted, so an undeclarable
    site must fail -- and must fail during planning, before any sibling site has
    been written, or the tree ends up carrying two versions at once.
    """
    root = _make_tree(tmp_path)
    registry_path = root / "packaging" / "version-sites.json"
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    registry["sites"].append(
        {
            "path": "README.md",
            "kind": "yaml_pointer",
            "pointer": "/version",
            "label": "site kind nothing implements",
        }
    )
    registry_path.write_text(json.dumps(registry, indent=2) + "\n", encoding="utf-8")

    before = _snapshot(root)
    proc = _run(root, "0.31.0")
    assert proc.returncode == 1
    assert "yaml_pointer" in proc.stderr
    assert _snapshot(root) == before, "an unimplemented site kind left files written"


def _add_bogus_kind(root: Path) -> None:
    registry_path = root / "packaging" / "version-sites.json"
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    registry["sites"].append(
        {
            "path": "README.md",
            "kind": "bogus_kind",
            "pointer": "/v",
            "label": "site kind nothing implements",
        }
    )
    registry_path.write_text(json.dumps(registry, indent=2) + "\n", encoding="utf-8")


def test_sanctioned_writer_does_not_orphan_the_changelog_heading(tmp_path):
    """Criterion #5 for scripts/bump-version.py, the writer ADR-013 names.

    It used to write the CHANGELOG heading first and the declared sites second,
    outside any transaction. A failure in between left the repository announcing
    a release that no manifest carried -- and the CHANGELOG heading is precisely
    what every other tool reads as canonical, so the tree then disagreed with
    itself in the one place that decides. The heading now joins the same
    transaction as the sites.
    """
    root = _make_tree(tmp_path)
    _add_bogus_kind(root)
    before = _snapshot(root)

    proc = subprocess.run(
        [sys.executable, str(root / "scripts" / "bump-version.py"), "0.31.0"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        cwd=str(root),
    )

    assert proc.returncode == 1
    assert "bogus_kind" in proc.stdout + proc.stderr
    changelog = (root / "CHANGELOG.md").read_text(encoding="utf-8")
    assert "0.31.0" not in changelog, "CHANGELOG announced a release no site carries"
    assert _snapshot(root) == before, "a failed bump left files written"


def test_invalid_semver_rejected(tmp_path):
    """Exit 2, from the canonical writer's argparse.

    `bin/bump-version` hand-rolled this and exited 1. It now delegates, so the
    usage contract is argparse's -- exit 2, which is what every other adr-kit
    CLI already returns for a usage error.
    """
    root = _make_tree(tmp_path)
    for bad in ("0.31", "0.31.0-rc1", "banana", "0.31.0.1", ""):
        proc = _run(root, bad)
        assert proc.returncode == 2, bad
        assert "MAJOR.MINOR.PATCH" in proc.stderr


def test_a_leading_v_is_accepted_and_normalised(tmp_path):
    """`v0.31.0` is the tag spelling, and the canonical writer strips it.

    `bin/bump-version` rejected it; `scripts/bump-version.py` documents the
    strip and `scripts/check-release-version.py` does the same, so the
    delegation takes the behaviour that already matches the rest of the release
    path rather than the stricter one that did not.
    """
    root = _make_tree(tmp_path)
    proc = _run(root, "v0.31.0")

    assert proc.returncode == 0, proc.stderr
    plugin = json.loads((root / ".claude-plugin" / "plugin.json").read_text())
    assert plugin["version"] == "0.31.0", "the leading v leaked into a manifest"


def test_usage_error_without_argument(tmp_path):
    root = _make_tree(tmp_path)
    proc = _run(root)
    assert proc.returncode == 2
    assert "usage" in proc.stderr.lower()


def test_missing_marketplace_entry_fails(tmp_path):
    root = _make_tree(tmp_path)
    (root / ".claude-plugin" / "marketplace.json").write_text(
        json.dumps({"plugins": [{"name": "other", "version": "1.0.0"}]}),
        encoding="utf-8",
    )
    proc = _run(root, "0.31.0")
    assert proc.returncode == 1
    assert "marketplace" in proc.stderr


def test_missing_unreleased_fails_preflight_without_mutation(tmp_path):
    root = _make_tree(tmp_path)
    (root / "CHANGELOG.md").write_text(
        "# Changelog\n\n## [0.30.0] - 2026-06-12\n", encoding="utf-8"
    )
    before = {
        path: path.read_bytes()
        for path in root.rglob("*")
        if path.is_file()
    }
    proc = _run(root, "0.31.0")
    assert proc.returncode == 1
    assert "Unreleased" in proc.stderr
    plugin = json.loads((root / ".claude-plugin" / "plugin.json").read_text())
    assert plugin["version"] == "0.30.0"
    assert {path: path.read_bytes() for path in before} == before


def test_missing_stamps_fail_preflight_without_mutation(tmp_path):
    root = _make_tree(tmp_path)
    (root / "templates" / "githooks" / "pre-commit").write_text(
        "#!/usr/bin/env bash\nexit 0\n", encoding="utf-8"
    )
    (root / "templates" / "cc-settings" / "guardian-hook-entry.json").write_text(
        "{not json", encoding="utf-8"
    )
    before = (root / ".claude-plugin" / "plugin.json").read_bytes()
    proc = _run(root, "0.31.0")
    assert proc.returncode == 1
    assert "stamp" in proc.stderr or "_wrapper_version" in proc.stderr
    plugin = json.loads((root / ".claude-plugin" / "plugin.json").read_text())
    assert plugin["version"] == "0.30.0"
    assert (root / ".claude-plugin" / "plugin.json").read_bytes() == before


def _load_engine(root: Path):
    """Load the fixture copy of scripts/version_sites.py, the shared write engine."""
    import importlib.machinery

    source = root / "scripts" / "version_sites.py"
    name = "version_sites_fixture"
    loader = importlib.machinery.SourceFileLoader(name, str(source))
    spec = importlib.util.spec_from_loader(name, loader)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    # Register before exec: @dataclass resolves annotations through
    # sys.modules[cls.__module__], which is None for an unregistered module.
    sys.modules[name] = module
    loader.exec_module(module)
    return module


def test_injected_write_failure_rolls_back_every_target(tmp_path, monkeypatch):
    """A failure part way through a bump must leave no file half-written.

    The transaction moved into scripts/version_sites.py with TASK-71, so both
    bump entry points now share it -- the registry-driven writer named by
    ADR-013 previously had no rollback at all.
    """
    root = _make_tree(tmp_path)
    module = _load_engine(root)
    first = root / "first.txt"
    second = root / "second.txt"
    first.write_text("first-original", encoding="utf-8")
    second.write_text("second-original", encoding="utf-8")
    real_write = module._atomic_write_bytes
    calls = 0

    def fail_second(path, content):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError("injected release write failure")
        real_write(path, content)

    monkeypatch.setattr(module, "_atomic_write_bytes", fail_second)

    with pytest.raises(module.VersionSiteError):
        module.apply_transaction({first: b"first-new", second: b"second-new"})

    assert first.read_text(encoding="utf-8") == "first-original"
    assert second.read_text(encoding="utf-8") == "second-original"
    assert not list(root.glob(".*.tmp"))


def test_staging_hint_names_every_changed_target(tmp_path):
    root = _make_tree(tmp_path)
    proc = _run(root, "0.31.0")
    assert proc.returncode == 0, proc.stderr
    hint = proc.stdout.split("git add", 1)[1].splitlines()[0]
    for expected in (
        ".claude-plugin/plugin.json",
        ".claude-plugin/marketplace.json",
        "codex/.codex-plugin/plugin.json",
        "copilot/plugin.json",
        ".github/plugin/marketplace.json",
        "package.json",
        "CHANGELOG.md",
        "templates/githooks/pre-commit",
        "templates/cc-settings/guardian-hook-entry.json",
        "templates/adr-kit-guide.md",
        ".githooks/pre-commit",
    ):
        assert expected in hint


def test_no_child_processes_in_source():
    """The launcher-misrouting bug class is structurally excluded: the script
    must not spawn any child process."""
    source = BUMP_VERSION.read_text(encoding="utf-8")
    assert "subprocess" not in source
    assert "os.system" not in source


def test_real_script_is_python():
    first_line = BUMP_VERSION.read_text(encoding="utf-8").splitlines()[0]
    assert "python" in first_line
