"""The release driver must be safe to run twice, and must refuse the two things that cost releases.

ADR-042 makes idempotence a Must clause rather than a nicety: a release that
dies halfway is the normal case, so the recovery has to be "run it again". Each
phase answers `done()` from the repository's state, and these tests pin that
the answer is derived rather than remembered.

The two refusals are here because each one maps to a release this project
actually lost or degraded: a tag that did not name the commit carrying the
version (v0.55.0), and a dist-tag left pointing at an older release by the
order staged versions were approved in (v0.55.1).
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
DRIVER = REPO_ROOT / "scripts" / "release.py"


def _load(name: str):
    spec = importlib.util.spec_from_file_location(
        name, REPO_ROOT / "scripts" / f"{name}.py"
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    sys.path.insert(0, str(REPO_ROOT / "scripts"))
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def phases():
    _load("release_shell")
    return _load("release_phases")


@pytest.fixture(scope="module")
def npm(phases):  # phases first: both import release_shell
    return _load("release_npm")


def _context(phases, **overrides):
    fields = {"version": "9.9.9", "skip_tests": True, "timeout_min": 1}
    fields.update(overrides)
    return phases.Context(**fields)


def test_every_phase_can_say_whether_it_is_already_done(phases):
    """Idempotence is structural: a phase without a done-check cannot be skipped."""
    assert phases.PHASES, "the driver declares no phases"
    for phase in phases.PHASES:
        assert callable(phase.done), f"{phase.name} has no done-check"
        assert callable(phase.run), f"{phase.name} has nothing to run"
        assert phase.step, f"{phase.name} does not name the runbook step it mirrors"


def test_phases_mirror_the_runbook_step_order(phases):
    """docs/RELEASING.md is the specification; drift between the two must be visible."""
    steps = [phase.step for phase in phases.PHASES]
    assert steps == sorted(steps), f"phases run out of runbook order: {steps}"


def test_status_reports_every_phase_and_changes_nothing():
    """--status is the "what is left" view, and must be safe on a dirty checkout."""
    before = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=REPO_ROOT, capture_output=True, text=True,
    ).stdout
    result = subprocess.run(
        [sys.executable, str(DRIVER), "9.9.9", "--status"],
        cwd=REPO_ROOT, capture_output=True, text=True, encoding="utf-8",
    )
    after = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=REPO_ROOT, capture_output=True, text=True,
    ).stdout

    assert result.returncode == 0, result.stderr
    assert after == before, "--status modified the working tree"
    for name in ("preflight", "prepare", "verify", "land", "tag", "syncback", "install"):
        assert name in result.stdout, f"{name} missing from the status report"
    assert "npm" in result.stdout


@pytest.mark.parametrize("bad", ["1.2", "v1", "latest", "1.2.3.4"])
def test_a_version_that_is_not_semver_is_refused(bad):
    result = subprocess.run(
        [sys.executable, str(DRIVER), bad, "--status"],
        cwd=REPO_ROOT, capture_output=True, text=True,
    )
    assert result.returncode != 0
    assert "MAJOR.MINOR.PATCH" in result.stderr


def test_prepare_refuses_a_placeholder_changelog(phases, tmp_path, monkeypatch):
    """release-publish.yml publishes that section verbatim as the Release body.

    Shipping the scaffold would announce a release with "TODO: describe this
    release." as its entire text, and a GitHub Release body cannot be quietly
    fixed afterwards for anyone who already read it.
    """
    monkeypatch.setattr(phases, "ROOT", tmp_path)
    (tmp_path / "CHANGELOG.md").write_text(
        "# Changelog\n\n## [9.9.9] - 2026-01-01\n\n### Added\n\n- TODO: describe this release.\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(phases, "_version_everywhere", lambda ctx: True)

    with pytest.raises(phases.ReleaseError) as caught:
        phases.prepare(_context(phases))

    assert "placeholder" in str(caught.value)
    assert "verbatim" in str(caught.value)


def test_prepare_accepts_a_written_changelog(phases, tmp_path, monkeypatch):
    monkeypatch.setattr(phases, "ROOT", tmp_path)
    (tmp_path / "CHANGELOG.md").write_text(
        "# Changelog\n\n## [9.9.9] - 2026-01-01\n\nThe thing this release does.\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(phases, "_version_everywhere", lambda ctx: True)

    assert phases.prepare(_context(phases))


def test_a_tag_that_does_not_name_main_is_refused(phases, monkeypatch):
    """The check that would have saved v0.55.0.

    That tag sat on the dev tip, where every version site still read the
    previous release. The refusal also has to say NOT to move the tag: a pushed
    tag is a public ref consumers may register a marketplace from.
    """
    monkeypatch.setattr(phases, "_wait_until", lambda predicate, ctx, what: None)
    monkeypatch.setattr(phases, "git", lambda *a, **k: (0, "1111111111111111111111111111111111111111", ""))
    monkeypatch.setattr(phases, "_main_sha", lambda: "2222222222222222222222222222222222222222")

    with pytest.raises(phases.ReleaseError) as caught:
        phases.verify_tag(_context(phases))

    message = str(caught.value)
    assert "origin/main" in message
    assert "Do not move the tag" in message


def test_a_tag_that_names_main_passes(phases, monkeypatch):
    sha = "3333333333333333333333333333333333333333"
    monkeypatch.setattr(phases, "_wait_until", lambda predicate, ctx, what: None)
    monkeypatch.setattr(phases, "git", lambda *a, **k: (0, sha, ""))
    monkeypatch.setattr(phases, "_main_sha", lambda: sha)

    assert phases.verify_tag(_context(phases))


def test_the_npm_instructions_carry_the_ordering_warning(phases, npm):
    """npm sets `latest` to the version published LAST, not the highest.

    Approving 0.55.1, then 0.53.0, then 0.54.0 on 2026-08-26 left `latest` on
    0.54.0 while 0.55.1 was the release, so `npm install` served the wrong one.
    The instructions are the only place a maintainer meets this in time.
    """
    text = npm.npm_instructions(_context(phases))
    assert "ASCENDING" in text
    assert "LAST" in text
    assert "dist-tag ls" in text
    assert "9.9.9" in text


def test_a_published_version_is_not_reported_as_awaiting_approval(phases, npm, monkeypatch):
    """The two npm states look identical from outside and have opposite fixes.

    Sending a maintainer to the approval flow for a package that is already
    published wastes the one window in which the real fault is cheap to fix:
    `latest` points at an older release and every `npm install` serves it.
    """
    monkeypatch.setattr(npm, "_dist_tags", lambda ctx: {"latest": "9.9.8"})
    monkeypatch.setattr(
        npm, "run",
        lambda *a, **k: (0, '["9.9.8","9.9.9"]', ""),
    )
    ctx = _context(phases)

    assert not npm.npm_latest_done(ctx)
    assert npm.npm_published(ctx), "a version in `npm view versions` is published"

    message = npm.npm_wrong_latest(ctx)
    assert "9.9.8" in message, "the message must name what npm actually serves"
    assert "dist-tag add" in message, "and the command that repairs it"
    assert "approve" not in message, "approval cannot fix an already-published version"


def test_a_single_published_version_is_recognised(phases, npm, monkeypatch):
    """`npm view <pkg> versions --json` returns a bare string, not a list, for one version.

    Left unhandled, `version in json.loads(out)` becomes a substring test on a
    string: it answers True for "9.9" against "9.9.9" and False for a genuine
    lone match written any other way.
    """
    monkeypatch.setattr(npm, "run", lambda *a, **k: (0, '"9.9.9"', ""))
    assert npm.npm_published(_context(phases))

    monkeypatch.setattr(npm, "run", lambda *a, **k: (0, '"9.9.8"', ""))
    assert not npm.npm_published(_context(phases))


def test_install_reads_the_version_back_rather_than_trusting_an_exit_code(phases, monkeypatch):
    """An installer exit code is not evidence that a client advanced.

    On 2026-08-27 the codex install reported a rollback failure while leaving
    the plugin installed and enabled, and a run that reported success had still
    left two clients on the previous version.
    """
    monkeypatch.setattr(phases, "run", lambda *a, **k: (0, "", ""))
    monkeypatch.setattr(phases, "_client_version", lambda client: "0.0.1")

    with pytest.raises(phases.ReleaseError) as caught:
        phases.install(_context(phases))

    assert "do not report the released version" in str(caught.value)
