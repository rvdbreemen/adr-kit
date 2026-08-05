"""Semantic retrieval reaches the query path, and says when it does not.

ADR-020 permits embedding the query where the query is asked, which is what
makes the vector store usable at all: a similarity comparison needs two vectors,
and the second one does not exist until someone asks something. ADR-018 forbade
producing it, so the store it authorised never reached a shipped path.

The embedder arrives as a callable rather than an import, and that is the design
rather than a convenience. `bin/adr_query.py` has to stay reachable from a hook,
so it imports nothing that can touch a model or the network -- asserted by AST
walk in `test_adr_vector_store_contract.py`. The caller that *can* reach a
backend decides whether to supply one, which is also how ADR-020's per-event
budget split is honoured: the 500 ms events get an embedder, the 100 ms events
stay on the index-only route.

Every failure here returns the lexical order with a named reason. A retrieval
path that silently degrades is worse than one that is slower: the user cannot
tell "no ADR was relevant" from "the backend was down".
"""

# Gate anchor for ADR-020: adr-query-embedding-v1
# Verified here: the query is embedded where it is asked, and authority is joined from the index at search time.

from __future__ import annotations

import importlib.machinery
import importlib.util
import json
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent


def _query_module():
    name = "adr_query_semantic"
    cached = sys.modules.get(name)
    if cached is not None:
        return cached
    loader = importlib.machinery.SourceFileLoader(
        name, str(REPO_ROOT / "bin" / "adr_query.py")
    )
    spec = importlib.util.spec_from_loader(name, loader)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    loader.exec_module(module)
    return module


adr_query = _query_module()

FRONTMATTER = """---
id: "ADR-{number:03d}"
title: "{title}"
status: "Accepted"
date: "2026-05-01"
binding: false
gate: null
documents_shipped: false
verified_in: []
supersedes: []
superseded_by: null
context_scope: "selective"
format: "madr"
aliases: []
components: []
symbols: []
topics:
  - "{topic}"
---
"""

BODY = textwrap.dedent(
    """\

    # ADR-{number:03d} {title}

    ## Status

    Accepted, 2026-05-01.

    ## Context and Problem Statement

    Some context for {title}.

    ## Considered Options

    * Do it.
    * Do nothing.

    ## Decision Outcome

    Chosen option: **{decision}**, because it is the point of this fixture.

    ## Consequences

    ### Positive

    * 1 benefit.

    ### Negative

    * 1 cost.

    ## Related Decisions

    * None.

    ## References

    * docs/adr/README.md
    """
)


def _adr(number: int, title: str, decision: str, topic: str) -> str:
    fields = {"number": number, "title": title, "decision": decision, "topic": topic}
    return FRONTMATTER.format(**fields) + BODY.format(**fields)


@pytest.fixture()
def project(tmp_path):
    """Two ADRs with a generated index, and no vector store unless a test adds one."""
    adr_dir = tmp_path / "docs" / "adr"
    adr_dir.mkdir(parents=True)
    (adr_dir / "ADR-001-first.md").write_text(
        _adr(1, "First Decision", "the first option", "alpha"), encoding="utf-8"
    )
    (adr_dir / "ADR-002-second.md").write_text(
        _adr(2, "Second Decision", "the second option", "beta"), encoding="utf-8"
    )
    subprocess.run(
        [sys.executable, str(REPO_ROOT / "bin" / "adr-index"), str(adr_dir)],
        capture_output=True, check=True,
    )
    return adr_dir


def _write_store(adr_dir: Path, vectors) -> None:
    (adr_dir / ".adr-kit-vectors.json").write_text(
        json.dumps({
            "schema_version": 1,
            "model": "test-model",
            "backend": "test",
            "dimension": 2,
            "built_at": "2026-08-04",
            "entries": [
                {"adr_id": adr_id, "vector": vector}
                for adr_id, vector in vectors.items()
            ],
        }),
        encoding="utf-8",
    )


def _query(adr_dir: Path, text: str, **kwargs):
    return adr_query.query_adr_context(text, adr_dir, limit=5, min_score=0.0, **kwargs)


def _raise(_query_text):
    raise OSError("connection refused")


def test_without_an_embedder_the_route_is_lexical(project):
    outcome = _query(project, "alpha")

    assert outcome["route"] == "lexical"
    assert outcome["warnings"] == []


def test_an_embedder_reorders_by_similarity(project):
    """The point of the feature: a query sharing no words with the record.

    'alpha' and 'beta' are the only lexical handles in this fixture, so a query
    containing neither can be answered correctly only by the vectors.
    """
    _write_store(project, {"ADR-001": [1.0, 0.0], "ADR-002": [0.0, 1.0]})

    outcome = _query(
        project, "something entirely unrelated", embedder=lambda _q: [0.0, 1.0]
    )

    assert outcome["route"] == "vector"
    assert outcome["results"][0]["adr_id"] == "ADR-002"
    assert outcome["results"][0]["similarity"] == pytest.approx(1.0)


def test_the_opposite_vector_selects_the_other_record(project):
    """A control: the order follows the vector, not the fixture's own order."""
    _write_store(project, {"ADR-001": [1.0, 0.0], "ADR-002": [0.0, 1.0]})

    outcome = _query(
        project, "something entirely unrelated", embedder=lambda _q: [1.0, 0.0]
    )

    assert outcome["results"][0]["adr_id"] == "ADR-001"


