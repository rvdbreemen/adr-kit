"""Tests for bin/adr-guardian multi-session-safe state handling (task-9).

Invariants under test:
  - atomic_save_state is atomic: a simulated interruption (temp file written but
    never moved into place) leaves the previous state file valid.
  - _load_state tolerates a corrupt/partial state file: treats it as empty
    state, logs one stderr warning, never raises; the next stamp overwrites
    the file with valid JSON.
  - State read-modify-write updates preserve unrelated keys through one shared
    transaction contract.
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
sys.path.insert(0, str(REPO_ROOT / "bin"))
from adr_state import atomic_save_state, update_state

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
        atomic_save_state(state_path, state)
        on_disk = json.loads(state_path.read_text(encoding="utf-8"))
        assert on_disk == state

    def test_interrupted_write_leaves_previous_state_valid(self, guardian, tmp_path):
        """Simulate a writer that died after writing its temp file but before
        os.replace: the stray temp file must not affect the state file."""
        state_path = tmp_path / ".adr-kit-state.json"
        original = {"cheap_tier": {"last_run": "2026-06-01T00:00:00+00:00"}}
        atomic_save_state(state_path, original)

        # Simulated interruption: temp file written, replace never happened.
        stray_tmp = tmp_path / f"{state_path.name}.99999.tmp"
        stray_tmp.write_text('{"cheap_tier": {"last_ru', encoding="utf-8")

        # The state file is untouched and still valid.
        assert json.loads(state_path.read_text(encoding="utf-8")) == original
        assert guardian._load_state(state_path) == original

        # A later save still works and the stray temp file stays out of the way.
        updated = {"cheap_tier": {"last_run": "2026-06-02T00:00:00+00:00"}}
        atomic_save_state(state_path, updated)
        assert json.loads(state_path.read_text(encoding="utf-8")) == updated

    def test_no_leftover_tmp_after_successful_save(self, guardian, tmp_path):
        state_path = tmp_path / ".adr-kit-state.json"
        atomic_save_state(state_path, {"k": 1})
        leftovers = list(tmp_path.glob(".*.tmp"))
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
# Transactional state updates
# ---------------------------------------------------------------------------

class TestInterleavedStamps:
    def test_separate_transactions_preserve_unrelated_updates(self, guardian, tmp_path):
        state_path = tmp_path / ".adr-kit-state.json"
        base = json.loads(json.dumps(guardian.DEFAULT_STATE))
        atomic_save_state(state_path, base)

        def update_cheap(state):
            state["cheap_tier"]["last_run"] = "2026-06-10T10:00:00+00:00"
            state["cheap_tier"]["drift_violations"] = 1
            return True, None

        def update_watch(state):
            state["watch"] = {"nudges": {"ADR-001|src/a.py": "2026-06-10"}}
            return True, None

        update_state(
            state_path,
            lambda: json.loads(json.dumps(guardian.DEFAULT_STATE)),
            update_cheap,
        )
        update_state(
            state_path,
            lambda: json.loads(json.dumps(guardian.DEFAULT_STATE)),
            update_watch,
        )
        on_disk = json.loads(state_path.read_text(encoding="utf-8"))
        assert on_disk["cheap_tier"]["drift_violations"] == 1
        assert "ADR-001|src/a.py" in on_disk["watch"]["nudges"]


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
