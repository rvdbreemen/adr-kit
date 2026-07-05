"""Tests for bin/adr-watch: in-flight ADR guidance for just-edited files.

Design invariants under test:
  - nudge on Enforcement path_glob match for the edited path
  - keyword relevance fallback (adr-context style) when no glob matches
  - no nudge for a non-matching path
  - cooldown: same ADR+file pair is not nudged twice within the window
  - self-guard: silent exit 0 when no docs/adr/ with ADRs is present
  - corrupt .adr-kit-state.json is tolerated (treated as empty)
  - --hook mode: parses the PostToolUse payload and emits the JSON envelope
  - always exits 0 (advisory, never blocks)
  - performance: 50 ADRs scored well under the CI budget

All subprocess calls use [sys.executable, SCRIPT] to work on Windows
(no shebang execution, no PATH tricks needed). The performance test runs
in-process via run_watch() to avoid interpreter cold-start overhead.
"""

from __future__ import annotations

import importlib.machinery
import importlib.util
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = REPO_ROOT / "bin" / "adr-watch"


# ---------------------------------------------------------------------------
# Helper: import the module so we can call functions in-process
# ---------------------------------------------------------------------------

def _load_module():
    """Dynamically import bin/adr-watch as a Python module (no .py extension)."""
    loader = importlib.machinery.SourceFileLoader("adr_watch", str(SCRIPT))
    spec = importlib.util.spec_from_loader("adr_watch", loader)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["adr_watch"] = mod
    loader.exec_module(mod)
    return mod


_mod = _load_module()


# ---------------------------------------------------------------------------
# Subprocess helper
# ---------------------------------------------------------------------------

def _run(args: list, cwd, env_extra=None, stdin_text=None) -> tuple:
    """Run adr-watch with given args; return (returncode, stdout, stderr)."""
    env = os.environ.copy()
    # Remove Claude Code env vars so tests don't pick up the repo's own
    # docs/adr/ or switch into the hook output envelope unexpectedly.
    env.pop("CLAUDE_PROJECT_DIR", None)
    env.pop("CLAUDE_PLUGIN_ROOT", None)
    if env_extra:
        env.update(env_extra)
    result = subprocess.run(
        [sys.executable, str(SCRIPT)] + args,
        capture_output=True,
        text=True,
        encoding="utf-8",
        cwd=str(cwd),
        env=env,
        input=stdin_text,
    )
    return result.returncode, result.stdout, result.stderr


# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------

ADR_WITH_GLOB = """# ADR-001 No direct database calls outside the repository layer

## Status

Accepted, 2026-01-15.

## Context

Direct SQL in handlers caused tight coupling.

## Decision

All database access goes through the repository layer.

## Enforcement

```json
{{
  "forbid_pattern": [
    {{"pattern": "cursor\\\\.execute", "path_glob": "{glob}",
      "message": "no direct DB calls outside repository layer"}}
  ]
}}
```
"""

ADR_KEYWORD_ONLY = """# ADR-002 Authentication middleware owns session tokens

## Status

Accepted, 2026-02-01.

## Context

Token handling was scattered.

## Decision

The authentication middleware is the only component that reads or
writes session tokens.
"""

ADR_PROPOSED = """# ADR-003 Everything is cached forever

## Status

Proposed, 2026-03-01.

## Decision

Cache the entire universe.

## Enforcement

```json
{{"forbid_pattern": [{{"pattern": "no_cache", "path_glob": "{glob}"}}]}}
```
"""


def _make_project(tmp_path: Path) -> Path:
    """Create docs/adr/ under tmp_path; return the adr dir."""
    adr_dir = tmp_path / "docs" / "adr"
    adr_dir.mkdir(parents=True)
    return adr_dir


def _write_adr(adr_dir: Path, name: str, content: str) -> None:
    (adr_dir / name).write_text(content, encoding="utf-8")


def _standard_project(tmp_path: Path) -> Path:
    adr_dir = _make_project(tmp_path)
    _write_adr(adr_dir, "ADR-001-repository-layer.md",
               ADR_WITH_GLOB.format(glob="src/**/*.py"))
    _write_adr(adr_dir, "ADR-002-auth-middleware.md", ADR_KEYWORD_ONLY)
    return adr_dir


