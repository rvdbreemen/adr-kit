"""Gate anchor for ADR-018: adr-vector-store-v1.

ADR-018 permits an embedding store, and pays for that permission with a
boundary: the store is built in an explicit step and only *read* on the query
path, and nothing in the hook path may call an embedding model, a language
model, or any network endpoint.

Two halves of that contract are verifiable today, before a single vector exists,
and this file holds them:

* the structural half -- the hot-path modules import nothing that could reach a
  model or the network. This is the assertion that keeps its value once the
  store lands, because it is what stops someone from putting embedding *in* the
  hook to make it simpler;
* the fallback half -- retrieval works with no store present. Today that is the
  only mode; after the store lands it is the degraded mode, and it must keep
  working either way.

The staleness half arrived with the store itself (TASK-79) and is asserted at
the bottom of this file: an edited, added or removed ADR marks the store stale
through its content hash, and a dimension mismatch refuses the store outright
rather than scoring nonsense against vectors from a different model.
"""

from __future__ import annotations

import ast
import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
ADR_018 = (
    REPO_ROOT
    / "docs"
    / "adr"
    / "ADR-018-add-a-local-precomputed-vector-layer-for-adr-retrieval.md"
)
GATE = "adr-vector-store-v1"

# Everything that could reach a model or leave the machine. `subprocess` is on
# the list because spawning a CLI is how this toolkit already reaches a model
# (bin/adr_llm.py's SubprocessBackend), so it is a model call by another name.
FORBIDDEN_IN_HOT_PATH = {
    "urllib",
    "http",
    "socket",
    "ssl",
    "ftplib",
    "requests",
    "httpx",
    "subprocess",
    "asyncio",
}

HOT_PATH_MODULES = [
    REPO_ROOT / "hooks" / "adr_hook_core.py",
    REPO_ROOT / "bin" / "adr_query.py",
]


def _imported_roots(path: Path) -> set[str]:
    """Top-level package names imported by a module, via AST rather than grep."""
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                roots.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.level == 0 and node.module:
                roots.add(node.module.split(".")[0])
    return roots


@pytest.mark.parametrize("module", HOT_PATH_MODULES, ids=lambda p: p.name)
def test_hot_path_cannot_reach_a_model_or_the_network(module):
    """ADR-018 Must Not: no model, no network, no daemon on the hook path."""
    assert module.exists(), f"{module} is missing; the gate anchors on it"
    offenders = sorted(_imported_roots(module) & FORBIDDEN_IN_HOT_PATH)
    assert not offenders, (
        f"{module.relative_to(REPO_ROOT)} imports {offenders}, which can reach a "
        f"model or the network. ADR-018 ({GATE}) confines both to the build step: "
        "the query and hook paths read a precomputed store, they do not produce it."
    )


def test_retrieval_works_with_no_vector_store_present():
    """ADR-018 Must: a missing store falls back to lexical ranking, not to silence."""
    result = subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "bin" / "adr-context"),
            "--adr-dir", str(REPO_ROOT / "docs" / "adr"),
            "--format", "json",
            "--limit", "5",
            "enforcement rules against a staged diff",
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        cwd=REPO_ROOT,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    # adr-context returns a bare list of results; tolerate an envelope in case
    # that shape ever changes, rather than pinning the test to today's wrapper.
    results = payload if isinstance(payload, list) else payload.get("results", [])
    assert results, (
        "retrieval returned nothing with no vector store present. The fallback is "
        f"the contract ADR-018 ({GATE}) leans on when the store is missing or stale."
    )


def test_the_record_and_this_anchor_still_agree():
    """A gate is a promise between a record and the code; check both ends."""
    text = ADR_018.read_text(encoding="utf-8")
    assert f'gate: "{GATE}"' in text, (
        f"ADR-018 no longer declares gate {GATE}. If the decision moved, move this "
        "file with it; an orphaned anchor makes adr-lint pass on a promise nobody kept."
    )
    assert 'binding: true' in text, "ADR-018 is no longer binding; this gate has no subject"


# ---------------------------------------------------------------------------
# The staleness half of adr-vector-store-v1, testable now that a store exists.
# ---------------------------------------------------------------------------

def _store_module():
    import importlib.machinery
    import importlib.util

    name = "adr_vector_store"
    loader = importlib.machinery.SourceFileLoader(name, str(REPO_ROOT / "bin" / f"{name}.py"))
    spec = importlib.util.spec_from_loader(name, loader)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    loader.exec_module(module)
    return module


