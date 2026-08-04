"""The signer is proposed and derived, never assumed (TASK-89, spec R8/R8.1).

Every lifecycle command writes a Status History entry naming who decided, and
until now it refused outright unless someone had configured `lifecycle.signer`
by hand. That refusal shipped as a breaking change in v0.44.0: a fresh clone, a
container and a CI runner all failed at the very first command, `bin/adr new`
included.

The refusal was stricter than R8.1 asks for. R8.1 forbids "a default that names
the tool" -- the old `adr-kit` actor, where the toolkit wrote itself into the
record as the decider. `git config user.name` is the opposite of that: it is a
value the human configured on this machine, and every commit in the repository
already carries it.

Two properties survive the change, and this file holds both:

* **never silently.** A derived actor is announced, because a name that lands in
  an immutable history should never be one the user did not know was written;
* **never a machine.** `github-actions[bot]`, `runner`, a bare `user` are
  configured values that name a machine, and R8 asks for evidence of which
  *human* accepted. Those fall through to the refusal.
"""
from __future__ import annotations

import importlib.machinery
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
ADR = REPO_ROOT / "bin" / "adr"


def _lifecycle_module():
    name = "adr_lifecycle_signer"
    loader = importlib.machinery.SourceFileLoader(name, str(ADR))
    spec = importlib.util.spec_from_loader(name, loader)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    loader.exec_module(module)
    return module


lifecycle = _lifecycle_module()


def _isolated_env(tmp_path: Path) -> dict:
    """An environment that answers about the fixture, not about this machine.

    Two ambient identities would otherwise leak in and make the result depend on
    who runs the suite: git falls back to the developer's global `user.name` when
    the repository sets none, and `gh` is signed in on a developer machine and
    signed out on a runner. Both are pointed at nothing here, so a test that
    claims "no identity is available" is actually testing that.

    This is the same failure mode that made the v0.44.0 release PR red -- a test
    passing because the machine happened to supply something the code needed.
    """
    import os

    void = tmp_path / "no-such-config"
    return {
        **os.environ,
        "GIT_CONFIG_GLOBAL": str(void),
        "GIT_CONFIG_SYSTEM": str(void),
        "GH_CONFIG_DIR": str(tmp_path / "gh-empty"),
        "GH_TOKEN": "",
        "GITHUB_TOKEN": "",
    }


def _repo(tmp_path: Path, user_name: str | None) -> Path:
    root = tmp_path / "project"
    (root / "docs" / "adr").mkdir(parents=True)
    env = _isolated_env(tmp_path)
    subprocess.run(["git", "init", "-q", str(root)], check=True, capture_output=True,
                   env=env)
    if user_name is not None:
        subprocess.run(["git", "config", "user.name", user_name],
                       cwd=root, check=True, capture_output=True, env=env)
    return root


def _adr(root: Path, *args: str):
    return subprocess.run(
        [sys.executable, str(ADR), *args, "--adr-dir", str(root / "docs" / "adr")],
        cwd=root, capture_output=True, text=True, encoding="utf-8", errors="replace",
        env=_isolated_env(root.parent),
    )


# ---------------------------------------------------------------------------
# Derivation: a person-named git config just works
# ---------------------------------------------------------------------------

def test_a_person_named_git_config_yields_a_working_signer(tmp_path):
    root = _repo(tmp_path, "Robert van den Breemen")

    result = _adr(root, "new", "A Decision")

    assert result.returncode == 0, result.stderr
    created = next((root / "docs" / "adr").glob("ADR-[0-9]*.md"))
    assert 'changed_by: "User: Robert van den Breemen"' in created.read_text(encoding="utf-8")


def test_the_derived_actor_is_announced_never_silent(tmp_path):
    """A name that lands in an immutable history must not arrive unseen."""
    root = _repo(tmp_path, "Ada Lovelace")

    result = _adr(root, "new", "A Decision")

    assert "signing as" in result.stderr
    assert "User: Ada Lovelace" in result.stderr
    assert "git config user.name" in result.stderr
    # And it says how to choose differently.
    assert "signer --set" in result.stderr


# ---------------------------------------------------------------------------
# Precedence: explicit beats configured beats derived
# ---------------------------------------------------------------------------

def test_the_flag_wins_over_everything(tmp_path):
    root = _repo(tmp_path, "Ada Lovelace")
    (root / "docs" / "adr" / ".adr-kit.local.json").write_text(
        json.dumps({"lifecycle": {"signer": "User: Configured Human"}}), encoding="utf-8"
    )

    result = _adr(root, "new", "A Decision", "--changed-by", "User: Explicit Human")

    assert result.returncode == 0, result.stderr
    text = next((root / "docs" / "adr").glob("ADR-[0-9]*.md")).read_text(encoding="utf-8")
    assert "User: Explicit Human" in text
    assert "Configured Human" not in text
    assert "Ada Lovelace" not in text


def test_the_configured_signer_wins_over_git(tmp_path):
    root = _repo(tmp_path, "Ada Lovelace")
    (root / "docs" / "adr" / ".adr-kit.local.json").write_text(
        json.dumps({"lifecycle": {"signer": "User: Configured Human"}}), encoding="utf-8"
    )

    result = _adr(root, "new", "A Decision")

    assert result.returncode == 0, result.stderr
    text = next((root / "docs" / "adr").glob("ADR-[0-9]*.md")).read_text(encoding="utf-8")
    assert "User: Configured Human" in text
    assert "Ada Lovelace" not in text
    # Nothing was derived, so nothing is announced.
    assert "signing as" not in result.stderr