# ---------------------------------------------------------------------------
# Enforcement-pattern matching
# ---------------------------------------------------------------------------

class TestEnforcementMatch:

    def test_nudge_on_glob_match(self, tmp_path):
        _standard_project(tmp_path)
        rc, out, err = _run(["src/db/queries.py"], cwd=tmp_path)
        assert rc == 0
        assert "[adr-watch] ADR-001" in out
        assert "src/db/queries.py" in out
        assert "No direct database calls outside the repository layer" in out

    def test_no_nudge_for_non_matching_path(self, tmp_path):
        _standard_project(tmp_path)
        rc, out, err = _run(["README.md"], cwd=tmp_path)
        assert rc == 0
        assert out.strip() == ""

    def test_proposed_adr_is_ignored(self, tmp_path):
        adr_dir = _make_project(tmp_path)
        _write_adr(adr_dir, "ADR-003-cache.md",
                   ADR_PROPOSED.format(glob="src/**/*.py"))
        rc, out, err = _run(["src/db/queries.py"], cwd=tmp_path)
        assert rc == 0
        assert out.strip() == ""

    def test_absolute_path_is_relativized(self, tmp_path):
        _standard_project(tmp_path)
        abs_path = str(tmp_path / "src" / "db" / "queries.py")
        rc, out, err = _run([abs_path], cwd=tmp_path)
        assert rc == 0
        assert "[adr-watch] ADR-001" in out
        assert "src/db/queries.py" in out

    def test_at_most_three_nudges(self, tmp_path):
        adr_dir = _make_project(tmp_path)
        for i in range(1, 6):
            _write_adr(
                adr_dir, f"ADR-{i:03d}-rule.md",
                ADR_WITH_GLOB.format(glob="src/**/*.py")
                .replace("ADR-001", f"ADR-{i:03d}"),
            )
        rc, out, err = _run(["src/db/queries.py"], cwd=tmp_path)
        assert rc == 0
        lines = [l for l in out.splitlines() if l.strip()]
        assert len(lines) == 3


# ---------------------------------------------------------------------------
# Keyword relevance fallback
# ---------------------------------------------------------------------------

class TestKeywordRelevance:

    def test_keyword_match_without_glob(self, tmp_path):
        _standard_project(tmp_path)
        rc, out, err = _run(["lib/authentication/middleware.go"], cwd=tmp_path)
        assert rc == 0
        assert "[adr-watch] ADR-002" in out

    def test_unrelated_path_no_keyword_match(self, tmp_path):
        _standard_project(tmp_path)
        rc, out, err = _run(["assets/logo.svg"], cwd=tmp_path)
        assert rc == 0
        assert out.strip() == ""


# ---------------------------------------------------------------------------
# Cooldown
# ---------------------------------------------------------------------------