store_mod = _store_module()


def _record(adr_id: str, decision: str, status: str = "Accepted") -> dict:
    return {
        "adr_id": adr_id,
        "title": f"{adr_id} title",
        "path": f"docs/adr/{adr_id}.md",
        "status": status,
        "superseded_by": None,
        "decision": decision,
    }


def _build(tmp_path, records, model="test-model", dims=4):
    vectors = [[float(i + 1)] * dims for i in range(len(records))]
    entries = store_mod.build_entries(records, vectors)
    store_mod.write_store(tmp_path, entries, model, "test", "2026-08-02")
    return store_mod.load_store(tmp_path)[0]


def test_an_edited_adr_marks_the_store_stale(tmp_path):
    """The content hash is what makes a wrong answer announce itself."""
    records = [_record("ADR-001", "original decision")]
    store = _build(tmp_path, records)

    edited = [_record("ADR-001", "a different decision")]
    drift = store_mod.staleness(store, edited)

    assert drift["stale"] is True
    assert drift["changed"] == ["ADR-001"]


def test_a_new_or_removed_adr_marks_the_store_stale(tmp_path):
    store = _build(tmp_path, [_record("ADR-001", "d")])

    drift = store_mod.staleness(store, [_record("ADR-002", "d")])

    assert drift["missing"] == ["ADR-002"]
    assert drift["removed"] == ["ADR-001"]


def test_an_unchanged_set_is_not_stale(tmp_path):
    records = [_record("ADR-001", "d"), _record("ADR-002", "e")]
    store = _build(tmp_path, records)

    assert store_mod.staleness(store, records)["stale"] is False


def test_a_dimension_mismatch_refuses_the_store_rather_than_scoring_nonsense(tmp_path):
    records = [_record("ADR-001", "d")]
    _build(tmp_path, records, dims=4)
    path = store_mod.store_path(tmp_path)
    document = json.loads(path.read_text(encoding="utf-8"))
    document["entries"][0]["vector"] = [1.0, 2.0]  # as if the model changed
    path.write_text(json.dumps(document), encoding="utf-8")

    store, reason = store_mod.load_store(tmp_path)

    assert store is None
    assert "dimension" in reason and "model likely changed" in reason


def test_a_corrupt_store_degrades_with_a_reason(tmp_path):
    store_mod.store_path(tmp_path).write_text("{not json", encoding="utf-8")

    store, reason = store_mod.load_store(tmp_path)

    assert store is None
    assert "unreadable" in reason


def test_a_missing_store_is_a_reason_not_an_exception(tmp_path):
    store, reason = store_mod.load_store(tmp_path)

    assert store is None
    assert reason == "no vector store present"


def test_similarity_never_promotes_a_historical_decision(tmp_path):
    """ADR-014's rule survives ADR-018: relevance and authority are separate."""
    records = [
        _record("ADR-001", "superseded thing", status="Superseded"),
        _record("ADR-002", "current thing", status="Accepted"),
    ]
    store = _build(tmp_path, records)
    # ADR-001 gets the vector nearest the query, and must still be excluded.
    results = store_mod.search(store, [1.0, 1.0, 1.0, 1.0], limit=5)

    assert [row["adr_id"] for row in results] == ["ADR-002"]

    with_history = store_mod.search(store, [1.0, 1.0, 1.0, 1.0], limit=5, include_historical=True)
    historical = next(row for row in with_history if row["adr_id"] == "ADR-001")
    assert historical["authority"] == "historical"


def test_cosine_is_stdlib_and_handles_a_zero_vector(tmp_path):
    assert store_mod.cosine([1.0, 0.0], [1.0, 0.0]) == pytest.approx(1.0)
    assert store_mod.cosine([1.0, 0.0], [0.0, 1.0]) == pytest.approx(0.0)
    assert store_mod.cosine([0.0, 0.0], [1.0, 1.0]) == 0.0


def test_the_store_module_imports_nothing_that_reaches_a_model():
    """The read path is arithmetic on a file; the build step is elsewhere."""
    module = REPO_ROOT / "bin" / "adr_vector_store.py"
    offenders = sorted(_imported_roots(module) & FORBIDDEN_IN_HOT_PATH)

    assert not offenders, f"{module.name} imports {offenders}"
