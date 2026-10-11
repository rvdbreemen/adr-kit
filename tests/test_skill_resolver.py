"""ADR-044: every skill resolves the plugin root from the installed skill.

The ten skills that run a bundled tool used to find the kit with
`ls -d ~/.claude/plugins/cache/rvdbreemen-adr-kit/adr-kit/*/ | sort -V | tail -1`.
That pipeline only finds a marketplace install in one client's cache, and GNU
`sort -V` is not portable (TASK-216, TASK-220). The skills now take the root in
ADR-044's order:

* `ADR_KIT_ROOT` first. OpenCode loads these same skills through its plugin
  (`opencode/plugin.ts`), does not substitute Claude Code's reference, and sets
  `ADR_KIT_ROOT` for its shell commands.
* Then `${CLAUDE_PLUGIN_ROOT}`, which Claude Code substitutes in a plugin
  skill's content with the root of the plugin the skill was loaded from.

When neither yields a root, every skill except the guardian, which falls back to
a local checkout, stops with one line.

ADR-044's Enforcement block forbids both old patterns in `skills/**/SKILL.md`;
this test states the same contract where a reader of the suite looks for it,
and it also pins what replaces the pipeline.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SKILLS = sorted((ROOT / "skills").glob("*/SKILL.md"))
CACHE_PATH = "~/.claude/plugins/cache/rvdbreemen-adr-kit"
RESOLVER = 'ADR_KIT="${ADR_KIT_ROOT:-${CLAUDE_PLUGIN_ROOT}}"'
EMPTY_ROOT_CHECK = (
    '[ -n "$ADR_KIT" ] || { echo "adr-kit: plugin root not found; set '
    'ADR_KIT_ROOT, or update or reinstall the plugin" >&2; exit 1; }'
)
GUARDIAN_ENTRY = "templates/cc-settings/guardian-hook-entry.json"


def _skill_id(path: Path) -> str:
    return path.parent.name


def _usable_bash() -> str | None:
    bash = shutil.which("bash")
    if bash is None:
        return None
    try:
        ok = subprocess.run([bash, "--version"], capture_output=True, timeout=5)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return bash if ok.returncode == 0 else None


BASH = _usable_bash()
needs_bash = pytest.mark.skipif(BASH is None, reason="bash not available")


def test_the_skill_tree_is_found():
    assert len(SKILLS) >= 10


@pytest.mark.parametrize("skill", SKILLS, ids=_skill_id)
def test_skill_names_no_client_cache_path_and_no_sort_v(skill: Path):
    text = skill.read_text(encoding="utf-8")
    assert CACHE_PATH not in text
    assert "sort -V" not in text


@pytest.mark.parametrize("skill", SKILLS, ids=_skill_id)
def test_skill_takes_the_plugin_root_from_the_installed_skill(skill: Path):
    assignments = [
        line.strip()
        for line in skill.read_text(encoding="utf-8").splitlines()
        if re.match(r"^\s*ADR_KIT=", line)
    ]
    # The guardian's documented fallback to a local checkout is the one other
    # assignment; it only runs when the resolved root is empty.
    plugin_root = [line for line in assignments if "git rev-parse" not in line]
    assert all(line == RESOLVER for line in plugin_root), plugin_root


@pytest.mark.parametrize("skill", SKILLS, ids=_skill_id)
def test_skill_stops_with_one_line_when_the_root_stays_empty(skill: Path):
    if skill.parent.name == "guardian":
        pytest.skip("the guardian falls back to a local checkout instead")
    lines = skill.read_text(encoding="utf-8").splitlines()
    for index, line in enumerate(lines):
        if line.strip() == RESOLVER:
            assert lines[index + 1].strip() == EMPTY_ROOT_CHECK, (
                f"{skill.parent.name}:{index + 2} lacks the empty-root check"
            )


def _resolver_snippet() -> str:
    """The real two lines from a skill, not a copy of them."""
    lines = (ROOT / "skills" / "lint" / "SKILL.md").read_text(encoding="utf-8").splitlines()
    index = next(i for i, line in enumerate(lines) if line.strip() == RESOLVER)
    return "\n".join(line.strip() for line in lines[index : index + 2])


def _claude_code_loads(snippet: str, plugin_root: str) -> str:
    """What Claude Code does to the skill text before the agent sees it."""
    return snippet.replace("${CLAUDE_PLUGIN_ROOT}", plugin_root)


def _run(script: str, **env_extra: str) -> subprocess.CompletedProcess:
    env = {
        key: value
        for key, value in os.environ.items()
        if key not in {"CLAUDE_PLUGIN_ROOT", "ADR_KIT_ROOT"}
    }
    env.update(env_extra)
    return subprocess.run(
        [BASH, "-s"],
        input=(script + '\necho "root=$ADR_KIT"\n').encode("utf-8"),
        capture_output=True,
        env=env,
        timeout=10,
    )


def _root_of(result: subprocess.CompletedProcess) -> str:
    assert result.returncode == 0, result.stderr.decode("utf-8", "replace")
    return result.stdout.decode("utf-8").strip()


@needs_bash
def test_claude_code_takes_the_substituted_plugin_root(tmp_path: Path):
    root = tmp_path.as_posix()
    result = _run(_claude_code_loads(_resolver_snippet(), root))
    assert _root_of(result) == f"root={root}"


@needs_bash
def test_opencode_takes_the_adr_kit_root_its_shell_env_sets(tmp_path: Path):
    # OpenCode passes the text unchanged and sets ADR_KIT_ROOT (plugin.ts shell.env).
    root = tmp_path.as_posix()
    result = _run(_resolver_snippet(), ADR_KIT_ROOT=root)
    assert _root_of(result) == f"root={root}"


@needs_bash
def test_an_explicit_adr_kit_root_wins_over_the_substituted_root(tmp_path: Path):
    override = (tmp_path / "override").as_posix()
    script = _claude_code_loads(_resolver_snippet(), (tmp_path / "plugin").as_posix())
    assert _root_of(_run(script, ADR_KIT_ROOT=override)) == f"root={override}"


@needs_bash
def test_without_any_root_the_skill_stops_with_the_message():
    result = _run(_resolver_snippet())
    assert result.returncode == 1
    assert "plugin root not found" in result.stderr.decode("utf-8", "replace")
    assert b"root=" not in result.stdout


def test_install_hooks_appends_the_shipped_guardian_entry():
    text = (ROOT / "skills" / "install-hooks" / "SKILL.md").read_text(encoding="utf-8")
    assert GUARDIAN_ENTRY in text
    assert '"command": "' not in text, "an inline copy of the guardian entry is back"
    assert (ROOT / GUARDIAN_ENTRY).is_file()