class TestCooldown:

    def test_second_run_is_suppressed(self, tmp_path):
        adr_dir = _standard_project(tmp_path)
        rc1, out1, _ = _run(["src/db/queries.py"], cwd=tmp_path)
        assert "[adr-watch] ADR-001" in out1
        rc2, out2, _ = _run(["src/db/queries.py"], cwd=tmp_path)
        assert rc2 == 0
        assert out2.strip() == ""
        # State file records the nudge under the separate "watch" key.
        state = json.loads(
            (adr_dir / ".adr-kit-state.json").read_text(encoding="utf-8"))
        assert "watch" in state
        assert any(k.startswith("ADR-001|") for k in state["watch"]["nudges"])

    def test_different_file_is_not_suppressed(self, tmp_path):
        _standard_project(tmp_path)
        _run(["src/db/queries.py"], cwd=tmp_path)
        rc, out, _ = _run(["src/api/handlers.py"], cwd=tmp_path)
        assert rc == 0
        assert "[adr-watch] ADR-001" in out
        assert "src/api/handlers.py" in out

    def test_expired_cooldown_nudges_again(self, tmp_path):
        adr_dir = _standard_project(tmp_path)
        old = (datetime.now(tz=timezone.utc) - timedelta(hours=5)).isoformat()
        state = {"watch": {"nudges": {"ADR-001|src/db/queries.py": old}}}
        (adr_dir / ".adr-kit-state.json").write_text(
            json.dumps(state), encoding="utf-8")
        rc, out, _ = _run(["src/db/queries.py"], cwd=tmp_path)
        assert rc == 0
        assert "[adr-watch] ADR-001" in out

    def test_configurable_cooldown_window(self, tmp_path):
        adr_dir = _standard_project(tmp_path)
        (adr_dir / ".adr-kit.json").write_text(
            json.dumps({"watch": {"cooldown_hours": 48}}), encoding="utf-8")
        old = (datetime.now(tz=timezone.utc) - timedelta(hours=5)).isoformat()
        state = {"watch": {"nudges": {"ADR-001|src/db/queries.py": old}}}
        (adr_dir / ".adr-kit-state.json").write_text(
            json.dumps(state), encoding="utf-8")
        # 5h old nudge is still inside the 48h window: suppressed.
        rc, out, _ = _run(["src/db/queries.py"], cwd=tmp_path)
        assert rc == 0
        assert out.strip() == ""

    def test_guardian_state_keys_are_preserved(self, tmp_path):
        adr_dir = _standard_project(tmp_path)
        guardian_state = {"cheap_tier": {"last_run": "2026-06-01T00:00:00+00:00"}}
        (adr_dir / ".adr-kit-state.json").write_text(
            json.dumps(guardian_state), encoding="utf-8")
        _run(["src/db/queries.py"], cwd=tmp_path)
        state = json.loads(
            (adr_dir / ".adr-kit-state.json").read_text(encoding="utf-8"))
        assert state["cheap_tier"]["last_run"] == "2026-06-01T00:00:00+00:00"
        assert "watch" in state


# ---------------------------------------------------------------------------
# Self-guard and degradation
# ---------------------------------------------------------------------------

class TestSelfGuard:

    def test_no_docs_adr_dir(self, tmp_path):
        rc, out, err = _run(["src/db/queries.py"], cwd=tmp_path)
        assert rc == 0
        assert out.strip() == ""

    def test_docs_adr_dir_empty(self, tmp_path):
        (tmp_path / "docs" / "adr").mkdir(parents=True)
        rc, out, err = _run(["src/db/queries.py"], cwd=tmp_path)
        assert rc == 0
        assert out.strip() == ""

    def test_no_paths_given(self, tmp_path):
        _standard_project(tmp_path)
        rc, out, err = _run([], cwd=tmp_path)
        assert rc == 0
        assert out.strip() == ""

    def test_disabled_via_config(self, tmp_path):
        adr_dir = _standard_project(tmp_path)
        (adr_dir / ".adr-kit.json").write_text(
            json.dumps({"watch": {"enabled": False}}), encoding="utf-8")
        rc, out, err = _run(["src/db/queries.py"], cwd=tmp_path)
        assert rc == 0
        assert out.strip() == ""

    def test_corrupt_state_is_tolerated(self, tmp_path):
        adr_dir = _standard_project(tmp_path)
        (adr_dir / ".adr-kit-state.json").write_text(
            "{{{ this is not json", encoding="utf-8")
        rc, out, err = _run(["src/db/queries.py"], cwd=tmp_path)
        assert rc == 0
        assert "[adr-watch] ADR-001" in out
        # State file was rewritten as valid JSON.
        state = json.loads(
            (adr_dir / ".adr-kit-state.json").read_text(encoding="utf-8"))
        assert "watch" in state

    def test_malformed_enforcement_json_is_tolerated(self, tmp_path):
        adr_dir = _make_project(tmp_path)
        broken = ADR_WITH_GLOB.format(glob="src/**/*.py").replace(
            '"forbid_pattern"', '"forbid_pattern" oops')
        _write_adr(adr_dir, "ADR-001-broken.md", broken)
        rc, out, err = _run(["src/db/queries.py"], cwd=tmp_path)
        assert rc == 0  # no crash; the broken block just yields no globs


