"""Tests for bin/adr-guardian — the periodic ADR-set staleness detector.

Design invariants under test:
  - check: always exits 0 (SessionStart must never fail)
  - check: silent (no stdout) when nothing is due
  - check: cwd-guard — silent when no docs/adr/ with ADRs present
  - check: nudge_cooldown_hours throttle — silent within cooldown window
  - check: cheap-tier and llm-tier due/not-due logic across two clocks
  - check: change-based retire nudge (candidate set changes → DUE; same → quiet)
  - stamp: updates .adr-kit-state.json for the named tier
  - state: prints current state JSON; always exits 0

Strategy:
  - Write state + config files into tmp directories.
  - Invoke adr-guardian via subprocess (same pattern as test_adr_suggest.py and
    test_adr_judge_llm.py).
  - Assert exit codes and stdout/stderr content.
  - No LLM is invoked — the guardian bin is stdlib-only.
"""
from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
ADR_GUARDIAN = REPO_ROOT / "bin" / "adr-guardian"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _run(args: list, cwd=None, env_extra=None) -> tuple[int, str, str]:
    """Run adr-guardian with given args; return (returncode, stdout, stderr)."""
    import os
    env = os.environ.copy()
    # Remove CLAUDE_PROJECT_DIR so tests don't accidentally pick up the repo's
    # own docs/adr/ when running inside an adr-kit checkout.
    env.pop("CLAUDE_PROJECT_DIR", None)
    if env_extra:
        env.update(env_extra)
    result = subprocess.run(
        [sys.executable, str(ADR_GUARDIAN)] + args,
        capture_output=True,
        text=True,
        encoding="utf-8",
        cwd=cwd or str(Path.cwd()),
        env=env,
    )
    return result.returncode, result.stdout, result.stderr


def _make_adr_dir(tmp_path: Path, num_adrs: int = 1) -> Path:
    """Create a minimal docs/adr/ directory with the requested number of stub ADR files."""
    adr_dir = tmp_path / "docs" / "adr"
    adr_dir.mkdir(parents=True)
    for i in range(1, num_adrs + 1):
        (adr_dir / f"ADR-{i:03d}-stub.md").write_text(
            f"# ADR-{i:03d} Stub\n\n## Status\n\nAccepted\n",
            encoding="utf-8",
        )
    return adr_dir


def _write_state(adr_dir: Path, state: dict) -> None:
    (adr_dir / ".adr-kit-state.json").write_text(
        json.dumps(state, indent=2) + "\n", encoding="utf-8"
    )


def _write_config(adr_dir: Path, guardian_cfg: dict) -> None:
    (adr_dir / ".adr-kit.json").write_text(
        json.dumps({"guardian": guardian_cfg}), encoding="utf-8"
    )


def _iso(dt: datetime) -> str:
    return dt.isoformat()


def _now() -> datetime:
    return datetime.now(tz=timezone.utc)


def _days_ago(n: float) -> str:
    return _iso(_now() - timedelta(days=n))


def _hours_ago(n: float) -> str:
    return _iso(_now() - timedelta(hours=n))


# ---------------------------------------------------------------------------
# cwd-guard tests
# ---------------------------------------------------------------------------

class TestCwdGuard:
    """The binary must exit 0 silently when there is no docs/adr/ with ADRs."""

    def test_no_docs_adr_dir(self, tmp_path):
        """Completely empty directory: exit 0, no stdout."""
        rc, out, err = _run(["check"], cwd=str(tmp_path))
        assert rc == 0
        assert out.strip() == ""

    def test_docs_adr_dir_exists_but_empty(self, tmp_path):
        """docs/adr/ exists but has no ADR-*.md files."""
        (tmp_path / "docs" / "adr").mkdir(parents=True)
        rc, out, err = _run(["check"], cwd=str(tmp_path))
        assert rc == 0
        assert out.strip() == ""

    def test_with_adrs_but_guardian_disabled(self, tmp_path):
        """docs/adr/ has ADRs but guardian is disabled in config."""
        adr_dir = _make_adr_dir(tmp_path)
        _write_config(adr_dir, {"enabled": False})
        # State is never run, so tiers are due — but disabled guardian stays silent.
        rc, out, err = _run(["check"], cwd=str(tmp_path))
        assert rc == 0
        assert out.strip() == ""


# ---------------------------------------------------------------------------
# Due / not-due logic
# ---------------------------------------------------------------------------

