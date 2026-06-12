"""Tests for bin/adr-guardian multi-session-safe state handling (task-9).

Invariants under test:
  - _save_state is atomic: a simulated interruption (temp file written but
    never moved into place) leaves the previous state file valid.
  - _load_state tolerates a corrupt/partial state file: treats it as empty
    state, logs one stderr warning, never raises; the next stamp overwrites
    the file with valid JSON.
  - Two interleaved stamp-style read-modify-write cycles end with exactly one
    valid winner (last-writer-wins), never a corrupt file.
  - The CI-cron sweep workflow files exist and have the required structure
    (cheap tier only, report-only, no LLM, no extra secrets). PyYAML is not
    stdlib, so this is a string-level structural check, consistent with the
    stdlib-only test posture of this repo.

Import strategy: bin/adr-guardian has no .py extension, so it is loaded via
SourceFileLoader (same pattern as tests/test_adr_context.py).
"""
from __future__ import annotations

import importlib.machinery
import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
ADR_GUARDIAN = REPO_ROOT / "bin" / "adr-guardian"
WORKFLOW_SELF = REPO_ROOT / ".github" / "workflows" / "adr-guardian-audit.yml"
WORKFLOW_TEMPLATE = REPO_ROOT / "templates" / "github-workflows" / "adr-guardian-audit.yml"