# ---------------------------------------------------------------------------
# Hook mode (--hook)
# ---------------------------------------------------------------------------

class TestHookMode:

    def test_hook_payload_plain_output(self, tmp_path):
        _standard_project(tmp_path)
        payload = json.dumps({
            "tool_name": "Edit",
            "tool_input": {"file_path": "src/db/queries.py"},
        })
        rc, out, err = _run(["--hook"], cwd=tmp_path, stdin_text=payload)
        assert rc == 0
        assert "[adr-watch] ADR-001" in out

    def test_hook_payload_json_envelope_under_claude(self, tmp_path):
        _standard_project(tmp_path)
        payload = json.dumps({
            "tool_name": "Write",
            "tool_input": {"file_path": "src/db/queries.py"},
        })
        rc, out, err = _run(
            ["--hook"], cwd=tmp_path, stdin_text=payload,
            env_extra={"CLAUDE_PLUGIN_ROOT": str(tmp_path)},
        )
        assert rc == 0
        envelope = json.loads(out)
        hso = envelope["hookSpecificOutput"]
        assert hso["hookEventName"] == "PostToolUse"
        assert "[adr-watch] ADR-001" in hso["additionalContext"]

    def test_hook_garbage_stdin_degrades_silently(self, tmp_path):
        _standard_project(tmp_path)
        rc, out, err = _run(["--hook"], cwd=tmp_path, stdin_text="not json at all")
        assert rc == 0
        assert out.strip() == ""

    def test_hook_payload_without_file_path(self, tmp_path):
        _standard_project(tmp_path)
        payload = json.dumps({"tool_name": "Bash", "tool_input": {"command": "ls"}})
        rc, out, err = _run(["--hook"], cwd=tmp_path, stdin_text=payload)
        assert rc == 0
        assert out.strip() == ""


# ---------------------------------------------------------------------------
# Performance smoke
# ---------------------------------------------------------------------------

class TestPerformance:

    def test_fifty_adrs_under_budget(self, tmp_path):
        adr_dir = _make_project(tmp_path)
        for i in range(1, 51):
            _write_adr(
                adr_dir, f"ADR-{i:03d}-generated.md",
                ADR_WITH_GLOB.format(glob=f"src/area{i}/**/*.py")
                .replace("ADR-001", f"ADR-{i:03d}"),
            )
        start = time.perf_counter()
        lines = _mod.run_watch(["src/area25/db/queries.py"], adr_dir)
        elapsed = time.perf_counter() - start
        assert any("ADR-025" in line for line in lines)
        # Target is <100ms; CI budget is generous (2s) to absorb slow runners.
        assert elapsed < 2.0, f"run_watch took {elapsed:.3f}s for 50 ADRs"


# ---------------------------------------------------------------------------
# Edit-tier injector (--pre-edit, ADR-004)
# ---------------------------------------------------------------------------

# A long Decision so the token-budget truncation path is exercised.
ADR_LONG_DECISION = """# ADR-001 No direct database calls outside the repository layer

## Status

Accepted, 2026-01-15.

## Context

Direct SQL in handlers caused tight coupling.

## Decision

All database access goes through the repository layer. """ + ("blah " * 400) + """

## Enforcement

```json
{"forbid_pattern": [{"pattern": "cursor", "path_glob": "src/**/*.py"}]}
```
"""


def _preedit_payload(file_path: str) -> str:
    return json.dumps({"tool_name": "Edit", "tool_input": {"file_path": file_path}})