class TestDueTiers:
    """Tier clocks: cheap daily, LLM bi-weekly."""

    def test_both_tiers_due_when_never_run(self, tmp_path):
        """Both tiers due when last_run is None (first session ever)."""
        adr_dir = _make_adr_dir(tmp_path)
        # No state file → defaults to None last_run for both tiers.
        rc, out, err = _run(["check"], cwd=str(tmp_path))
        assert rc == 0
        assert "[adr-guardian]" in out
        assert "DUE" in out

    def test_cheap_tier_due_after_drift_stale_days(self, tmp_path):
        """cheap tier is due when last_run is > drift_stale_days ago."""
        adr_dir = _make_adr_dir(tmp_path)
        state = {
            "cheap_tier": {"last_run": _days_ago(2), "drift_violations": 0,
                           "retire_candidates": 0, "lint": "0F/0A"},
            "llm_tier": {"last_run": _days_ago(1), "suggest_hits": 0, "audit_findings": 0},
            "retire_seen": [],
            "last_nudged": None,
        }
        _write_state(adr_dir, state)
        _write_config(adr_dir, {"drift_stale_days": 1, "llm_stale_days": 14})
        rc, out, err = _run(["check"], cwd=str(tmp_path))
        assert rc == 0
        assert "DUE" in out  # cheap tier is due

    def test_cheap_tier_not_due_when_fresh(self, tmp_path):
        """cheap tier is NOT due when last_run is < drift_stale_days ago."""
        adr_dir = _make_adr_dir(tmp_path)
        state = {
            "cheap_tier": {"last_run": _hours_ago(6), "drift_violations": 0,
                           "retire_candidates": 0, "lint": "0F/0A"},
            "llm_tier": {"last_run": _hours_ago(6), "suggest_hits": 0, "audit_findings": 0},
            "retire_seen": [],
            "last_nudged": None,
        }
        _write_state(adr_dir, state)
        # drift_stale_days=1 (24h) — 6h ago is NOT stale; llm_stale_days=14 — also not stale.
        _write_config(adr_dir, {"drift_stale_days": 1, "llm_stale_days": 14})
        rc, out, err = _run(["check"], cwd=str(tmp_path))
        assert rc == 0
        assert out.strip() == ""  # nothing due → no output

    def test_llm_tier_due_after_llm_stale_days(self, tmp_path):
        """llm tier is due when last_run is > llm_stale_days ago; cheap is not due."""
        adr_dir = _make_adr_dir(tmp_path)
        state = {
            "cheap_tier": {"last_run": _hours_ago(6), "drift_violations": 0,
                           "retire_candidates": 0, "lint": "0F/0A"},
            "llm_tier": {"last_run": _days_ago(20), "suggest_hits": 0, "audit_findings": 0},
            "retire_seen": [],
            "last_nudged": None,
        }
        _write_state(adr_dir, state)
        _write_config(adr_dir, {"drift_stale_days": 1, "llm_stale_days": 14})
        rc, out, err = _run(["check"], cwd=str(tmp_path))
        assert rc == 0
        # llm tier is due
        assert "[adr-guardian]" in out
        assert "llm-tier" in out
        assert "DUE" in out
        assert "costs $" in out  # LLM cost annotation

    def test_neither_tier_due_when_both_fresh(self, tmp_path):
        """Both tiers recently run: no output."""
        adr_dir = _make_adr_dir(tmp_path)
        state = {
            "cheap_tier": {"last_run": _hours_ago(12), "drift_violations": 0,
                           "retire_candidates": 0, "lint": "0F/0A"},
            "llm_tier": {"last_run": _days_ago(5), "suggest_hits": 0, "audit_findings": 0},
            "retire_seen": [],
            "last_nudged": None,
        }
        _write_state(adr_dir, state)
        _write_config(adr_dir, {"drift_stale_days": 1, "llm_stale_days": 14})
        rc, out, err = _run(["check"], cwd=str(tmp_path))
        assert rc == 0
        assert out.strip() == ""


# ---------------------------------------------------------------------------
# Nudge cooldown throttle
# ---------------------------------------------------------------------------

class TestNudgeCooldown:
    """nudge_cooldown_hours prevents repeated nags within a session window."""

    def test_suppressed_within_cooldown(self, tmp_path):
        """If last_nudged is within cooldown window, output is suppressed even when DUE."""
        adr_dir = _make_adr_dir(tmp_path)
        state = {
            "cheap_tier": {"last_run": None, "drift_violations": 0,
                           "retire_candidates": 0, "lint": "0F/0A"},
            "llm_tier": {"last_run": None, "suggest_hits": 0, "audit_findings": 0},
            "retire_seen": [],
            "last_nudged": _hours_ago(2),  # 2h ago, cooldown=24h
        }
        _write_state(adr_dir, state)
        _write_config(adr_dir, {"nudge_cooldown_hours": 24})
        rc, out, err = _run(["check"], cwd=str(tmp_path))
        assert rc == 0
        assert out.strip() == ""  # throttled

    def test_not_suppressed_after_cooldown(self, tmp_path):
        """last_nudged > cooldown_hours ago: nudge fires."""
        adr_dir = _make_adr_dir(tmp_path)
        state = {
            "cheap_tier": {"last_run": None, "drift_violations": 0,
                           "retire_candidates": 0, "lint": "0F/0A"},
            "llm_tier": {"last_run": None, "suggest_hits": 0, "audit_findings": 0},
            "retire_seen": [],
            "last_nudged": _hours_ago(25),  # 25h ago, cooldown=24h
        }
        _write_state(adr_dir, state)
        _write_config(adr_dir, {"nudge_cooldown_hours": 24})
        rc, out, err = _run(["check"], cwd=str(tmp_path))
        assert rc == 0
        assert "[adr-guardian]" in out

    def test_zero_cooldown_always_nudges(self, tmp_path):
        """cooldown_hours=0 means always nudge when due."""
        adr_dir = _make_adr_dir(tmp_path)
        state = {
            "cheap_tier": {"last_run": None, "drift_violations": 0,
                           "retire_candidates": 0, "lint": "0F/0A"},
            "llm_tier": {"last_run": None, "suggest_hits": 0, "audit_findings": 0},
            "retire_seen": [],
            "last_nudged": _hours_ago(0.1),  # very recent nudge
        }
        _write_state(adr_dir, state)
        _write_config(adr_dir, {"nudge_cooldown_hours": 0})
        rc, out, err = _run(["check"], cwd=str(tmp_path))
        assert rc == 0
        assert "[adr-guardian]" in out


