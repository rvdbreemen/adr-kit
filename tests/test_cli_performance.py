"""Latency budgets and single-pass regression guards for deterministic CLIs.

Two layers, mirroring tests/test_hook_performance.py:

1. Machine-independent structural guards: the O(ADRs x files) and
   O(gates x files) repeated-walk bugs stay fixed regardless of runner speed.
2. A live smoke measurement against this repository asserting the 2-second
   user-wait ceiling from tests/fixtures/cli/latency-corpus.json.
"""

from __future__ import annotations

import json
import os
import runpy
import statistics
import subprocess
import sys
import time
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
CORPUS = REPO_ROOT / "tests" / "fixtures" / "cli" / "latency-corpus.json"

RETIRE = runpy.run_path(str(REPO_ROOT / "bin" / "adr-retire"))
LINT = runpy.run_path(str(REPO_ROOT / "bin" / "adr-lint"))


# ---------------------------------------------------------------------------
# Corpus invariants
# ---------------------------------------------------------------------------

def test_latency_corpus_fixes_method_budgets_and_goal():
    corpus = json.loads(CORPUS.read_text(encoding="utf-8"))
    assert corpus["method_id"] == "adr-kit-cli-latency-v1"
    assert corpus["process_startup_included"] is True
    for tool in ("adr-lint", "adr-retire"):
        budget = corpus["budgets"][tool]
        assert budget["hard_timeout_ms"] == 2000
        assert budget["p50_ms"] < budget["p95_ms"] <= budget["hard_timeout_ms"]


# ---------------------------------------------------------------------------
# Structural guards: adr-retire
# ---------------------------------------------------------------------------

def _project(tmp_path, sources):
    for rel, content in sources.items():
        target = tmp_path / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
    return tmp_path


def test_retire_walk_is_memoized_per_root(tmp_path):
    _project(tmp_path, {"src/app.py": "import redis\n"})
    first = RETIRE["_walk_repo_files"](tmp_path, {".py"})
    second = RETIRE["_walk_repo_files"](tmp_path, {".py"})
    assert first is second, "repeated walks of the same root must hit the cache"


def test_retire_resolves_all_terms_in_one_pass(tmp_path):
    root = _project(
        tmp_path,
        {
            "src/a.py": "redis client\n",
            "src/b.ts": "kafka producer\n",
        },
    )
    found = RETIRE["resolve_present_terms"](root, ["Redis", "Kafka", "Cobol"])
    assert found == {"redis", "kafka"}


def test_retire_ignores_nested_checkout(tmp_path):
    root = _project(
        tmp_path,
        {
            "src/app.py": "plain code\n",
            "vendor-clone/lib.py": "uses redis\n",
        },
    )
    (root / "vendor-clone" / ".git").mkdir()
    found = RETIRE["resolve_present_terms"](root, ["redis"])
    assert found == set(), "terms inside a nested checkout are not project source"


def test_retire_tech_removal_matches_precomputed_and_on_demand(tmp_path):
    root = _project(tmp_path, {"src/app.py": "redis here\n"})
    content = "# ADR-001 X\n\n## Decision\n\nUse `redis`.\n"
    on_demand = RETIRE["detect_tech_removal"]("ADR-001", content, root)
    precomputed = RETIRE["detect_tech_removal"](
        "ADR-001", content, root, present_terms={"redis"}
    )
    assert on_demand == precomputed == 0.0


# ---------------------------------------------------------------------------
# Structural guards: adr-lint
# ---------------------------------------------------------------------------

def test_lint_resolves_multiple_gates_in_one_pass(tmp_path):
    root = _project(
        tmp_path,
        {
            "scripts/release.sh": "runs gate-alpha\n",
            "tests/test_x.py": "covers gate-beta\n",
        },
    )
    found = LINT["_resolve_gates_locally"](["gate-alpha", "gate-beta", "gate-nope"], root)
    assert found == {"gate-alpha", "gate-beta"}


def test_lint_gate_scan_ignores_nested_checkout(tmp_path):
    root = _project(tmp_path, {"scripts/run.sh": "no gates here\n"})
    nested = root / "worktree-copy"
    (nested / "scripts").mkdir(parents=True)
    (nested / ".git").mkdir()
    (nested / "scripts" / "run.sh").write_text("mentions gate-alpha\n", encoding="utf-8")
    assert LINT["_gate_exists_locally"]("gate-alpha", root) is False


def test_lint_single_gate_wrapper_still_works(tmp_path):
    root = _project(tmp_path, {"scripts/run.sh": "mentions gate-alpha\n"})
    assert LINT["_gate_exists_locally"]("gate-alpha", root) is True
    assert LINT["_gate_exists_locally"]("", root) is False


def _link_dir(link: Path, target: Path) -> None:
    """A junction on Windows, a directory symlink elsewhere.

    Windows gets the junction first on purpose: os.walk already skipped a
    symlink, and the junction is the case it walked into.
    """
    if sys.platform == "win32":
        subprocess.run(
            ["cmd", "/c", "mklink", "/J", str(link), str(target)],
            capture_output=True, check=False,
        )
    else:
        try:
            os.symlink(target, link, target_is_directory=True)
        except (OSError, NotImplementedError):
            pass
    if not link.exists():
        pytest.skip("cannot create a directory link on this machine")