class TestPreEditInject:

    def test_injects_decision_before_edit_on_glob_match(self, tmp_path):
        _standard_project(tmp_path)
        rc, out, err = _run(
            ["--pre-edit"], cwd=tmp_path,
            env_extra={"CLAUDE_PLUGIN_ROOT": "x"},
            stdin_text=_preedit_payload("src/db/queries.py"),
        )
        assert rc == 0
        payload = json.loads(out)
        ctx = payload["hookSpecificOutput"]["additionalContext"]
        assert payload["hookSpecificOutput"]["hookEventName"] == "PreToolUse"
        assert "[adr-inject] ADR-001" in ctx
        # It carries the Decision text, not just the ADR name.
        assert "repository layer" in ctx

    def test_glob_match_wins_over_keyword(self, tmp_path):
        # ADR-001 governs src/**/*.py by glob; ADR-002 is keyword-only on auth.
        _standard_project(tmp_path)
        rc, out, _ = _run(
            ["--pre-edit"], cwd=tmp_path,
            env_extra={"CLAUDE_PLUGIN_ROOT": "x"},
            stdin_text=_preedit_payload("src/auth/session.py"),
        )
        assert rc == 0
        ctx = json.loads(out)["hookSpecificOutput"]["additionalContext"]
        assert "ADR-001" in ctx  # the glob hit outranks the keyword hit

    def test_no_injection_for_non_matching_path(self, tmp_path):
        _standard_project(tmp_path)
        rc, out, _ = _run(
            ["--pre-edit"], cwd=tmp_path,
            stdin_text=_preedit_payload("assets/logo.svg"),
        )
        assert rc == 0
        assert out.strip() == ""

    def test_decision_truncated_to_token_budget(self, tmp_path):
        adr_dir = _make_project(tmp_path)
        _write_adr(adr_dir, "ADR-001-repo.md", ADR_LONG_DECISION)
        (adr_dir / ".adr-kit.json").write_text(
            json.dumps({"inject": {"max_tokens": 50}}), encoding="utf-8")
        rc, out, _ = _run(
            ["--pre-edit"], cwd=tmp_path,
            env_extra={"CLAUDE_PLUGIN_ROOT": "x"},
            stdin_text=_preedit_payload("src/db/queries.py"),
        )
        assert rc == 0
        ctx = json.loads(out)["hookSpecificOutput"]["additionalContext"]
        assert "[…]" in ctx  # truncation marker present
        # 50 tokens ~ 200 chars budget; the whole envelope stays well under the
        # untruncated ~2000-char decision.
        assert len(ctx) < 700

    def test_cooldown_suppresses_second_injection(self, tmp_path):
        adr_dir = _standard_project(tmp_path)
        rc1, out1, _ = _run(
            ["--pre-edit"], cwd=tmp_path,
            env_extra={"CLAUDE_PLUGIN_ROOT": "x"},
            stdin_text=_preedit_payload("src/db/queries.py"),
        )
        assert "ADR-001" in out1
        rc2, out2, _ = _run(
            ["--pre-edit"], cwd=tmp_path,
            env_extra={"CLAUDE_PLUGIN_ROOT": "x"},
            stdin_text=_preedit_payload("src/db/queries.py"),
        )
        assert rc2 == 0
        assert out2.strip() == ""
        # Cooldown recorded under the separate "inject" key, not "watch".
        state = json.loads(
            (adr_dir / ".adr-kit-state.json").read_text(encoding="utf-8"))
        assert "inject" in state
        assert any(k.startswith("ADR-001|") for k in state["inject"]["nudges"])

    def test_disabled_via_config(self, tmp_path):
        adr_dir = _standard_project(tmp_path)
        (adr_dir / ".adr-kit.json").write_text(
            json.dumps({"inject": {"enabled": False}}), encoding="utf-8")
        rc, out, _ = _run(
            ["--pre-edit"], cwd=tmp_path,
            stdin_text=_preedit_payload("src/db/queries.py"),
        )
        assert rc == 0
        assert out.strip() == ""

    def test_malformed_payload_exits_zero(self, tmp_path):
        _standard_project(tmp_path)
        rc, out, _ = _run(["--pre-edit"], cwd=tmp_path, stdin_text="not json")
        assert rc == 0
        assert out.strip() == ""

    def test_self_guard_no_adr_dir(self, tmp_path):
        rc, out, _ = _run(
            ["--pre-edit"], cwd=tmp_path,
            stdin_text=_preedit_payload("src/db/queries.py"),
        )
        assert rc == 0
        assert out.strip() == ""