# ---------------------------------------------------------------------------
# Change-based retire nudge
# ---------------------------------------------------------------------------

class TestRetireNudge:
    """Retire detection: the detector surfaces retire_candidates count from last stamp.

    The change-based retire nudge logic (nudge only when candidate set changes vs
    retire_seen) lives in the /adr-kit:guardian skill, not in the detector binary.
    The skill: runs adr-retire, diffs fresh candidates against state.retire_seen,
    highlights only the new ones, then stamps the new seen set. The detector binary
    only reads what was stamped; it does not freshly compute candidates.
    """

    def test_retire_candidate_count_displayed_from_state(self, tmp_path):
        """The state line shows retire_candidates count from the stamped state.

        This tests what the detector actually does: read and display stored counts.
        The comparison (fresh candidates vs retire_seen) is the skill's job.
        """
        adr_dir = _make_adr_dir(tmp_path, num_adrs=2)
        state = {
            "cheap_tier": {"last_run": _days_ago(2), "drift_violations": 0,
                           "retire_candidates": 1, "lint": "0F/0A"},
            "llm_tier": {"last_run": _days_ago(1), "suggest_hits": 0, "audit_findings": 0},
            "retire_seen": [],
            "last_nudged": None,
        }
        _write_state(adr_dir, state)
        _write_config(adr_dir, {"drift_stale_days": 1, "llm_stale_days": 14})
        rc, out, err = _run(["check"], cwd=str(tmp_path))
        assert rc == 0
        # cheap tier is due (2d > 1d threshold)
        assert "[adr-guardian]" in out
        assert "retire candidates" in out

    def test_retire_candidate_count_in_state_block(self, tmp_path):
        """The state line shows retire_candidates count from stored state."""
        adr_dir = _make_adr_dir(tmp_path)
        state = {
            "cheap_tier": {"last_run": None, "drift_violations": 3,
                           "retire_candidates": 2, "lint": "1F/2A"},
            "llm_tier": {"last_run": None, "suggest_hits": 1, "audit_findings": 4},
            "retire_seen": ["ADR-001"],
            "last_nudged": None,
        }
        _write_state(adr_dir, state)
        rc, out, err = _run(["check"], cwd=str(tmp_path))
        assert rc == 0
        assert "2 retire candidates" in out
        assert "3 drift" in out
        assert "1 suggestion" in out


# ---------------------------------------------------------------------------
# Stamp subcommand
# ---------------------------------------------------------------------------

class TestStamp:
    """stamp updates .adr-kit-state.json for the named tier."""

    def test_stamp_cheap_tier(self, tmp_path):
        """stamp cheap sets last_run and the provided metrics."""
        adr_dir = _make_adr_dir(tmp_path)
        rc, out, err = _run(
            ["stamp", "cheap",
             "--violations", "2",
             "--retire", "1",
             "--lint", "2F/3A",
             "--state-dir", str(adr_dir)],
            cwd=str(tmp_path),
        )
        assert rc == 0
        state_path = adr_dir / ".adr-kit-state.json"
        assert state_path.exists()
        state = json.loads(state_path.read_text(encoding="utf-8"))
        cheap = state["cheap_tier"]
        assert cheap["last_run"] is not None
        assert cheap["drift_violations"] == 2
        assert cheap["retire_candidates"] == 1
        assert cheap["lint"] == "2F/3A"

    def test_stamp_llm_tier(self, tmp_path):
        """stamp llm sets last_run and suggest/audit counts."""
        adr_dir = _make_adr_dir(tmp_path)
        rc, out, err = _run(
            ["stamp", "llm",
             "--suggest", "3",
             "--audit", "5",
             "--state-dir", str(adr_dir)],
            cwd=str(tmp_path),
        )
        assert rc == 0
        state = json.loads((adr_dir / ".adr-kit-state.json").read_text(encoding="utf-8"))
        llm = state["llm_tier"]
        assert llm["last_run"] is not None
        assert llm["suggest_hits"] == 3
        assert llm["audit_findings"] == 5

    def test_stamp_preserves_other_tier(self, tmp_path):
        """Stamping one tier does not clobber the other tier."""
        adr_dir = _make_adr_dir(tmp_path)
        initial_state = {
            "cheap_tier": {"last_run": _days_ago(3), "drift_violations": 5,
                           "retire_candidates": 2, "lint": "5F/0A"},
            "llm_tier": {"last_run": _days_ago(10), "suggest_hits": 7, "audit_findings": 3},
            "retire_seen": ["ADR-007"],
            "last_nudged": None,
        }
        _write_state(adr_dir, initial_state)
        # Stamp only the cheap tier.
        _run(["stamp", "cheap", "--violations", "0", "--state-dir", str(adr_dir)],
             cwd=str(tmp_path))
        state = json.loads((adr_dir / ".adr-kit-state.json").read_text(encoding="utf-8"))
        # cheap tier updated
        assert state["cheap_tier"]["drift_violations"] == 0
        # llm tier preserved
        assert state["llm_tier"]["suggest_hits"] == 7
        assert state["retire_seen"] == ["ADR-007"]

    def test_stamp_retire_seen(self, tmp_path):
        """stamp cheap with --retire-seen updates the retire_seen list."""
        adr_dir = _make_adr_dir(tmp_path)
        rc, out, err = _run(
            ["stamp", "cheap",
             "--retire-seen", '["ADR-003", "ADR-012"]',
             "--state-dir", str(adr_dir)],
            cwd=str(tmp_path),
        )
        assert rc == 0
        state = json.loads((adr_dir / ".adr-kit-state.json").read_text(encoding="utf-8"))
        assert state["retire_seen"] == ["ADR-003", "ADR-012"]

    def test_stamp_always_exits_0(self, tmp_path):
        """stamp exits 0 even with bad state dir (gracefully degrades)."""
        bad_dir = tmp_path / "nonexistent" / "deep"
        rc, out, err = _run(
            ["stamp", "cheap", "--violations", "1", "--state-dir", str(bad_dir)],
        )
        # May succeed (creating dirs) or degrade silently — must not raise.
        assert rc == 0