def test_lint_gate_scan_does_not_follow_directory_links(tmp_path):
    # A link (symlink or Windows junction) out of the tree, and one that loops
    # back into it. os.walk(followlinks=False) still descends into junctions,
    # so the loop was walked until the path limit and the outside tree was
    # read as if it were this project's source.
    root = _project(tmp_path / "proj", {"scripts/run.sh": "no gates here\n"})
    outside = _project(tmp_path / "outside", {"scripts/x.sh": "gate-alpha\n"})
    _link_dir(root / "elsewhere", outside)
    _link_dir(root / "scripts" / "loop", root)
    found, unverified = LINT["_scan_gates"](["gate-alpha"], root)
    assert found == set()
    assert unverified is None


# runpy hands back a copy of the module namespace; the functions read their
# constants from the live one, so overrides go through __globals__.
LINT_LIVE = LINT["detect_frontmatter_consistency"].__globals__


def _with_lint_globals(**overrides):
    saved = {key: LINT_LIVE[key] for key in overrides}
    LINT_LIVE.update(overrides)
    return saved


def test_lint_gate_scan_stops_at_entry_budget(tmp_path):
    root = _project(
        tmp_path, {f"scripts/f{i}.sh": "nothing\n" for i in range(20)}
    )
    saved = _with_lint_globals(GATE_SCAN_MAX_ENTRIES=5)
    try:
        found, unverified = LINT["_scan_gates"](["gate-alpha"], root)
    finally:
        LINT_LIVE.update(saved)
    assert found == set()
    assert unverified and "5 entries" in unverified


def test_lint_gate_scan_stops_at_time_budget(tmp_path):
    root = _project(tmp_path, {"scripts/run.sh": "nothing\n"})
    saved = _with_lint_globals(GATE_SCAN_MAX_SECONDS=0.0)
    try:
        found, unverified = LINT["_scan_gates"](["gate-alpha"], root)
    finally:
        LINT_LIVE.update(saved)
    assert found == set()
    assert unverified and "seconds" in unverified


def test_lint_gate_scan_skips_large_files_and_graphify_out(tmp_path):
    root = _project(
        tmp_path,
        {
            "scripts/big.sh": "gate-alpha\n" + "x" * 64,
            "graphify-out/graph.json": '{"gate": "gate-beta"}\n',
        },
    )
    saved = _with_lint_globals(GATE_SCAN_MAX_FILE_BYTES=32)
    try:
        found, unverified = LINT["_scan_gates"](["gate-alpha", "gate-beta"], root)
    finally:
        LINT_LIVE.update(saved)
    assert found == set()
    assert unverified is None


def test_lint_reports_unverified_gate_apart_from_missing_gate(tmp_path):
    root = _project(tmp_path, {f"scripts/f{i}.sh": "nothing\n" for i in range(20)})
    adr_dir = root / "docs" / "adr"
    adr_dir.mkdir(parents=True)
    adr = adr_dir / "ADR-001-bound.md"
    adr.write_text(
        "---\n"
        'id: "ADR-001"\n'
        'title: "Bound"\n'
        'status: "Accepted"\n'
        'date: "2026-10-03"\n'
        "binding: true\n"
        'gate: "gate-alpha"\n'
        "documents_shipped: false\n"
        "verified_in: []\n"
        "supersedes: []\n"
        "superseded_by: null\n"
        "---\n\n# ADR-001: Bound\n\n## Status\n\nAccepted\n",
        encoding="utf-8",
    )
    saved = _with_lint_globals(GATE_SCAN_MAX_ENTRIES=5)
    try:
        issues = LINT["detect_frontmatter_consistency"]([adr], root)
    finally:
        LINT_LIVE.update(saved)
    messages = [m for found in issues.values() for m in found if "gate-alpha" in m]
    assert messages, issues
    assert all("could not be verified" in m for m in messages)
    assert not any("was not found" in m for m in messages)


def test_lifecycle_lint_call_times_out():
    adr = runpy.run_path(str(REPO_ROOT / "bin" / "adr"))
    adr["_run_json_tool"].__globals__["LIFECYCLE_TOOL_TIMEOUT_S"] = 0.5
    with pytest.raises(adr["AdrLifecycleError"], match="timed out"):
        adr["_run_json_tool"]([sys.executable, "-c", "import time; time.sleep(30)"])


# ---------------------------------------------------------------------------
# Live smoke: the 2-second ceiling on this repository
# ---------------------------------------------------------------------------

def _smoke(argv, samples):
    cmd = [sys.executable, *argv]
    subprocess.run(cmd, cwd=REPO_ROOT, capture_output=True, timeout=60)  # warmup
    durations = []
    for _ in range(samples):
        started = time.perf_counter()
        subprocess.run(cmd, cwd=REPO_ROOT, capture_output=True, timeout=60)
        durations.append((time.perf_counter() - started) * 1000)
    return statistics.median(durations)


def test_lint_and_retire_meet_hard_ceiling_on_this_repo():
    corpus = json.loads(CORPUS.read_text(encoding="utf-8"))
    samples = corpus["sample_count"]["smoke"]
    for tool, argv in (
        ("adr-lint", [str(REPO_ROOT / "bin" / "adr-lint"), "docs/adr"]),
        ("adr-retire", [str(REPO_ROOT / "bin" / "adr-retire")]),
    ):
        p50 = _smoke(argv, samples)
        ceiling = corpus["budgets"][tool]["hard_timeout_ms"]
        assert p50 <= ceiling, (
            f"{tool} p50 {p50:.0f}ms exceeds the {ceiling}ms user-wait ceiling"
        )
