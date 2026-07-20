import importlib.util
import os
import stat
import subprocess
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


setup = _load("project_setup_for_test", SCRIPTS / "project_setup.py")
settings = _load("adr_settings_for_setup_test", SCRIPTS / "adr_settings.py")


def _git(root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(root), *args],
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    return result.stdout.strip()


def _repo(tmp_path: Path) -> Path:
    _git(tmp_path, "init", "-q")
    return tmp_path


def _collect(root: Path, enabled: bool = True):
    return setup.collect_changes(
        root,
        ROOT,
        ["claude", "codex", "copilot"],
        pre_commit_enabled=enabled,
    )


def test_setup_writes_guide_three_independent_markers_and_pre_commit(tmp_path):
    root = _repo(tmp_path)
    (root / "AGENTS.md").write_text("user agents\n", encoding="utf-8")
    (root / "CLAUDE.md").write_text("user claude\n", encoding="utf-8")
    local = root / ".adr-kit" / "ADR-guide.local.md"
    local.parent.mkdir()
    local.write_text("project-specific\n", encoding="utf-8")

    changes, configure = _collect(root)
    setup.apply_changes(root, changes, configure_hooks_path=configure)

    assert (root / ".adr-kit" / "ADR-guide.md").read_bytes() == (
        ROOT / "instructions" / "ADR-guide.md"
    ).read_bytes()
    assert local.read_text(encoding="utf-8") == "project-specific\n"
    assert "ADR-KIT CODEX START" in (root / "AGENTS.md").read_text(
        encoding="utf-8"
    )
    assert "user agents" in (root / "AGENTS.md").read_text(encoding="utf-8")
    assert "ADR-KIT CLAUDE START" in (root / "CLAUDE.md").read_text(
        encoding="utf-8"
    )
    assert "user claude" in (root / "CLAUDE.md").read_text(encoding="utf-8")
    assert "ADR-KIT COPILOT START" in (
        root / ".github" / "copilot-instructions.md"
    ).read_text(encoding="utf-8")
    assert not (root / "AGENT.md").exists()
    assert (root / ".githooks" / "pre-commit").exists()
    assert _git(root, "config", "--get", "core.hooksPath") == ".githooks"

    second, configure_second = _collect(root)
    assert second == []
    assert configure_second is False


def test_replacing_generated_guide_creates_content_addressed_backup(tmp_path):
    root = _repo(tmp_path)
    guide = root / ".adr-kit" / "ADR-guide.md"
    guide.parent.mkdir()
    guide.write_text("old generated guide\n", encoding="utf-8")

    changes, configure = _collect(root)
    setup.apply_changes(root, changes, configure_hooks_path=configure)

    backups = list((root / ".adr-kit" / "backups").glob("*.generated.bak"))
    assert len(backups) == 1
    assert backups[0].read_text(encoding="utf-8") == "old generated guide\n"


@pytest.mark.parametrize(
    "body",
    [
        "<!-- ADR-KIT CODEX START -->\n",
        "<!-- ADR-KIT CODEX END -->\n<!-- ADR-KIT CODEX START -->\n",
        (
            "<!-- ADR-KIT CODEX START -->\n"
            "<!-- ADR-KIT CODEX START -->\n"
            "<!-- ADR-KIT CODEX END -->\n"
        ),
        (
            "<!-- ADR-KIT CODEX START -->\n"
            "<!-- ADR-KIT OTHER START -->\n"
            "<!-- ADR-KIT OTHER END -->\n"
            "<!-- ADR-KIT CODEX END -->\n"
        ),
    ],
)
def test_malformed_duplicate_reversed_or_nested_markers_refuse_all_writes(
    tmp_path, body
):
    root = _repo(tmp_path)
    agents = root / "AGENTS.md"
    agents.write_text(body, encoding="utf-8")
    before = agents.read_bytes()

    with pytest.raises(setup.SetupError):
        _collect(root)

    assert agents.read_bytes() == before
    assert not (root / ".adr-kit" / "ADR-guide.md").exists()


def test_bom_crlf_unicode_and_permissions_are_preserved(tmp_path):
    root = _repo(tmp_path)
    agents = root / "AGENTS.md"
    payload = b"\xef\xbb\xbfUser \xe2\x98\x83\r\n"
    agents.write_bytes(payload)
    os.chmod(agents, 0o640)
    original_mode = stat.S_IMODE(agents.stat().st_mode)

    changes, configure = _collect(root)
    setup.apply_changes(root, changes, configure_hooks_path=configure)

    updated = agents.read_bytes()
    assert updated.startswith(b"\xef\xbb\xbf")
    assert b"User \xe2\x98\x83\r\n" in updated
    assert b"\r\n<!-- ADR-KIT CODEX START -->\r\n" in updated
    assert stat.S_IMODE(agents.stat().st_mode) == original_mode


def test_existing_lock_refuses_concurrent_setup_before_changes(tmp_path):
    root = _repo(tmp_path)
    lock = root / ".adr-kit" / "setup.lock"
    lock.parent.mkdir()
    lock.write_text("busy", encoding="utf-8")
    changes, configure = _collect(root)

    with pytest.raises(setup.SetupError):
        setup.apply_changes(root, changes, configure_hooks_path=configure)

    assert not (root / ".adr-kit" / "ADR-guide.md").exists()