# ---------------------------------------------------------------------------
# State subcommand
# ---------------------------------------------------------------------------

class TestStateCmd:
    """state prints current JSON state."""

    def test_state_no_file(self, tmp_path):
        """state with no state file prints default state JSON."""
        adr_dir = _make_adr_dir(tmp_path)
        rc, out, err = _run(["state", "--state-dir", str(adr_dir)], cwd=str(tmp_path))
        assert rc == 0
        data = json.loads(out)
        assert "cheap_tier" in data
        assert "llm_tier" in data

    def test_state_with_file(self, tmp_path):
        """state reads and prints existing state file."""
        adr_dir = _make_adr_dir(tmp_path)
        state = {
            "cheap_tier": {"last_run": _days_ago(2), "drift_violations": 1,
                           "retire_candidates": 0, "lint": "1F/0A"},
            "llm_tier": {"last_run": _days_ago(10), "suggest_hits": 2, "audit_findings": 0},
            "retire_seen": [],
            "last_nudged": None,
        }
        _write_state(adr_dir, state)
        rc, out, err = _run(["state", "--state-dir", str(adr_dir)], cwd=str(tmp_path))
        assert rc == 0
        data = json.loads(out)
        assert data["cheap_tier"]["drift_violations"] == 1
        assert data["llm_tier"]["suggest_hits"] == 2


# ---------------------------------------------------------------------------
# Always-exit-0 invariant
# ---------------------------------------------------------------------------

class TestAlwaysExit0:
    """The check subcommand must NEVER return non-zero under any circumstances."""

    def test_check_with_corrupt_state(self, tmp_path):
        """check exits 0 even if state file is corrupt JSON."""
        adr_dir = _make_adr_dir(tmp_path)
        (adr_dir / ".adr-kit-state.json").write_text("{not valid json", encoding="utf-8")
        rc, out, err = _run(["check"], cwd=str(tmp_path))
        assert rc == 0

    def test_check_with_corrupt_config(self, tmp_path):
        """check exits 0 even if config file is corrupt JSON."""
        adr_dir = _make_adr_dir(tmp_path)
        (adr_dir / ".adr-kit.json").write_text("{broken", encoding="utf-8")
        rc, out, err = _run(["check"], cwd=str(tmp_path))
        assert rc == 0

    def test_check_empty_project_dir(self, tmp_path):
        """check exits 0 for a completely empty cwd."""
        rc, out, err = _run(["check"], cwd=str(tmp_path))
        assert rc == 0

    def test_stamp_always_exits_0_corrupt_json(self, tmp_path):
        """stamp exits 0 even when existing state is corrupt."""
        adr_dir = _make_adr_dir(tmp_path)
        (adr_dir / ".adr-kit-state.json").write_text("garbage", encoding="utf-8")
        rc, out, err = _run(
            ["stamp", "cheap", "--violations", "1", "--state-dir", str(adr_dir)],
            cwd=str(tmp_path),
        )
        assert rc == 0


# ---------------------------------------------------------------------------
# Output format
# ---------------------------------------------------------------------------

