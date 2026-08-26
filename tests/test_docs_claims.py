"""Documentation claims that a reader would act on must be true, and stay true.

Three classes of claim live here, all found rotting on the same day (TASK-190):
counts the README advertises, version literals that go stale on the next
release, and action pins shipped in templates users copy. Each is checked
against the artefact that actually knows the answer, so the failure message can
say which file is behind rather than which number to type.

Original docstring, for the count checks:

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


# --- Version literals that go stale on the next release ----------------------


def test_security_policy_names_no_version_it_would_have_to_maintain():
    """SECURITY.md told reporters that v0.33.x was current, for 22 minor versions.

    The prose above the table already states the rule correctly ("only the
    latest minor release line is supported"), so the table was pure
    duplication with an expiry date. A supported-versions table that names a
    number tells a reporter the current release is unsupported the moment it
    ages, which is the most expensive direction for this particular file to be
    wrong in.
    """
    policy = (ROOT / "SECURITY.md").read_text(encoding="utf-8")
    section = policy.split("## Supported versions", 1)
    assert len(section) == 2, "SECURITY.md has no '## Supported versions' section"
    body = section[1].split("\n## ", 1)[0]
    literals = sorted(set(re.findall(r"\bv?\d+\.\d+(?:\.\d+|\.x)\b", body)))
    assert not literals, (
        f"SECURITY.md's supported-versions section names {literals}. State the "
        "rule and link the latest release instead; a number here is false from "
        "the next tag onwards."
    )


def test_roadmap_does_not_assert_a_current_version():
    """ROADMAP.md claimed "adr-kit is at v0.40.0" while 0.55.1 shipped.

    The version history further down the file is deliberately allowed: that is
    a record of what happened, and records do not go stale. Only the status
    line, which claims something about *now*, is checked.
    """
    roadmap = (ROOT / "ROADMAP.md").read_text(encoding="utf-8")
    section = roadmap.split("## Status", 1)
    assert len(section) == 2, "ROADMAP.md has no '## Status' section"
    body = section[1].split("\n## ", 1)[0]
    claims = re.findall(r"is at v?\d+\.\d+\.\d+|currently v?\d+\.\d+\.\d+", body)
    assert not claims, (
        f"ROADMAP.md's status section asserts {claims}. Point at the latest "
        "release instead of restating it here."
    )


# --- Action pins shipped in files users copy ---------------------------------

# The surfaces a user copies into their own repository. A wrong pin here ships
# to them; a wrong pin in a historical note does not.
PINNED_SURFACES = ("README.md", "templates", "codex/templates", "copilot/templates")
PIN = re.compile(r"adr-kit/\.github/actions/([a-z-]+)@v(\d+\.\d+\.\d+)")


def _declared_pin_paths() -> set[str]:
    registry = json.loads(
        (ROOT / "packaging/version-sites.json").read_text(encoding="utf-8")
    )
    return {site["path"] for site in registry["sites"]}


def _shipped_files_with_pins() -> dict[str, list[str]]:
    found: dict[str, list[str]] = {}
    for surface in PINNED_SURFACES:
        target = ROOT / surface
        paths = [target] if target.is_file() else sorted(target.rglob("*"))
        for path in paths:
            if not path.is_file():
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue
            pins = [f"{name}@v{version}" for name, version in PIN.findall(text)]
            if pins:
                found[path.relative_to(ROOT).as_posix()] = pins
    return found


def test_every_shipped_action_pin_is_a_declared_version_site():
    """An undeclared pin ages silently: no writer, gate, generator or test knows.

    templates/github-workflows/adr-readiness.yml sat at v0.37.0 for eighteen
    minor versions while the README pin beside it stayed current, because only
    the README was declared in packaging/version-sites.json. Generated copies
    under codex/ and copilot/ follow from their canonical source rather than
    from their own registry entry, so they are exempt.
    """
    declared = _declared_pin_paths()
    generated_prefixes = ("codex/", "copilot/")
    offenders = {
        path: pins
        for path, pins in _shipped_files_with_pins().items()
        if path not in declared and not path.startswith(generated_prefixes)
    }
    assert not offenders, (
        f"these shipped files carry an action pin no registry declares: {offenders}. "
        "Declare each in packaging/version-sites.json so scripts/bump-version.py "
        "writes it, instead of leaving it to age."
    )


def test_generated_template_pins_match_their_canonical_source():
    """The codex/ and copilot/ copies must not drift from templates/.

    build-client-adapters.py --check is the real guard for drift, but it only
    runs when someone thinks to run it. This states the property directly, so a
    hand-edited copy fails the suite rather than the generator.
    """
    found = _shipped_files_with_pins()
    canonical = {p: v for p, v in found.items() if p.startswith("templates/")}
    assert canonical, "no pinned templates found; the surfaces list is wrong"
    for path, pins in canonical.items():
        tail = path[len("templates/") :]
        for tree in ("codex/templates/", "copilot/templates/"):
            mirror = tree + tail
            if mirror in found:
                assert found[mirror] == pins, (
                    f"{mirror} pins {found[mirror]} but its source {path} pins "
                    f"{pins}. Edit the canonical file and regenerate with "
                    "python scripts/build-client-adapters.py."
                )
