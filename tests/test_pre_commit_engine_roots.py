"""The commit floor finds the engine wherever a client installed it (DEF-29, DEF-30).

The hook looked in the Claude and Codex plugin caches, in Copilot's
`installed-plugins`, and in an ADR Kit checkout. Two installs fell outside:

* Copilot CLI 1.0.81 and later loads a directory marketplace live from the
  payload the installer prepared and no longer copies it to `installed-plugins`.
* OpenCode installs the kit as the `@rvdbreemen/adr-kit-opencode` npm package.

With no engine found the hook exits 0, so a violating commit landed. ADR-044's
candidate set also starts with an explicit `ADR_KIT_ROOT`. Every candidate still
competes on manifest version (ADR-008). Each test below gives the hook exactly
one engine and expects the violating commit to be refused.
"""

from __future__ import annotations

import pytest

from _precommit_project import ROOT, git, link_engine, project, stage_violation, tools_present

needs_tools = pytest.mark.skipif(
    not tools_present("bash", "git"), reason="needs bash and git",
)


def _refused(repo, env):
    stage_violation(repo, env)
    result = git(repo, "commit", "-m", "violates ADR-043", env=env)
    assert "adr-judge binary not found" not in result.stderr, result.stderr
    assert result.returncode != 0, f"the violating commit landed: {result.stderr!r}"
    return result


@needs_tools
def test_an_explicit_adr_kit_root_is_a_candidate(tmp_path):
    repo, _home, env = project(tmp_path)
    _refused(repo, {**env, "ADR_KIT_ROOT": str(ROOT)})


@needs_tools
def test_the_copilot_payload_it_loads_live_is_found(tmp_path):
    repo, home, env = project(tmp_path)
    payload = home / ".local" / "share" / "adr-kit" / "marketplaces" / "99.0.0"
    link_engine(payload / "copilot", ROOT / "copilot")
    _refused(repo, env)


@needs_tools
def test_an_installer_payload_honours_xdg_data_home(tmp_path):
    repo, _home, env = project(tmp_path)
    data = tmp_path / "data"
    link_engine(data / "adr-kit" / "marketplaces" / "99.0.0" / "copilot", ROOT / "copilot")
    _refused(repo, {**env, "XDG_DATA_HOME": str(data)})


@needs_tools
def test_the_opencode_package_in_the_project_is_found(tmp_path):
    repo, _home, env = project(tmp_path)
    link_engine(repo / "node_modules" / "@rvdbreemen" / "adr-kit-opencode")
    _refused(repo, env)


@needs_tools
def test_the_opencode_package_in_opencodes_cache_is_found(tmp_path):
    # OpenCode 1.19.0 keeps one directory per spec under its cache (observed).
    repo, home, env = project(tmp_path)
    spec = home / ".cache" / "opencode" / "packages" / "@rvdbreemen" / "adr-kit-opencode@0.59.1"
    link_engine(spec / "node_modules" / "@rvdbreemen" / "adr-kit-opencode")
    _refused(repo, env)


@needs_tools
def test_without_any_engine_the_hook_still_says_where_it_looked(tmp_path):
    repo, _home, env = project(tmp_path)
    stage_violation(repo, env)
    result = git(repo, "commit", "-m", "no engine", env=env)
    assert result.returncode == 0
    assert "ADR_KIT_ROOT" in result.stderr