class TestOutputFormat:
    """Verify the [adr-guardian] block content and JSON envelope."""

    def test_block_mentions_slash_command(self, tmp_path):
        """The block always advertises /adr-kit:guardian."""
        adr_dir = _make_adr_dir(tmp_path, num_adrs=5)
        rc, out, err = _run(["check"], cwd=str(tmp_path))
        assert rc == 0
        assert "/adr-kit:guardian" in out

    def test_block_is_json_envelope(self, tmp_path):
        """Output is a JSON object wrapping the block in additionalContext."""
        adr_dir = _make_adr_dir(tmp_path)
        rc, out, err = _run(
            ["check"],
            cwd=str(tmp_path),
            # No CLAUDE_PLUGIN_ROOT → use top-level additionalContext format.
            env_extra={"CLAUDE_PLUGIN_ROOT": "", "COPILOT_CLI": ""},
        )
        assert rc == 0
        if out.strip():  # may be empty if cooldown or not-due
            data = json.loads(out)
            assert data["suppressOutput"] is True
            assert "additionalContext" in data or "hookSpecificOutput" in data

    def test_claude_code_envelope(self, tmp_path):
        """With CLAUDE_PLUGIN_ROOT set (no COPILOT_CLI), uses hookSpecificOutput format."""
        adr_dir = _make_adr_dir(tmp_path)
        rc, out, err = _run(
            ["check"],
            cwd=str(tmp_path),
            env_extra={"CLAUDE_PLUGIN_ROOT": "/some/plugin/path", "COPILOT_CLI": ""},
        )
        assert rc == 0
        if out.strip():
            data = json.loads(out)
            assert data["suppressOutput"] is True
            assert "hookSpecificOutput" in data
            assert data["hookSpecificOutput"]["hookEventName"] == "SessionStart"
            assert "additionalContext" in data["hookSpecificOutput"]

    def test_adr_count_in_block(self, tmp_path):
        """The state line includes the ADR count from the directory."""
        adr_dir = _make_adr_dir(tmp_path, num_adrs=7)
        rc, out, err = _run(["check"], cwd=str(tmp_path))
        assert rc == 0
        if out.strip():
            assert "7 ADRs" in out

    def test_check_writes_last_nudged(self, tmp_path):
        """After a nudge is emitted, last_nudged is updated in the state file."""
        adr_dir = _make_adr_dir(tmp_path)
        state_path = adr_dir / ".adr-kit-state.json"
        initial = {
            "cheap_tier": {"last_run": None, "drift_violations": 0,
                           "retire_candidates": 0, "lint": "0F/0A"},
            "llm_tier": {"last_run": None, "suggest_hits": 0, "audit_findings": 0},
            "retire_seen": [],
            "last_nudged": None,
        }
        _write_state(adr_dir, initial)
        rc, out, err = _run(["check"], cwd=str(tmp_path))
        assert rc == 0
        assert "[adr-guardian]" in out
        # last_nudged should now be set.
        state = json.loads(state_path.read_text(encoding="utf-8"))
        assert state["last_nudged"] is not None


# ---------------------------------------------------------------------------
# Trend history (task-4)
# ---------------------------------------------------------------------------

def _trend_entry(date_str, tier="cheap", drift=0, retire=0, suggest=0, audit=0,
                 coverage=None, total=1):
    return {
        "date": date_str,
        "tier": tier,
        "total_adrs": total,
        "drift_violations": drift,
        "retire_candidates": retire,
        "suggest_hits": suggest,
        "audit_findings": audit,
        "coverage_percent": coverage,
    }