# ---------------------------------------------------------------------------
# A machine is not a human
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "identity",
    [
        "github-actions[bot]",
        "dependabot[bot]",
        "renovate[bot]",
        "GitHub Actions",
        "runner",
        "jenkins",
        "root",
        "user",
        "unknown",
        "adr-kit",
    ],
)
def test_a_machine_identity_is_refused_rather_than_adopted(tmp_path, identity):
    root = _repo(tmp_path, identity)

    result = _adr(root, "new", "A Decision")

    assert result.returncode != 0, f"{identity!r} was adopted as a human signer"
    assert "no signer configured" in result.stderr
    # The refusal explains why this particular value was not taken.
    assert "does not name a person" in result.stderr
    assert not list((root / "docs" / "adr").glob("ADR-[0-9]*.md")), "nothing may be written"


def test_the_refusal_still_names_both_manual_routes(tmp_path):
    root = _repo(tmp_path, None)

    result = _adr(root, "new", "A Decision")

    assert result.returncode != 0
    assert "signer --set" in result.stderr
    assert "--changed-by" in result.stderr


@pytest.mark.parametrize(
    ("identity", "expected"),
    [
        ("Robert van den Breemen", True),
        ("Ada Lovelace", True),
        ("rvdbreemen", True),
        ("github-actions[bot]", False),
        ("bot", False),
        ("CI", False),
        ("", False),
        (None, False),
        ("<noreply@github.com>", False),
    ],
)
def test_person_shaped_draws_the_line_where_it_says_it_does(identity, expected):
    assert lifecycle.person_shaped(identity) is expected


# ---------------------------------------------------------------------------
# Install and upgrade: propose, write nothing
# ---------------------------------------------------------------------------

def test_suggest_writes_nothing_and_shows_the_source(tmp_path):
    root = _repo(tmp_path, "Grace Hopper")

    result = _adr(root, "signer", "--suggest")

    assert result.returncode == 0, result.stderr
    assert "User: Grace Hopper" in result.stdout
    assert "git config user.name" in result.stdout
    assert "Nothing is written until you choose" in result.stdout
    assert not (root / "docs" / "adr" / ".adr-kit.local.json").exists()


def test_suggest_json_is_machine_readable(tmp_path):
    root = _repo(tmp_path, "Grace Hopper")

    result = _adr(root, "signer", "--suggest", "--format", "json")

    # Assert the exit before parsing. A failed command yields empty stdout, and
    # json.loads then raises a decode error that buries the stderr explaining
    # what actually went wrong.
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["configured"] is None
    assert payload["candidates"][0]["actor"] == "User: Grace Hopper"
    assert payload["candidates"][0]["source"]


def test_suggest_does_not_offer_a_machine_identity(tmp_path):
    root = _repo(tmp_path, "github-actions[bot]")

    result = _adr(root, "signer", "--suggest", "--format", "json")

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert all("bot" not in c["name"].casefold() for c in payload["candidates"])


def test_suggest_leaves_an_existing_signer_alone(tmp_path):
    root = _repo(tmp_path, "Grace Hopper")
    config = root / "docs" / "adr" / ".adr-kit.local.json"
    config.write_text(json.dumps({"lifecycle": {"signer": "User: Already Chosen"}}),
                      encoding="utf-8")
    before = config.read_bytes()

    result = _adr(root, "signer", "--suggest")

    assert "already configured: User: Already Chosen" in result.stdout
    assert config.read_bytes() == before


def test_signer_reports_where_the_current_value_comes_from(tmp_path):
    """AC#6: provenance, because 'why is this the name?' is the question."""
    root = _repo(tmp_path, "Grace Hopper")

    derived = _adr(root, "signer")
    assert "User: Grace Hopper" in derived.stdout
    assert "git config user.name (derived" in derived.stdout

    (root / "docs" / "adr" / ".adr-kit.local.json").write_text(
        json.dumps({"lifecycle": {"signer": "User: Chosen"}}), encoding="utf-8"
    )
    configured = _adr(root, "signer")
    assert "User: Chosen" in configured.stdout
    assert "machine-local" in configured.stdout


def test_candidate_duplicates_collapse(monkeypatch):
    """The GitHub name and git user.name are usually the same string."""
    monkeypatch.setattr(
        lifecycle, "github_identity",
        lambda: [
            {"name": "Grace Hopper", "source": "gh api user (.name)"},
            {"name": "ghopper", "source": "gh api user (.login)"},
        ],
    )
    monkeypatch.setattr(lifecycle, "git_user_name", lambda: "Grace Hopper")

    candidates = lifecycle.signer_candidates()

    names = [c["name"] for c in candidates]
    assert names == ["Grace Hopper", "ghopper"], candidates
    # The GitHub profile name wins the tie, because it is the one a person chose
    # to be called; the identical git value collapses into it rather than
    # appearing as a second, indistinguishable option.
    assert candidates[0]["source"] == "gh api user (.name)"


def test_a_machine_identity_is_never_a_candidate(monkeypatch):
    monkeypatch.setattr(
        lifecycle, "github_identity",
        lambda: [{"name": "github-actions[bot]", "source": "gh api user (.login)"}],
    )
    monkeypatch.setattr(lifecycle, "git_user_name", lambda: "runner")

    assert lifecycle.signer_candidates() == []


# ---------------------------------------------------------------------------
# The skills say so
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("skill", ["setup", "init", "upgrade"])
def test_the_install_and_upgrade_paths_propose_a_signer(skill):
    text = (REPO_ROOT / "skills" / skill / "SKILL.md").read_text(encoding="utf-8")

    assert "signer --suggest" in text, f"{skill} never proposes a signer"
    assert "signer --set" in text
    # And it says why a bot is not offered.
    assert "human" in text.casefold()