def _load_module():
    loader = importlib.machinery.SourceFileLoader(
        "adr_guardian_state_mod", str(ADR_GUARDIAN)
    )
    spec = importlib.util.spec_from_loader("adr_guardian_state_mod", loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def guardian():
    return _load_module()


def _run(args: list, cwd: Path) -> "subprocess.CompletedProcess":
    env = os.environ.copy()
    env.pop("CLAUDE_PROJECT_DIR", None)
    return subprocess.run(
        [sys.executable, str(ADR_GUARDIAN)] + args,
        capture_output=True,
        text=True,
        encoding="utf-8",
        cwd=str(cwd),
        env=env,
    )


# ---------------------------------------------------------------------------
# Atomic write
# ---------------------------------------------------------------------------

class TestAtomicWrite:
    def test_save_state_produces_valid_json(self, guardian, tmp_path):
        state_path = tmp_path / ".adr-kit-state.json"
        state = {"cheap_tier": {"last_run": "2026-06-01T00:00:00+00:00"}}
        guardian._save_state(state_path, state)
        on_disk = json.loads(state_path.read_text(encoding="utf-8"))
        assert on_disk == state

    def test_interrupted_write_leaves_previous_state_valid(self, guardian, tmp_path):
        """Simulate a writer that died after writing its temp file but before
        os.replace: the stray temp file must not affect the state file."""
        state_path = tmp_path / ".adr-kit-state.json"
        original = {"cheap_tier": {"last_run": "2026-06-01T00:00:00+00:00"}}
        guardian._save_state(state_path, original)

        # Simulated interruption: temp file written, replace never happened.
        stray_tmp = tmp_path / f"{state_path.name}.99999.tmp"
        stray_tmp.write_text('{"cheap_tier": {"last_ru', encoding="utf-8")

        # The state file is untouched and still valid.
        assert json.loads(state_path.read_text(encoding="utf-8")) == original
        assert guardian._load_state(state_path) == original

        # A later save still works and the stray temp file stays out of the way.
        updated = {"cheap_tier": {"last_run": "2026-06-02T00:00:00+00:00"}}
        guardian._save_state(state_path, updated)
        assert json.loads(state_path.read_text(encoding="utf-8")) == updated

    def test_no_leftover_tmp_after_successful_save(self, guardian, tmp_path):
        state_path = tmp_path / ".adr-kit-state.json"
        guardian._save_state(state_path, {"k": 1})
        leftovers = list(tmp_path.glob(f"{state_path.name}.*.tmp"))
        assert leftovers == []


# ---------------------------------------------------------------------------
# Corrupt state tolerance
# ---------------------------------------------------------------------------

class TestCorruptState:
    def test_corrupt_json_treated_as_empty_state(self, guardian, tmp_path, capsys):
        state_path = tmp_path / ".adr-kit-state.json"
        state_path.write_text('{"cheap_tier": {"last_ru', encoding="utf-8")
        state = guardian._load_state(state_path)
        assert state == guardian.DEFAULT_STATE
        err = capsys.readouterr().err
        assert "[adr-guardian] warning" in err
        # The corrupt file is left in place, not deleted silently.
        assert state_path.exists()

    def test_non_dict_json_treated_as_empty_state(self, guardian, tmp_path, capsys):
        state_path = tmp_path / ".adr-kit-state.json"
        state_path.write_text("[1, 2, 3]\n", encoding="utf-8")
        state = guardian._load_state(state_path)
        assert state == guardian.DEFAULT_STATE
        assert "[adr-guardian] warning" in capsys.readouterr().err

    def test_missing_file_is_silent(self, guardian, tmp_path, capsys):
        state = guardian._load_state(tmp_path / "nope.json")
        assert state == guardian.DEFAULT_STATE
        assert capsys.readouterr().err == ""

    def test_corrupt_state_overwritten_by_next_stamp(self, tmp_path):
        """End-to-end: stamp via the CLI overwrites a corrupt state file."""
        state_dir = tmp_path / "statedir"
        state_dir.mkdir()
        state_path = state_dir / ".adr-kit-state.json"
        state_path.write_text("NOT JSON {{{", encoding="utf-8")

        result = _run(
            ["stamp", "cheap", "--violations", "2", "--state-dir", str(state_dir)],
            cwd=tmp_path,
        )
        assert result.returncode == 0
        on_disk = json.loads(state_path.read_text(encoding="utf-8"))
        assert on_disk["cheap_tier"]["drift_violations"] == 2
        assert on_disk["cheap_tier"]["last_run"] is not None

    def test_check_exits_zero_on_corrupt_state(self, tmp_path):
        adr_dir = tmp_path / "docs" / "adr"
        adr_dir.mkdir(parents=True)
        (adr_dir / "ADR-001-stub.md").write_text(
            "# ADR-001 Stub\n\n## Status\n\nAccepted\n", encoding="utf-8"
        )
        (adr_dir / ".adr-kit-state.json").write_text("garbage", encoding="utf-8")
        result = _run(["check"], cwd=tmp_path)
        assert result.returncode == 0


# ---------------------------------------------------------------------------
# Interleaved stamps (last-writer-wins)
# ---------------------------------------------------------------------------

class TestInterleavedStamps:
    def test_two_interleaved_writers_one_valid_winner(self, guardian, tmp_path):
        """Simulate two sessions doing read-modify-write with full overlap:
        both read the same base state, then write in sequence. The file must
        end up as valid JSON equal to the LAST writer's state."""
        state_path = tmp_path / ".adr-kit-state.json"
        base = json.loads(json.dumps(guardian.DEFAULT_STATE))
        guardian._save_state(state_path, base)

        session_a = guardian._load_state(state_path)
        session_b = guardian._load_state(state_path)

        session_a["cheap_tier"]["last_run"] = "2026-06-10T10:00:00+00:00"
        session_a["cheap_tier"]["drift_violations"] = 1
        session_b["cheap_tier"]["last_run"] = "2026-06-10T10:00:05+00:00"
        session_b["cheap_tier"]["drift_violations"] = 7

        guardian._save_state(state_path, session_a)
        guardian._save_state(state_path, session_b)

        on_disk = json.loads(state_path.read_text(encoding="utf-8"))
        assert on_disk == session_b  # last writer wins, file never corrupt

    def test_state_lock_is_best_effort_and_reentrant_safe(self, guardian, tmp_path):
        """Holding the lock in one context must not block or crash a second
        writer (non-blocking, best-effort semantics)."""
        state_path = tmp_path / ".adr-kit-state.json"
        with guardian._state_lock(state_path):
            # A concurrent save while the lock is held still succeeds.
            guardian._save_state(state_path, {"k": "concurrent"})
        assert json.loads(state_path.read_text(encoding="utf-8")) == {"k": "concurrent"}


# ---------------------------------------------------------------------------
# Workflow structural checks (no PyYAML in stdlib: string-level assertions)
# ---------------------------------------------------------------------------

WORKFLOW_REQUIRED_SNIPPETS = [
    "name: ADR guardian audit",
    "schedule:",
    "cron:",
    "workflow_dispatch:",
    "issues: write",
    "contents: read",
    "adr-lint",
    "adr-retire",
    "adr-status",
    "ADR guardian audit",  # fixed tracking-issue title
    "gh issue edit",       # update path for the single tracking issue
    "gh issue create",
]


@pytest.mark.parametrize("workflow_path", [WORKFLOW_SELF, WORKFLOW_TEMPLATE],
                         ids=["self-dogfood", "downstream-template"])
class TestWorkflowStructure:
    def test_workflow_exists(self, workflow_path):
        assert workflow_path.is_file(), f"missing workflow: {workflow_path}"

    def test_workflow_required_keys(self, workflow_path):
        text = workflow_path.read_text(encoding="utf-8")
        for snippet in WORKFLOW_REQUIRED_SNIPPETS:
            assert snippet in text, f"workflow missing: {snippet!r}"

    def test_workflow_never_runs_llm(self, workflow_path):
        text = workflow_path.read_text(encoding="utf-8")
        assert "--llm" not in text
        assert "adr-suggest" not in text
        assert "ANTHROPIC_API_KEY" not in text

    def test_workflow_uses_only_github_token(self, workflow_path):
        text = workflow_path.read_text(encoding="utf-8")
        # github.token is fine; any other secrets reference is not.
        assert "secrets." not in text