class TestTrendStamp:
    """stamp appends an entry to the append-only trend list."""

    def test_stamp_appends_trend_entry(self, tmp_path):
        adr_dir = _make_adr_dir(tmp_path, num_adrs=3)
        rc, out, err = _run(
            ["stamp", "cheap",
             "--violations", "2",
             "--retire", "1",
             "--coverage", "40.0",
             "--state-dir", str(adr_dir)],
            cwd=str(tmp_path),
        )
        assert rc == 0
        state = json.loads((adr_dir / ".adr-kit-state.json").read_text(encoding="utf-8"))
        trend = state["trend"]
        assert len(trend) == 1
        entry = trend[0]
        assert entry["tier"] == "cheap"
        assert entry["date"] is not None
        assert entry["total_adrs"] == 3
        assert entry["drift_violations"] == 2
        assert entry["retire_candidates"] == 1
        assert entry["coverage_percent"] == 40.0
        # llm-tier fields carried from last known values (DEFAULT_STATE = 0).
        assert entry["suggest_hits"] == 0
        assert entry["audit_findings"] == 0

    def test_two_stamps_record_two_entries(self, tmp_path):
        """Running the guardian twice records a delta-able trend."""
        adr_dir = _make_adr_dir(tmp_path)
        _run(["stamp", "cheap", "--violations", "2", "--coverage", "40",
              "--state-dir", str(adr_dir)], cwd=str(tmp_path))
        _run(["stamp", "cheap", "--violations", "0", "--coverage", "45",
              "--state-dir", str(adr_dir)], cwd=str(tmp_path))
        state = json.loads((adr_dir / ".adr-kit-state.json").read_text(encoding="utf-8"))
        trend = state["trend"]
        assert len(trend) == 2
        assert trend[0]["drift_violations"] == 2
        assert trend[1]["drift_violations"] == 0
        assert trend[1]["coverage_percent"] == 45.0

    def test_llm_stamp_carries_cheap_fields(self, tmp_path):
        """Stamping llm carries last known cheap-tier counts and coverage."""
        adr_dir = _make_adr_dir(tmp_path)
        _run(["stamp", "cheap", "--violations", "3", "--retire", "2",
              "--coverage", "33.3", "--state-dir", str(adr_dir)], cwd=str(tmp_path))
        _run(["stamp", "llm", "--suggest", "4", "--audit", "1",
              "--state-dir", str(adr_dir)], cwd=str(tmp_path))
        state = json.loads((adr_dir / ".adr-kit-state.json").read_text(encoding="utf-8"))
        entry = state["trend"][-1]
        assert entry["tier"] == "llm"
        assert entry["suggest_hits"] == 4
        assert entry["audit_findings"] == 1
        # carried from previous sweep / tier state
        assert entry["drift_violations"] == 3
        assert entry["retire_candidates"] == 2
        assert entry["coverage_percent"] == 33.3

    def test_trend_capped_at_52(self, tmp_path):
        """The trend list never exceeds 52 entries; oldest are dropped."""
        adr_dir = _make_adr_dir(tmp_path)
        state = {
            "cheap_tier": {"last_run": _days_ago(2), "drift_violations": 0,
                           "retire_candidates": 0, "lint": "0F/0A"},
            "llm_tier": {"last_run": None, "suggest_hits": 0, "audit_findings": 0},
            "retire_seen": [],
            "last_nudged": None,
            "trend": [_trend_entry(_days_ago(60 - i), drift=i) for i in range(60)],
        }
        _write_state(adr_dir, state)
        rc, out, err = _run(
            ["stamp", "cheap", "--violations", "9", "--state-dir", str(adr_dir)],
            cwd=str(tmp_path),
        )
        assert rc == 0
        new_state = json.loads((adr_dir / ".adr-kit-state.json").read_text(encoding="utf-8"))
        trend = new_state["trend"]
        assert len(trend) == 52
        # Newest entry is the one we just stamped.
        assert trend[-1]["drift_violations"] == 9
        # Oldest entries were dropped (entry with drift=0..8 gone, drift=9.. remain
        # before the new one).
        assert trend[0]["drift_violations"] == 9

    def test_corrupt_trend_tolerated(self, tmp_path):
        """A corrupt trend value (not a list) is reset; stamp still exits 0."""
        adr_dir = _make_adr_dir(tmp_path)
        state = {
            "cheap_tier": {"last_run": None, "drift_violations": 0,
                           "retire_candidates": 0, "lint": "0F/0A"},
            "llm_tier": {"last_run": None, "suggest_hits": 0, "audit_findings": 0},
            "retire_seen": [],
            "last_nudged": None,
            "trend": "this is not a list",
        }
        _write_state(adr_dir, state)
        rc, out, err = _run(
            ["stamp", "cheap", "--violations", "1", "--state-dir", str(adr_dir)],
            cwd=str(tmp_path),
        )
        assert rc == 0
        new_state = json.loads((adr_dir / ".adr-kit-state.json").read_text(encoding="utf-8"))
        assert isinstance(new_state["trend"], list)
        assert len(new_state["trend"]) == 1

    def test_default_state_includes_trend(self, tmp_path):
        """adr-guardian state with no file shows the trend key in defaults."""
        adr_dir = _make_adr_dir(tmp_path)
        rc, out, err = _run(["state", "--state-dir", str(adr_dir)], cwd=str(tmp_path))
        assert rc == 0
        data = json.loads(out)
        assert data["trend"] == []


class TestTrendDelta:
    """check emits a one-line delta vs the previous sweep when trend data exists."""

    def _base_state(self, trend):
        return {
            "cheap_tier": {"last_run": _days_ago(2), "drift_violations": 0,
                           "retire_candidates": 2, "lint": "0F/0A"},
            "llm_tier": {"last_run": _days_ago(1), "suggest_hits": 0, "audit_findings": 0},
            "retire_seen": [],
            "last_nudged": None,
            "trend": trend,
        }

    def test_delta_line_with_trend(self, tmp_path):
        adr_dir = _make_adr_dir(tmp_path)
        trend = [
            _trend_entry(_days_ago(9), drift=2, retire=1, coverage=40.0),
            _trend_entry(_days_ago(2), drift=0, retire=2, coverage=45.0),
        ]
        _write_state(adr_dir, self._base_state(trend))
        _write_config(adr_dir, {"drift_stale_days": 1, "llm_stale_days": 14})
        rc, out, err = _run(["check"], cwd=str(tmp_path))
        assert rc == 0
        assert "[adr-guardian]" in out
        assert "trend: " in out
        assert "drift 2 -> 0" in out
        assert "retire 1 -> 2" in out
        assert "coverage 40% -> 45%" in out

    def test_no_delta_line_without_trend(self, tmp_path):
        adr_dir = _make_adr_dir(tmp_path)
        _write_state(adr_dir, self._base_state([]))
        _write_config(adr_dir, {"drift_stale_days": 1, "llm_stale_days": 14})
        rc, out, err = _run(["check"], cwd=str(tmp_path))
        assert rc == 0
        assert "[adr-guardian]" in out
        assert "trend: " not in out

    def test_no_delta_line_with_single_entry(self, tmp_path):
        """One trend entry has no previous sweep to delta against."""
        adr_dir = _make_adr_dir(tmp_path)
        trend = [_trend_entry(_days_ago(2), drift=1)]
        _write_state(adr_dir, self._base_state(trend))
        _write_config(adr_dir, {"drift_stale_days": 1, "llm_stale_days": 14})
        rc, out, err = _run(["check"], cwd=str(tmp_path))
        assert rc == 0
        assert "[adr-guardian]" in out
        assert "trend: " not in out

    def test_corrupt_trend_entries_tolerated_by_check(self, tmp_path):
        """Non-dict trend entries do not break check; no delta line, exit 0."""
        adr_dir = _make_adr_dir(tmp_path)
        _write_state(adr_dir, self._base_state(["garbage", 42]))
        _write_config(adr_dir, {"drift_stale_days": 1, "llm_stale_days": 14})
        rc, out, err = _run(["check"], cwd=str(tmp_path))
        assert rc == 0
        assert "[adr-guardian]" in out
        assert "trend: " not in out