@pytest.mark.parametrize(
    ("embedder", "expected_fragment"),
    [
        pytest.param(_raise, "embedding failed", id="backend-unreachable"),
        pytest.param(lambda _q: None, "returned no vector", id="empty-response"),
        pytest.param(lambda _q: [], "returned no vector", id="empty-list"),
    ],
)
def test_every_backend_failure_falls_back_and_says_so(
    project, embedder, expected_fragment
):
    """Exit 0, lexical order, and a reason the user can read.

    Silence here is the failure mode this release keeps finding: an empty result
    reads exactly like "no ADR was relevant".
    """
    _write_store(project, {"ADR-001": [1.0, 0.0], "ADR-002": [0.0, 1.0]})

    outcome = _query(project, "alpha", embedder=embedder)

    assert outcome["route"] == "lexical"
    assert any(expected_fragment in warning for warning in outcome["warnings"])
    assert outcome["results"], "the lexical answer must still be returned"


def test_a_missing_store_falls_back_without_an_error(project):
    outcome = _query(project, "alpha", embedder=lambda _q: [1.0, 0.0])

    assert outcome["route"] == "lexical"
    assert any("no vector store" in warning for warning in outcome["warnings"])


def test_a_malformed_store_falls_back_without_an_error(project):
    (project / ".adr-kit-vectors.json").write_text("{not json", encoding="utf-8")

    outcome = _query(project, "alpha", embedder=lambda _q: [1.0, 0.0])

    assert outcome["route"] == "lexical"
    assert outcome["warnings"]


def test_an_empty_store_falls_back_rather_than_ranking_everything_at_zero(project):
    _write_store(project, {})

    outcome = _query(project, "alpha", embedder=lambda _q: [1.0, 0.0])

    assert outcome["route"] == "lexical"
    assert any("empty" in warning for warning in outcome["warnings"])


def test_the_route_is_reported_on_every_outcome(project):
    """A caller must be able to tell which route answered, without guessing."""
    _write_store(project, {"ADR-001": [1.0, 0.0], "ADR-002": [0.0, 1.0]})

    assert _query(project, "alpha")["route"] == "lexical"
    assert _query(project, "alpha", embedder=lambda _q: [1.0, 0.0])["route"] == "vector"


# ---------------------------------------------------------------------------
# The hook path, driven through the real process (TASK-94 AC#2)
# ---------------------------------------------------------------------------

def _fire(workspace: Path, event: str, payload: dict) -> bytes:
    body = dict(payload)
    body["cwd"] = str(workspace)
    result = subprocess.run(
        [sys.executable, str(REPO_ROOT / "hooks" / "adr-hook.py"),
         "--client", "claude-code-cli", "--event", event],
        input=json.dumps(body).encode("utf-8"), capture_output=True,
    )
    assert result.returncode == 0, result.stderr.decode("utf-8", "replace")
    return result.stdout


def test_the_prompt_event_falls_back_audibly_when_the_backend_is_absent(project):
    """A store with no reachable backend must say the answer is degraded.

    This is the case a user actually hits: they built a store, then the runtime
    was not running. Silence would be indistinguishable from a healthy lexical
    answer, and from "no ADR was relevant".
    """
    _write_store(project, {"ADR-001": [1.0, 0.0], "ADR-002": [0.0, 1.0]})

    frame = _fire(project.parent.parent, "user-prompt-submit",
                  {"hook_event_name": "UserPromptSubmit", "prompt": "alpha"})

    assert b"fell back to lexical" in frame


def test_no_store_means_no_claim_about_semantic_retrieval(project):
    """Without a store the hook never promised vectors, so it says nothing.

    The note exists to flag a *degraded* answer. Printing it where semantic
    retrieval was never configured would train users to ignore it.
    """
    frame = _fire(project.parent.parent, "user-prompt-submit",
                  {"hook_event_name": "UserPromptSubmit", "prompt": "alpha"})

    assert frame, "the lexical answer is still injected"
    assert b"fell back to lexical" not in frame


def test_the_edit_tier_never_embeds(project):
    """ADR-020 keeps the 100 ms events on the index-only route.

    An embedding round trip does not fit 100 ms at any realistic ADR count, so
    the edit tier must not even be offered an embedder -- and therefore must
    never print the fallback note, which only appears when one was supplied.
    """
    _write_store(project, {"ADR-001": [1.0, 0.0], "ADR-002": [0.0, 1.0]})
    (project.parent.parent / "src").mkdir(exist_ok=True)
    (project.parent.parent / "src" / "thing.py").write_text("x\n", encoding="utf-8")

    for event in ("pre-tool-use", "post-tool-use"):
        frame = _fire(project.parent.parent, event, {
            "hook_event_name": "PreToolUse" if event == "pre-tool-use" else "PostToolUse",
            "tool_name": "Write",
            "tool_input": {"file_path": "src/thing.py"},
        })
        assert b"fell back to lexical" not in frame, event


def test_the_entrypoint_decides_which_events_may_embed():
    """The split is a named constant, not a condition buried in a branch.

    Widening it is a decision -- it puts a network round trip on a tighter
    budget -- so it should be one line a reviewer can see.
    """
    source = (REPO_ROOT / "hooks" / "adr-hook.py").read_text(encoding="utf-8")

    assert "EMBEDDING_EVENTS = {\"UserPromptSubmit\"}" in source


def test_the_retrieval_core_still_cannot_reach_the_network():
    """The guarantee threading an embedder through was designed to preserve."""
    import ast

    forbidden = {"urllib", "http", "socket", "ssl", "requests", "httpx",
                 "subprocess", "asyncio"}
    for module in (REPO_ROOT / "hooks" / "adr_hook_core.py",
                   REPO_ROOT / "bin" / "adr_query.py"):
        tree = ast.parse(module.read_text(encoding="utf-8"), filename=str(module))
        roots = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                roots.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                roots.add(node.module.split(".")[0])
        assert not roots & forbidden, (module.name, sorted(roots & forbidden))