def test_legacy_stub_and_guides_migrate_once_with_backups(tmp_path):
    root = _repo(tmp_path)
    (root / "CLAUDE.md").write_text(
        "before\n"
        "<!-- ADR-KIT STUB START -->\nlegacy\n"
        "<!-- ADR-KIT STUB END -->\n"
        "after\n",
        encoding="utf-8",
    )
    for relative in (
        Path(".claude/adr-kit-guide.md"),
        Path(".agents/adr-kit-guide.md"),
    ):
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"legacy {relative}\n", encoding="utf-8")

    changes, configure = _collect(root)
    assert any(change.action == "migrate-marker" for change in changes)
    setup.apply_changes(root, changes, configure_hooks_path=configure)

    claude = (root / "CLAUDE.md").read_text(encoding="utf-8")
    assert "before" in claude and "after" in claude
    assert "ADR-KIT STUB" not in claude
    assert "ADR-KIT CLAUDE START" in claude
    assert not (root / ".claude" / "adr-kit-guide.md").exists()
    assert not (root / ".agents" / "adr-kit-guide.md").exists()
    assert len(list((root / ".adr-kit" / "backups").glob("*.legacy.bak"))) == 2
    second, configure_second = _collect(root)
    assert second == []
    assert configure_second is False


def test_dry_run_cli_produces_diff_without_writes(tmp_path):
    root = _repo(tmp_path)
    command = [
        sys.executable,
        str(SCRIPTS / "setup-project.py"),
        "--project-root",
        str(root),
        "--plugin-root",
        str(ROOT),
        "--dry-run",
    ]

    result = subprocess.run(command, text=True, capture_output=True, check=False)

    assert result.returncode == 0, result.stderr
    assert "--- a/AGENTS.md" in result.stdout
    assert "ADR-KIT CODEX START" in result.stdout
    assert not (root / "AGENTS.md").exists()
    assert not (root / ".adr-kit").exists()


def test_pre_commit_can_be_disabled_and_reenabled_without_user_hook_clobber(
    tmp_path,
):
    root = _repo(tmp_path)
    changes, configure = _collect(root, enabled=False)
    setup.apply_changes(root, changes, configure_hooks_path=configure)
    assert not (root / ".githooks" / "pre-commit").exists()

    changes, configure = _collect(root, enabled=True)
    setup.apply_changes(root, changes, configure_hooks_path=configure)
    assert (root / ".githooks" / "pre-commit").exists()

    changes, configure = _collect(root, enabled=False)
    setup.apply_changes(root, changes, configure_hooks_path=configure)
    assert not (root / ".githooks" / "pre-commit").exists()

    user_hook = root / ".githooks" / "pre-commit"
    user_hook.write_text("# user hook\n", encoding="utf-8")
    with pytest.raises(setup.SetupError):
        _collect(root, enabled=True)
    assert user_hook.read_text(encoding="utf-8") == "# user hook\n"


def test_setup_cli_honors_project_pre_commit_setting(tmp_path):
    root = _repo(tmp_path)
    global_path = tmp_path / "global-settings.json"
    settings.write_setting(
        root,
        "project",
        "pre_commit.enabled",
        False,
        global_path=global_path,
    )
    command = [
        sys.executable,
        str(SCRIPTS / "setup-project.py"),
        "--project-root",
        str(root),
        "--plugin-root",
        str(ROOT),
        "--global-settings",
        str(global_path),
    ]

    disabled = subprocess.run(
        command, text=True, capture_output=True, check=False
    )
    assert disabled.returncode == 0, disabled.stderr
    assert not (root / ".githooks" / "pre-commit").exists()

    settings.write_setting(
        root,
        "project",
        "pre_commit.enabled",
        True,
        global_path=global_path,
    )
    enabled = subprocess.run(
        command, text=True, capture_output=True, check=False
    )
    assert enabled.returncode == 0, enabled.stderr
    assert (root / ".githooks" / "pre-commit").exists()


def test_custom_hooks_path_is_never_replaced(tmp_path):
    root = _repo(tmp_path)
    _git(root, "config", "core.hooksPath", "custom-hooks")

    with pytest.raises(setup.SetupError) as error:
        _collect(root, enabled=True)

    assert "custom core.hooksPath" in str(error.value)


def test_uninstall_removes_only_generated_guide_and_selected_managed_blocks(tmp_path):
    root = tmp_path / "project"
    (root / ".adr-kit").mkdir(parents=True)
    (root / ".adr-kit" / "ADR-guide.md").write_text("generated\n", encoding="utf-8")
    (root / ".adr-kit" / "ADR-guide.local.md").write_text("keep local\n", encoding="utf-8")
    (root / "AGENTS.md").write_text(
        "user before\n\n" + setup.marker_block("codex") + "\n\nuser after\n",
        encoding="utf-8",
    )
    (root / "CLAUDE.md").write_text(
        setup.marker_block("claude") + "\n", encoding="utf-8"
    )
    changes = setup.plan_uninstall(root, ["codex"])
    setup.apply_changes(root, changes, configure_hooks_path=False)
    assert not (root / ".adr-kit" / "ADR-guide.md").exists()
    assert (root / ".adr-kit" / "ADR-guide.local.md").read_text() == "keep local\n"
    assert (root / "AGENTS.md").read_text() == "user before\n\n\n\nuser after\n"
    assert "ADR-KIT CLAUDE" in (root / "CLAUDE.md").read_text()
