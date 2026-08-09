"""Enable the LLM judge on existing ADRs, opt-out style.

`llm_judge` defaults to TRUE as of TASK-74, so an Enforcement block that says
nothing about it opts in. Existing ADRs are the problem this module solves:
they were authored under the old default and carry an explicit
``"llm_judge": false`` that is indistinguishable from a deliberate refusal.

The distinction is a reason. A bare ``false`` is treated as a leftover and
proposed for enabling; a ``false`` with ``llm_judge_reason`` is a decision
somebody made on purpose and is left alone, on this run and every later one.
That is the whole memory mechanism -- it lives in the ADR, not in a state file
that a fresh clone would lose.

The module is deterministic and does no prompting. The interactive part
belongs to the upgrade skill, which shows the user each Decision and its
current block and then calls this code with explicit opt-outs. Same split as
ADR-011: a deterministic engine, a human-gated conversation on top.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

ENFORCEMENT_FENCE_RE = re.compile(
    r"(^##\s+Enforcement\s*$\n+.*?```json\s*\n)(.*?)(\n```)",
    re.IGNORECASE | re.MULTILINE | re.DOTALL,
)

NO_CODE_SURFACE_REASON = (
    "no code surface: this decision governs process or documentation, "
    "so there is no diff for a model to judge it against"
)

# What a scan can conclude about one ADR.
STATE_ENABLED = "enabled"  # llm_judge true or absent -- already opted in
STATE_LEGACY_OFF = "legacy-off"  # bare false: propose enabling
STATE_OPTED_OUT = "opted-out"  # false + reason: remembered refusal
STATE_NO_BLOCK = "no-enforcement-block"
STATE_UNPARSEABLE = "unparseable-enforcement-block"
STATE_NOT_ACCEPTED = "not-accepted"


def _adr_id(path: Path) -> str:
    match = re.match(r"(?i)(ADR-\d{1,4})", path.name)
    return match.group(1).upper() if match else path.stem


def _status_word(text: str) -> Optional[str]:
    """Delegate to the one cross-tool status reader.

    Writing a second status heuristic here would be a quiet way to disagree
    with the judge about which ADRs are Accepted -- and this module decides
    which ADRs the judge will be asked to enforce. One reader, one answer.
    """
    import importlib.machinery
    import importlib.util

    here = Path(__file__).resolve().parent

    def load(name: str):
        cached = sys.modules.get(name)
        if cached is not None:
            return cached
        loader = importlib.machinery.SourceFileLoader(name, str(here / f"{name}.py"))
        spec = importlib.util.spec_from_loader(name, loader)
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        loader.exec_module(module)
        return module

    # Dependency order, same as bin/adr-migrate: adr_catalog imports both.
    load("adr_format")
    load("adr_schema")
    return load("adr_catalog").adr_status(text)


def read_enforcement(text: str) -> Tuple[Optional[Dict], Optional[str]]:
    """Return (block, error). Both None-able: no block is not an error."""
    match = ENFORCEMENT_FENCE_RE.search(text)
    if not match:
        return None, None
    try:
        data = json.loads(match.group(2))
    except json.JSONDecodeError as exc:
        return None, f"{exc.msg} at line {exc.lineno}"
    if not isinstance(data, dict):
        return None, "Enforcement block is not a JSON object"
    return data, None


def rule_count(block: Dict) -> int:
    return sum(
        len(block.get(kind, []) or [])
        for kind in ("forbid_pattern", "forbid_import", "require_pattern")
    )


def has_unbounded_scope(block: Dict) -> bool:
    """True when nothing narrows this ADR, so judging it costs a call per commit."""
    saw_rule = False
    for kind in ("forbid_pattern", "forbid_import", "require_pattern"):
        for rule in block.get(kind, []) or []:
            saw_rule = True
            if not (rule or {}).get("path_glob"):
                return True
    return not saw_rule


def classify(path: Path) -> Dict:
    """Read one ADR and decide what the upgrade should propose for it."""
    text = path.read_text(encoding="utf-8", errors="replace")
    row: Dict = {
        "adr": _adr_id(path),
        "path": str(path),
        "status": _status_word(text),
        "state": STATE_NO_BLOCK,
        "rules": 0,
        "unbounded_scope": False,
        "reason": None,
        "proposal": "none",
    }
    if (row["status"] or "").lower() != "accepted":
        row["state"] = STATE_NOT_ACCEPTED
        return row
    block, error = read_enforcement(text)
    if error is not None:
        row["state"] = STATE_UNPARSEABLE
        row["reason"] = error
        return row
    if block is None:
        return row
    row["rules"] = rule_count(block)
    row["unbounded_scope"] = has_unbounded_scope(block)
    reason = block.get("llm_judge_reason")
    if block.get("llm_judge", True):
        row["state"] = STATE_ENABLED
        return row
    if isinstance(reason, str) and reason.strip():
        row["state"] = STATE_OPTED_OUT
        row["reason"] = reason
        return row
    row["state"] = STATE_LEGACY_OFF
    # A rule-less block has no boundary, so enabling it means a call on every
    # commit. Say so in the proposal rather than in a footnote nobody reads.
    row["proposal"] = "mark-no-code-surface" if row["rules"] == 0 else "enable"
    return row


def scan(adr_dir: Path) -> List[Dict]:
    files = sorted(
        (p for p in adr_dir.glob("ADR-*.md") if re.match(r"(?i)ADR-\d", p.name)),
        key=lambda p: p.name.lower(),
    )
    return [classify(p) for p in files]


def _rewrite_block(text: str, mutate) -> Optional[str]:
    """Apply mutate(block) to the Enforcement JSON, preserving the surroundings."""
    match = ENFORCEMENT_FENCE_RE.search(text)
    if not match:
        return None
    try:
        block = json.loads(match.group(2))
    except json.JSONDecodeError:
        return None
    if not isinstance(block, dict):
        return None
    changed = mutate(block)
    if not changed:
        return None
    body = json.dumps(block, indent=2, ensure_ascii=False)
    return text[: match.start(2)] + body + text[match.end(2) :]


def enable(path: Path) -> bool:
    """Drop an unreasoned llm_judge:false so the true default applies."""

    def mutate(block: Dict) -> bool:
        if block.get("llm_judge", True):
            return False
        if isinstance(block.get("llm_judge_reason"), str) and block["llm_judge_reason"].strip():
            return False
        # Remove rather than write true: absent means the default, and the
        # default is what this change is about. One fewer thing to re-flip if
        # the default ever moves again.
        block.pop("llm_judge", None)
        return True

    new = _rewrite_block(path.read_text(encoding="utf-8"), mutate)
    if new is None:
        return False
    path.write_text(new, encoding="utf-8")
    return True


def opt_out(path: Path, reason: str) -> bool:
    """Record a deliberate refusal that later upgrades must respect."""
    reason = (reason or "").strip()
    if not reason:
        raise ValueError("an opt-out needs a reason; a bare false is not remembered")

    def mutate(block: Dict) -> bool:
        if block.get("llm_judge") is False and block.get("llm_judge_reason") == reason:
            return False
        block["llm_judge"] = False
        block["llm_judge_reason"] = reason
        return True

    new = _rewrite_block(path.read_text(encoding="utf-8"), mutate)
    if new is None:
        return False
    path.write_text(new, encoding="utf-8")
    return True


def apply(
    adr_dir: Path,
    *,
    opt_out_ids: Sequence[str] = (),
    no_code_surface_ids: Sequence[str] = (),
    force_enable_ids: Sequence[str] = (),
    opt_out_reason: str = "",
    dry_run: bool = False,
) -> Dict:
    """Enable every eligible ADR except the ones the user declined.

    Opt-out is the default posture: an ADR the caller does not name gets the
    LLM pass. Naming an ADR in ``opt_out_ids`` or ``no_code_surface_ids``
    writes a reasoned false instead, which later runs leave alone.

    One exception to plain opt-out, and it is the reason this function is not
    a one-liner: an Enforcement block with NO rules has no scope to narrow
    with, so enabling it buys a model call on every commit for a decision that
    may have no code surface at all. Those are marked no-code-surface instead.
    ``force_enable_ids`` overrides that per ADR, for the case where the
    decision really is code-governing and the author simply has not written
    the rules yet -- and then the cost is what the user asked for.
    """
    declined = {i.upper() for i in opt_out_ids}
    no_surface = {i.upper() for i in no_code_surface_ids}
    overlap = declined & no_surface
    if overlap:
        raise ValueError(
            f"{sorted(overlap)} named as both a plain opt-out and no-code-surface"
        )
    if declined and not opt_out_reason.strip():
        raise ValueError("--except needs --reason so the opt-out is self-explaining")

    forced = {i.upper() for i in force_enable_ids}
    rows = scan(adr_dir)
    result: Dict = {"enabled": [], "opted_out": [], "unchanged": [], "dry_run": dry_run}
    # The set the judge will actually evaluate once this migration lands. The
    # per-row lists above only show what THIS run changes, and that framing has
    # misled an operator before: a dry-run reading "6 enabled, 0 unbounded" on a
    # repository that already carried 58 enabled unscoped ADRs looks cost-free,
    # while the post-migration pass makes one isolated model call per unscoped
    # ADR on every commit. The totals answer the question the operator is
    # actually asking: what will judging cost after I accept this?
    judged_after = 0
    unbounded_after = 0

    def count_judged(row: Dict) -> None:
        nonlocal judged_after, unbounded_after
        judged_after += 1
        if row["unbounded_scope"]:
            unbounded_after += 1

    for row in rows:
        adr, path = row["adr"], Path(row["path"])
        if (
            row["proposal"] == "mark-no-code-surface"
            and adr not in forced
            and adr not in declined
        ):
            if not dry_run:
                opt_out(path, NO_CODE_SURFACE_REASON)
            result["opted_out"].append(
                {"adr": adr, "reason": NO_CODE_SURFACE_REASON, "proposed": True}
            )
            continue
        if adr in no_surface:
            if not dry_run:
                opt_out(path, NO_CODE_SURFACE_REASON)
            result["opted_out"].append({"adr": adr, "reason": NO_CODE_SURFACE_REASON})
            continue
        if adr in declined:
            if not dry_run:
                opt_out(path, opt_out_reason.strip())
            result["opted_out"].append({"adr": adr, "reason": opt_out_reason.strip()})
            continue
        if row["state"] == STATE_LEGACY_OFF:
            if not dry_run:
                enable(path)
            result["enabled"].append(
                {
                    "adr": adr,
                    "rules": row["rules"],
                    "unbounded_scope": row["unbounded_scope"],
                }
            )
            count_judged(row)
            continue
        if row["state"] == STATE_ENABLED:
            count_judged(row)
        result["unchanged"].append({"adr": adr, "state": row["state"]})
    result["summary"] = {
        "judged_after": judged_after,
        "unbounded_after": unbounded_after,
    }
    return result
