"""Latency budgets and single-pass regression guards for deterministic CLIs.

Two layers, mirroring tests/test_hook_performance.py:

1. Machine-independent structural guards: the O(ADRs x files) and
   O(gates x files) repeated-walk bugs stay fixed regardless of runner speed.
2. A live smoke measurement against this repository asserting the 2-second
   user-wait ceiling from tests/fixtures/cli/latency-corpus.json.
"""

from __future__ import annotations

import json
import runpy
import statistics
import subprocess
import sys
import time
from pathlib import Path

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
