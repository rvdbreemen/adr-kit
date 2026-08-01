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

The staleness half (a recorded model identity or content hash that no longer
matches marks the store stale) cannot be asserted until the store exists. It is
named in ADR-018's Verification and belongs to the first implementation, not
here. Writing a passing test for machinery that does not exist would make the
gate look satisfied while proving nothing.
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