# ---------------------------------------------------------------------------
# Per-ADR verdict stamps (ADR-037)
# ---------------------------------------------------------------------------

class TestPerAdrStamp:
    """ADR-037: llm_tier.adrs records one verdict per ADR, advisory and
    per-machine, so an interrupted sweep keeps what it established and a
    recorded violation holds the tier open until a re-judge clears it."""

    def test_adr_stamp_writes_entry_without_tier_timestamp_or_trend(self, tmp_path):
        adr_dir = _make_adr_dir(tmp_path, num_adrs=2)
        rc, out, err = _run(
            ["stamp", "llm", "--adr", "ADR-001", "--verdict", "violation",
             "--state-dir", str(adr_dir)],
            cwd=str(tmp_path),
        )
        assert rc == 0, err
        state = json.loads((adr_dir / ".adr-kit-state.json").read_text(encoding="utf-8"))
        llm = state["llm_tier"]
        assert llm["adrs"]["ADR-001"]["verdict"] == "violation"
        assert llm["adrs"]["ADR-001"]["last_run"] is not None
        # The tier timestamp means "a completed sweep"; one verdict is not that.
        assert llm["last_run"] is None
        assert state.get("trend", []) == []

    def test_recorded_violation_keeps_llm_tier_due(self, tmp_path):
        """A fresh tier timestamp does not silence a recorded violation."""
        adr_dir = _make_adr_dir(tmp_path, num_adrs=2)
        _write_config(adr_dir, {"llm_stale_days": 14, "drift_stale_days": 1})
        _write_state(adr_dir, {
            "cheap_tier": {"last_run": _hours_ago(1)},
            "llm_tier": {
                "last_run": _hours_ago(1),
                "adrs": {"ADR-002": {"last_run": _hours_ago(1),
                                     "verdict": "violation"}},
            },
        })
        rc, out, err = _run(["check"], cwd=str(tmp_path))
        assert rc == 0
        assert "DUE" in out
        assert "1 violation(s) outstanding" in out
        assert "ADR-002" in out

    def test_rejudge_ok_clears_the_violation_and_the_nudge(self, tmp_path):
        adr_dir = _make_adr_dir(tmp_path, num_adrs=2)
        _write_config(adr_dir, {"llm_stale_days": 14, "drift_stale_days": 1})
        _write_state(adr_dir, {
            "cheap_tier": {"last_run": _hours_ago(1)},
            "llm_tier": {
                "last_run": _hours_ago(1),
                "adrs": {"ADR-002": {"last_run": _hours_ago(2),
                                     "verdict": "violation"}},
            },
        })
        rc, _, err = _run(
            ["stamp", "llm", "--adr", "ADR-002", "--verdict", "ok",
             "--state-dir", str(adr_dir)],
            cwd=str(tmp_path),
        )
        assert rc == 0, err
        rc, out, _ = _run(["check"], cwd=str(tmp_path))
        assert rc == 0
        # Nothing due: both tiers fresh, no violation left. check prints nothing.
        assert out.strip() == ""

    def test_tier_stamp_preserves_the_per_adr_map(self, tmp_path):
        adr_dir = _make_adr_dir(tmp_path, num_adrs=2)
        _run(["stamp", "llm", "--adr", "ADR-001", "--verdict", "ok",
              "--state-dir", str(adr_dir)], cwd=str(tmp_path))
        rc, _, err = _run(
            ["stamp", "llm", "--suggest", "0", "--audit", "0",
             "--state-dir", str(adr_dir)],
            cwd=str(tmp_path),
        )
        assert rc == 0, err
        state = json.loads((adr_dir / ".adr-kit-state.json").read_text(encoding="utf-8"))
        assert state["llm_tier"]["adrs"]["ADR-001"]["verdict"] == "ok"
        assert state["llm_tier"]["last_run"] is not None

    def test_stamp_prunes_entries_for_deleted_adrs(self, tmp_path):
        adr_dir = _make_adr_dir(tmp_path, num_adrs=1)
        _write_state(adr_dir, {
            "llm_tier": {"adrs": {"ADR-099": {"last_run": _hours_ago(1),
                                              "verdict": "violation"}}},
        })
        rc, _, err = _run(
            ["stamp", "llm", "--adr", "ADR-001", "--verdict", "ok",
             "--state-dir", str(adr_dir)],
            cwd=str(tmp_path),
        )
        assert rc == 0, err
        state = json.loads((adr_dir / ".adr-kit-state.json").read_text(encoding="utf-8"))
        assert "ADR-099" not in state["llm_tier"]["adrs"]
        assert "ADR-001" in state["llm_tier"]["adrs"]

    def test_invalid_flag_combinations_are_refused(self, tmp_path):
        adr_dir = _make_adr_dir(tmp_path)
        cases = [
            ["stamp", "llm", "--adr", "ADR-001"],                      # no verdict
            ["stamp", "cheap", "--adr", "ADR-001", "--verdict", "ok"],  # wrong tier
            ["stamp", "llm", "--verdict", "ok"],                        # no adr
        ]
        for case in cases:
            rc, _, err = _run(case + ["--state-dir", str(adr_dir)], cwd=str(tmp_path))
            assert rc == 2, f"{case}: expected refusal, got rc={rc}"
            assert "ERROR" in err
        # A refused stamp must not have created state as a side effect.
        assert not (adr_dir / ".adr-kit-state.json").exists()

    def test_empty_adr_id_is_refused_not_a_tier_stamp(self, tmp_path):
        """An empty --adr is not None (passes the pairing check) and falsy
        (used to fall through to the TIER branch): it stamped a completed
        sweep. TASK-157 finding 1."""
        adr_dir = _make_adr_dir(tmp_path)
        rc, _, err = _run(
            ["stamp", "llm", "--adr", "", "--verdict", "ok",
             "--state-dir", str(adr_dir)],
            cwd=str(tmp_path),
        )
        assert rc == 2
        assert "ERROR" in err
        assert not (adr_dir / ".adr-kit-state.json").exists()

    def test_unresolvable_adr_id_is_refused_not_silently_pruned(self, tmp_path):
        """A typo (ADR-999) or unpadded id (ADR-1) used to be written and then
        pruned in the same transaction: exit 0, verdict silently lost
        TASK-157 finding 2."""
        adr_dir = _make_adr_dir(tmp_path, num_adrs=1)   # only ADR-001 exists
        for bad in ("ADR-999",):
            rc, _, err = _run(
                ["stamp", "llm", "--adr", bad, "--verdict", "violation",
                 "--state-dir", str(adr_dir)],
                cwd=str(tmp_path),
            )
            assert rc == 2, f"{bad}: expected refusal, got rc={rc}"
            assert bad in err
        assert not (adr_dir / ".adr-kit-state.json").exists()

    def test_prune_still_removes_entries_for_files_deleted_later(self, tmp_path):
        """The up-front validation must not defeat the prune: an entry whose
        ADR file is deleted AFTER its stamp still ages out on the next stamp."""
        adr_dir = _make_adr_dir(tmp_path, num_adrs=2)
        _run(["stamp", "llm", "--adr", "ADR-002", "--verdict", "ok",
              "--state-dir", str(adr_dir)], cwd=str(tmp_path))
        (adr_dir / "ADR-002-stub.md").unlink()
        rc, _, err = _run(
            ["stamp", "llm", "--adr", "ADR-001", "--verdict", "ok",
             "--state-dir", str(adr_dir)],
            cwd=str(tmp_path),
        )
        assert rc == 0, err
        state = json.loads((adr_dir / ".adr-kit-state.json").read_text(encoding="utf-8"))
        assert "ADR-002" not in state["llm_tier"]["adrs"]
        assert "ADR-001" in state["llm_tier"]["adrs"]

    def test_tier_flags_on_a_per_adr_stamp_are_refused(self, tmp_path):
        """TASK-159: the per-ADR branch returned before the tier writes, so
        --coverage etc. were accepted and silently dropped."""
        adr_dir = _make_adr_dir(tmp_path)
        rc, _, err = _run(
            ["stamp", "llm", "--adr", "ADR-001", "--verdict", "ok",
             "--coverage", "80", "--state-dir", str(adr_dir)],
            cwd=str(tmp_path),
        )
        assert rc == 2
        assert "--coverage" in err
        assert not (adr_dir / ".adr-kit-state.json").exists()

    def test_unpadded_id_normalizes_to_the_canonical_form(self, tmp_path):
        """TASK-161: the shared adr_catalog reader zero-pads, so ADR-1 resolves
        to the ADR-001 file instead of being refused over formatting."""
        adr_dir = _make_adr_dir(tmp_path, num_adrs=1)
        rc, _, err = _run(
            ["stamp", "llm", "--adr", "ADR-1", "--verdict", "violation",
             "--state-dir", str(adr_dir)],
            cwd=str(tmp_path),
        )
        assert rc == 0, err
        state = json.loads((adr_dir / ".adr-kit-state.json").read_text(encoding="utf-8"))
        assert state["llm_tier"]["adrs"]["ADR-001"]["verdict"] == "violation"
