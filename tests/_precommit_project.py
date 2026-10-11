"""A scratch project that runs the real pre-commit template (test helper).

Shared by the pre-commit tests that need a whole commit, not a block cut from
the template: a git repository with ADR-043 and the hook installed, a fake HOME,
and a staged change that violates ADR-043. Where the engine lives is up to each
test, because that is what several of them are about.
"""

from __future__ import annotations

import os
import pathlib
import shutil
import subprocess

ROOT = pathlib.Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "templates" / "githooks" / "pre-commit"
ADR_043 = next((ROOT / "docs" / "adr").glob("ADR-043-*.md"))


def tools_present(*tools: str) -> bool:
    return os.name != "nt" and all(shutil.which(tool) for tool in tools)


def git(cwd: pathlib.Path, *args: str, env: dict) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args], cwd=cwd, env=env, capture_output=True, text=True, timeout=120,
    )


def project(tmp_path: pathlib.Path) -> tuple[pathlib.Path, pathlib.Path, dict]:
    """(repo, home, env) with no engine anywhere yet."""
    home = tmp_path / "home"
    home.mkdir()
    env = {
        **{key: value for key, value in os.environ.items()
           if not key.startswith("GIT_")
           and key not in {"ADR_KIT_ROOT", "XDG_DATA_HOME", "XDG_CACHE_HOME",
                           "CODEX_HOME", "COPILOT_HOME"}},
        "HOME": str(home),
        "ADR_KIT_NO_LLM": "1",
        "ADR_KIT_SUGGEST_DISABLE": "1",
        "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@example.invalid",
        "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@example.invalid",
    }
    repo = tmp_path / "repo"
    (repo / "docs" / "adr").mkdir(parents=True)
    shutil.copy2(ADR_043, repo / "docs" / "adr" / ADR_043.name)
    hooks = repo / ".githooks"
    hooks.mkdir()
    shutil.copy2(TEMPLATE, hooks / "pre-commit")
    (hooks / "pre-commit").chmod(0o755)
    git(repo, "init", "-q", env=env)
    git(repo, "config", "core.hooksPath", ".githooks", env=env)
    git(repo, "add", "-A", env=env)
    seeded = git(repo, "commit", "-q", "--no-verify", "-m", "seed", env=env)
    assert seeded.returncode == 0, seeded.stderr
    return repo, home, env


def link_engine(path: pathlib.Path, target: pathlib.Path = ROOT) -> None:
    """Make `path` an engine root by pointing it at an ADR Kit tree."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.symlink_to(target, target_is_directory=True)


def stage_violation(repo: pathlib.Path, env: dict) -> None:
    target = repo / "bin" / "adr_llm.py"
    target.parent.mkdir(exist_ok=True)
    target.write_text('DEFAULT_LLM_CMD = ["claude", "-p"]\n', encoding="utf-8")
    git(repo, "add", "bin/adr_llm.py", env=env)
