"""The counts the README advertises must match the manifests they describe.

Written after a sweep found the README claiming "15 workflows, six bounded
hooks, and the five-tool MCP server" while the repository shipped 17 workflows,
eight hook events and seven MCP tools -- and while the same README said "Seven
tools, all key-free" two hundred lines further down. Correcting the numbers by
hand fixes today and guarantees a repeat, because nothing reads the sentence.
These assertions read it.

The failure message names the file to edit rather than the number to type: the
manifests are the source of truth, so a mismatch means the prose is behind, not
that the count is wrong.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Only the values the README actually spells out in words or digits.
NUMBER_WORDS = {
    5: "five",
    6: "six",
    7: "seven",
    8: "eight",
    9: "nine",
    10: "ten",
}


def _readme() -> str:
    return (ROOT / "README.md").read_text(encoding="utf-8")


def _workflow_count() -> int:
    data = json.loads((ROOT / "clients/workflows.json").read_text(encoding="utf-8"))
    return len(data["workflows"])


def _hook_event_count() -> int:
    data = json.loads((ROOT / "hooks/manifest.json").read_text(encoding="utf-8"))
    return len(data["events"])


def _mcp_tool_count() -> int:
    source = (ROOT / "bin/adr-mcp").read_text(encoding="utf-8")
    return len(set(re.findall(r'"name":\s*"(adr_[a-z_]+)"', source)))


def test_readme_workflow_count_matches_the_registry():
    expected = _workflow_count()
    stale = re.findall(r"\b(\d+) workflows\b", _readme())
    assert stale, "README no longer states a workflow count; drop this assertion"
    wrong = sorted({n for n in stale if int(n) != expected})
    assert not wrong, (
        f"README says {wrong} workflows; clients/workflows.json declares {expected}. "
        "Update README.md."
    )


def test_readme_hook_count_matches_the_manifest():
    expected = _hook_event_count()
    word = NUMBER_WORDS[expected]
    readme = _readme()
    claims = re.findall(r"\b(\w+) bounded hooks\b", readme)
    assert claims, "README no longer states a bounded-hook count; drop this assertion"
    wrong = sorted({c for c in claims if c != word and c != str(expected)})
    assert not wrong, (
        f"README says {wrong} bounded hooks; hooks/manifest.json declares "
        f"{expected} ({word}). Update README.md."
    )


def test_readme_mcp_tool_count_is_consistent_everywhere():
    expected = _mcp_tool_count()
    word = NUMBER_WORDS[expected]
    readme = _readme()
    # "five-tool MCP server" and friends: the hyphenated adjective form. The
    # README uses the word in prose and the digit inside a comparison table, so
    # both spellings are correct and only a different count is a failure.
    accepted = {word, str(expected)}
    adjectives = sorted(set(re.findall(r"\b(\w+)-tool MCP server\b", readme)))
    wrong = [a for a in adjectives if a not in accepted]
    assert not wrong, (
        f"README calls it a {wrong} MCP server; bin/adr-mcp exposes {expected} "
        f"tools ({word}). Update README.md."
    )
    # The prose section that enumerates them must agree with the adjective.
    assert f"{word.capitalize()} tools" in readme or f"{word} tools" in readme, (
        f"README states no '{word} tools' section while bin/adr-mcp exposes "
        f"{expected}. The adjective and the enumeration must not disagree."
    )
