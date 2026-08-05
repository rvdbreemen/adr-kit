"""An ADR whose named gate exists must stop saying it has none.

ADR-020 through ADR-032 were accepted with `gate: null` and `binding: false`,
because each declares a gate name that did not exist in the tree yet and
`adr-lint` refuses an Accepted *binding* ADR whose gate cannot be resolved. The
fields said what was true rather than what was intended.

The part that decays silently is the flip back. `binding: false` costs a real
thing while it lasts -- `adr_retrieval_health` only inspects Accepted binding
records, so a non-binding ADR's Decision Contract is never checked -- and nothing
reminds anyone once the gate finally ships.

This turns "someone must remember" into "the gate tells you" (TASK-127).

It lives here rather than in `bin/adr-lint` deliberately. The investigation
measured the equivalent probe at roughly +220 ms on every lint run, and lint runs
on every commit through the pre-commit hook. A governance check that makes the
commit path slower is a check people switch off.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ADR_DIR = ROOT / "docs" / "adr"

# Where a gate anchor may legitimately live. Mirrors adr-lint's own scan set:
# docs/ and backlog/ are excluded, because an ADR's own Verification bullet and a
# task file's table must not be able to make a gate "exist".
ANCHOR_ROOTS = ("bin", "hooks", "scripts", "tests", "clients", ".github")

_GATE_NAME = re.compile(r"^\s*[*-]\s*`([a-z0-9][a-z0-9-]*-v\d+)`\s*$", re.M)


def _verification_gate(text: str) -> str | None:
    """The gate name an ADR declares in its Verification section, if any."""
    match = re.search(
        r"^### Verification\s*$(.*?)^##", text, re.M | re.S
    ) or re.search(r"^### Verification\s*$(.*)", text, re.M | re.S)
    if not match:
        return None
    names = _GATE_NAME.findall(match.group(1))
    return names[0] if names else None


def _frontmatter(text: str, key: str) -> str | None:
    match = re.search(rf"^{key}:\s*(.+?)\s*$", text, re.M)
    return match.group(1).strip().strip('"') if match else None


def _anchor_exists(gate: str) -> bool:
    result = subprocess.run(
        ["git", "grep", "-l", "--", gate, "--", *ANCHOR_ROOTS],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    return bool(result.stdout.strip())


def test_an_adr_whose_named_gate_exists_no_longer_says_it_has_none():
    """The flip is mechanical, not remembered."""
    stale = []
    for path in sorted(ADR_DIR.glob("ADR-*.md")):
        text = path.read_text(encoding="utf-8")
        if _frontmatter(text, "status") != "Accepted":
            continue
        gate = _verification_gate(text)
        if not gate or not _anchor_exists(gate):
            continue
        declared = _frontmatter(text, "gate")
        binding = _frontmatter(text, "binding")
        if declared in (None, "null") or binding != "true":
            stale.append(
                f"{path.name}: Verification names `{gate}`, which exists in the "
                f"tree, but frontmatter carries gate: {declared} and "
                f"binding: {binding}"
            )

    assert not stale, (
        "these records now have the gate they were waiting for:\n  "
        + "\n  ".join(stale)
        + "\n\nSet gate to the declared name and binding to true, together. While "
        "binding is false, adr_retrieval_health never checks the record's "
        "Decision Contract."
    )


def test_a_declared_gate_that_does_not_exist_yet_is_not_a_finding():
    """gate: null is correct while the anchor is genuinely absent.

    Without this the check would push people to declare a gate name that
    resolves to nothing, which adr-lint then refuses -- trading a silent decay
    for a loud false alarm.
    """
    assert not _anchor_exists("this-gate-does-not-exist-anywhere-v1")


def test_an_adrs_own_verification_bullet_cannot_make_its_gate_exist():
    """docs/ is excluded from the anchor scan, so a record cannot self-satisfy."""
    assert "docs" not in ANCHOR_ROOTS
    assert "backlog" not in ANCHOR_ROOTS
