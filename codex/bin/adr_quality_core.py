"""adr_quality_core: the four-gate ADR quality scorer, separated from its CLI.

`bin/adr-quality` was both the scorer and the command, and that made the scorer
unreachable. Readiness computed its own "quality" from three booleans -- is
there decision text, is there a verified_in, are the open questions closed --
while the real weighted scorer sat behind a command line that only
`accept --auto` ever invoked. So a vague ADR and a sharp one were queued for
grilling identically, and the evaluator that could have told them apart was
never asked.

Moving the scoring here makes it importable, which is what puts it on a shipped
path: readiness reads it in-process, the guardian queue ranks on it, and
`bin/adr-quality` becomes the rendering shell it always should have been.
Nothing about the scores changed in the move.
"""

from __future__ import annotations

import importlib.machinery
import importlib.util
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

_BIN_DIR = Path(__file__).resolve().parent


def _load_sibling(name: str):
    """Import bin/<name>.py by explicit path, WITHOUT touching sys.path.

    SEC-HIGH (TASK-62): `sys.path.insert(0, _BIN_DIR)` put this directory ahead
    of the standard library for every import, so a module committed next to
    this script executed as code -- and it re-added the very directory
    CPython's -P / PYTHONSAFEPATH removes. Siblings are registered in
    sys.modules under their bare name, so the plain `from adr_* import ...`
    statements below (and the lazy ones inside functions) resolve from the
    cache instead of the path. bin/adr-judge carries the full rationale.
    """
    cached = sys.modules.get(name)
    if cached is not None:
        return cached
    loader = importlib.machinery.SourceFileLoader(name, str(_BIN_DIR / f"{name}.py"))
    spec = importlib.util.spec_from_loader(name, loader)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    loader.exec_module(module)
    return module


_load_sibling("adr_format")

from adr_format import detect_profile, required_headings, section_text


REQUIRED_SECTIONS = [
    "## Status",
    "## Context",
    "## Decision",
    "## Alternatives Considered",
    "## Consequences",
    "## Related Decisions",
    "## References",
]

VALID_STATUSES = {
    "proposed", "accepted", "deprecated", "superseded", "amended",
}

ADR_ID_RE = re.compile(r"(?i)^ADR-(\d{1,4})-")
ADR_REF_RE = re.compile(r"\bADR-(\d{3})\b", re.IGNORECASE)
METRICS_RE = re.compile(r"\d+\s*(ms|MB|GB|KB|%|req|s|hours?)\b")
FILE_LINE_RE = re.compile(r"[\w./]+:\d+")
EXTERNAL_LINK_RE = re.compile(r"https?://")
# Unified vague-words set; identical to bin/adr-lint's check_quality_gate().
VAGUE_WORDS_RE = re.compile(
    r"\b(appropriate|somehow|maybe|possibly|might|could|"
    r"should\s+consider|might\s+consider)\b",
    re.IGNORECASE,
)

# Precompiled section-heading patterns: one regex per required section, used
# for both presence checks (gate_completeness) and slicing (_section_text).
_SECTION_PRESENCE_RE: Dict[str, re.Pattern] = {
    section: re.compile(r"^" + re.escape(section) + r"\b", re.MULTILINE)
    for section in REQUIRED_SECTIONS
}
_SECTION_BODY_RE: Dict[str, re.Pattern] = {
    section: re.compile(
        r"^" + re.escape(section) + r"\s*$\n(.*?)(?=\n##\s+|\Z)",
        re.MULTILINE | re.DOTALL,
    )
    for section in REQUIRED_SECTIONS
}

# Acronym scanning (gate_clarity).
_ACRO_RE = re.compile(r"\b([A-Z]{2,})\b")
_ACRO_DEFINED_RE = re.compile(
    r"\b([A-Z]{2,})\b\s*(?:\(|stands\s+for|means\b|\:)"
)


# ---------------------------------------------------------------------------
# Structured quality issues
# ---------------------------------------------------------------------------

ISSUE_MESSAGES: Dict[str, str] = {
    "MISSING_SECTION": "Required section missing: {detail}",
    "DECISION_TOO_SHORT":
        "Decision section too short ({detail} chars, minimum 100)",
    "TOO_FEW_ALTERNATIVES":
        "Too few alternatives considered ({detail} found, minimum 2)",
    "CONSEQUENCES_EMPTY": "Consequences section is empty",
    "NO_REFERENCES": "References section is empty or contains only 'None'",
    "NO_MEASUREMENTS":
        "No quantitative measurements found (e.g., '50 ms', '10 MB', '30%')",
    "NO_EXTERNAL_LINK":
        "No external links found in the document; add https:// references",
    "NO_FILE_LINE_REF":
        "No file:line references found (e.g., 'src/main.py:42')",
    "VAGUE_LANGUAGE": "Decision section uses vague language: {detail}",
    "NO_TITLE": "No ADR title heading found (expected '# ADR-NNN Title')",
    "ACRONYM_UNEXPLAINED": "More than 3 undefined acronyms: {detail}",
    "CONTEXT_TOO_SHORT":
        "Context section too short ({detail} chars, minimum 50)",
    "NO_RELATED_DECISIONS":
        "Related Decisions is empty or 'None'; reference related ADRs "
        "(or explain why there are none)",
    "ORPHAN_RELATED_ID": "Referenced ADRs do not exist: {detail}",
    "INVALID_STATUS":
        "Status section has no valid status value "
        "(expected one of: {detail})",
}

# Severity ordering for triage display (lower = more severe).
SEVERITY_ORDER: Dict[str, int] = {"high": 0, "medium": 1, "low": 2}


@dataclass
class QualityIssue:
    """Structured issue produced by a quality gate.

    ``code`` is a stable machine-readable identifier (see ISSUE_MESSAGES);
    ``detail`` is free-form context interpolated into the human message.
    """

    code: str
    detail: str = ""
    severity: str = "medium"  # "high" | "medium" | "low"

    def message(self) -> str:
        template = ISSUE_MESSAGES.get(self.code, self.code)
        try:
            return template.format(detail=self.detail)
        except (KeyError, IndexError):
            return template

    def to_dict(self) -> Dict:
        return {
            "code": self.code,
            "detail": self.detail,
            "severity": self.severity,
            "message": self.message(),
        }


def _section_text(content: str, heading: str) -> str:
    """Extract text of a markdown section (up to the next ## heading or EOF)."""
    role = {
        "## Status": "status",
        "## Context": "context",
        "## Decision": "decision",
        "## Alternatives Considered": "alternatives",
        "## Consequences": "consequences",
        "## Related Decisions": "related",
        "## References": "references",
    }.get(heading)
    if role:
        return section_text(content, role)
    pat = _SECTION_BODY_RE.get(heading)
    if pat is None:
        # Fallback for any heading not in REQUIRED_SECTIONS.
        pat = re.compile(
            r"^" + re.escape(heading) + r"\s*$\n(.*?)(?=\n##\s+|\Z)",
            re.MULTILINE | re.DOTALL,
        )
    m = pat.search(content)
    return m.group(1) if m else ""


def gate_completeness(content: str) -> Dict:
    """Gate 1: Completeness (0.0-1.0).

    Checks:
    - All 7 required sections present (each missing: -1/7)
    - ## Decision section > 100 chars (else: -0.1)
    - ## Alternatives Considered contains >= 2 bullet/heading items (else: -0.15)
    - ## Consequences section present and not empty (else: -0.1)

    Returns: {score: float, issues: List[QualityIssue], checks: Dict[str, bool]}
    """
    issues: List[QualityIssue] = []
    checks: Dict[str, bool] = {}

    # Check all required sections present
    missing_sections = []
    profile = detect_profile(content)
    effective_sections = (
        required_headings(profile)
        if profile in {"madr", "nygard", "canonical"}
        else REQUIRED_SECTIONS
    )
    for section in effective_sections:
        pattern = _SECTION_PRESENCE_RE.get(section) or re.compile(
            r"^" + re.escape(section) + r"\b", re.MULTILINE
        )
        present = bool(pattern.search(content))
        checks[f"section_{section.replace('## ', '').replace(' ', '_').lower()}"] = present
        if not present:
            missing_sections.append(section)

    score = 1.0
    n_missing = len(missing_sections)
    if n_missing > 0:
        score -= n_missing / 7.0
        missing_names = ", ".join(s.replace("## ", "") for s in missing_sections)
        issues.append(QualityIssue(
            code="MISSING_SECTION",
            detail=missing_names,
            severity="high",
        ))

    # Check Decision section length
    decision_text = _section_text(content, "## Decision")
    decision_len = len(decision_text.strip())
    decision_long_enough = decision_len > 100
    checks["decision_length_ok"] = decision_long_enough
    if not decision_long_enough:
        score -= 0.1
        issues.append(QualityIssue(
            code="DECISION_TOO_SHORT",
            detail=str(decision_len),
            severity="medium",
        ))

    # Check Alternatives Considered has >= 2 items
    alternatives_text = _section_text(content, "## Alternatives Considered")
    list_items = re.findall(r"^[-*]\s+\S", alternatives_text, re.MULTILINE)
    heading_items = re.findall(r"^###\s+\S", alternatives_text, re.MULTILINE)
    total_alternatives = len(list_items) + len(heading_items)
    enough_alternatives = total_alternatives >= 2
    checks["alternatives_count_ok"] = enough_alternatives
    if not enough_alternatives:
        score -= 0.15
        issues.append(QualityIssue(
            code="TOO_FEW_ALTERNATIVES",
            detail=str(total_alternatives),
            severity="medium",
        ))

    # Check Consequences present and not empty
    consequences_text = _section_text(content, "## Consequences")
    consequences_ok = bool(consequences_text.strip())
    checks["consequences_not_empty"] = consequences_ok
    if not consequences_ok:
        score -= 0.1
        issues.append(QualityIssue(
            code="CONSEQUENCES_EMPTY",
            severity="high",
        ))

    score = max(0.0, min(1.0, score))
    return {"score": score, "issues": issues, "checks": checks}


def gate_evidence(content: str) -> Dict:
    """Gate 2: Evidence (0.0-1.0).

    Checks:
    - ## References section contains >= 1 non-'None' entry: +0.4
    - Number/measurement present (regex r'\\d+\\s*(ms|MB|GB|KB|%|req|s|hours?)'): +0.3
    - External link present (http:// or https://): +0.2
    - file:line reference present: +0.1

    Returns: {score: float, issues: List[str], checks: Dict[str, bool]}
    """
    issues: List[QualityIssue] = []
    checks: Dict[str, bool] = {}

    # Check References section has at least 1 non-None entry
    refs_text = _section_text(content, "## References")
    refs_lines = [
        ln.strip() for ln in refs_text.splitlines()
        if ln.strip() and ln.strip().lower() not in ("none.", "none", "-")
    ]
    has_references = bool(refs_lines)
    checks["references_present"] = has_references
    score = 0.0
    if has_references:
        score += 0.4
    else:
        issues.append(QualityIssue(code="NO_REFERENCES", severity="high"))

    # Check for metrics/measurements in the whole document
    has_metrics = bool(METRICS_RE.search(content))
    checks["metrics_present"] = has_metrics
    if has_metrics:
        score += 0.3
    else:
        issues.append(QualityIssue(code="NO_MEASUREMENTS", severity="low"))

    # Check for external links
    has_external_link = bool(EXTERNAL_LINK_RE.search(content))
    checks["external_link_present"] = has_external_link
    if has_external_link:
        score += 0.2
    else:
        issues.append(QualityIssue(code="NO_EXTERNAL_LINK", severity="low"))

    # Check for file:line references
    has_file_line = bool(FILE_LINE_RE.search(content))
    checks["file_line_reference_present"] = has_file_line
    if has_file_line:
        score += 0.1
    else:
        issues.append(QualityIssue(code="NO_FILE_LINE_REF", severity="low"))

    score = max(0.0, min(1.0, score))
    return {"score": score, "issues": issues, "checks": checks}


def gate_clarity(content: str) -> Dict:
    """Gate 3: Clarity (0.0-1.0).

    Checks:
    - ## Decision section has no vague language ('might', 'maybe', 'possibly',
      'could', 'should consider'): vague_words check
    - ADR has a title (# ADR-NNN title present): +0.3
    - Acronyms defined: check if all-caps words (>=2 letters) appear at least once
      with a definition pattern. If > 3 undefined acronyms: -0.2
    - ## Context section > 50 chars: +0.2

    Returns: {score: float, issues: List[str], checks: Dict[str, bool]}
    """
    issues: List[QualityIssue] = []
    checks: Dict[str, bool] = {}

    score = 0.5  # base score

    # Check Decision section for vague language
    decision_text = _section_text(content, "## Decision")
    has_vague = bool(VAGUE_WORDS_RE.search(decision_text))
    checks["no_vague_language"] = not has_vague
    if has_vague:
        vague_found = VAGUE_WORDS_RE.findall(decision_text)
        issues.append(QualityIssue(
            code="VAGUE_LANGUAGE",
            detail=", ".join(repr(w) for w in vague_found[:5]),
            severity="medium",
        ))
        score -= 0.15

    # Check ADR has a title heading
    has_title = bool(re.search(r"^#\s+ADR-\d+", content, re.MULTILINE | re.IGNORECASE))
    checks["has_title"] = has_title
    if has_title:
        score += 0.3
    else:
        issues.append(QualityIssue(code="NO_TITLE", severity="high"))

    # Check acronyms are defined (all-caps words >= 2 letters).
    # Stopwords that are definitely not acronyms.
    acro_stopwords = frozenset({
        "OK", "TO", "BY", "AS", "IS", "ON", "OR", "AN", "AT", "IN", "OF",
        "IF", "DO", "NO", "SO", "UP", "US", "WE", "MY", "IT",
        "ADR", "ID",  # ADR is always defined in the context of this tool
    })
    # Words followed by definition patterns: '(', 'stands for', 'means', ':'
    defined_acros = {m.group(1) for m in _ACRO_DEFINED_RE.finditer(content)}

    undefined_acros = set()
    for m in _ACRO_RE.finditer(content):
        acro = m.group(1)
        if acro not in acro_stopwords and acro not in defined_acros:
            undefined_acros.add(acro)

    acros_ok = len(undefined_acros) <= 3
    checks["acronyms_defined"] = acros_ok
    if not acros_ok:
        score -= 0.2
        issues.append(QualityIssue(
            code="ACRONYM_UNEXPLAINED",
            detail=", ".join(sorted(undefined_acros)[:5]),
            severity="low",
        ))

    # Check Context section > 50 chars
    context_text = _section_text(content, "## Context")
    context_len = len(context_text.strip())
    context_ok = context_len > 50
    checks["context_sufficient"] = context_ok
    if context_ok:
        score += 0.2
    else:
        issues.append(QualityIssue(
            code="CONTEXT_TOO_SHORT",
            detail=str(context_len),
            severity="medium",
        ))

    score = max(0.0, min(1.0, score))
    return {"score": score, "issues": issues, "checks": checks}


def gate_consistency(content: str, adr_dir: Optional[Path] = None) -> Dict:
    """Gate 4: Consistency (0.0-1.0).

    Checks:
    - ## Related Decisions section not empty (not just 'None.'): +0.4
    - If adr_dir given: check if mentioned ADR-NNN numbers exist: +0.3
    - ## Status section contains a valid status value: +0.3

    Returns: {score: float, issues: List[str], checks: Dict[str, bool]}
    """
    issues: List[QualityIssue] = []
    checks: Dict[str, bool] = {}

    score = 0.0

    # Check Related Decisions not empty
    related_text = _section_text(content, "## Related Decisions")
    related_lines = [
        ln.strip() for ln in related_text.splitlines()
        if ln.strip() and ln.strip().lower() not in ("none.", "none", "-")
    ]
    has_related = bool(related_lines)
    checks["related_decisions_present"] = has_related
    if has_related:
        score += 0.4
    else:
        issues.append(QualityIssue(
            code="NO_RELATED_DECISIONS",
            severity="medium",
        ))

    # Check if mentioned ADR references exist in adr_dir
    mentioned_adrs = set(ADR_REF_RE.findall(content))
    if adr_dir and adr_dir.is_dir() and mentioned_adrs:
        existing_nums = set()
        for f in adr_dir.glob("ADR-*.md"):
            m = re.match(r"(?i)ADR-(\d+)-", f.name)
            if m:
                existing_nums.add(int(m.group(1)))
        missing_refs = [
            f"ADR-{num}" for num in sorted(mentioned_adrs)
            if int(num) not in existing_nums
        ]
        refs_valid = not missing_refs
        checks["referenced_adrs_exist"] = refs_valid
        if refs_valid:
            score += 0.3
        else:
            issues.append(QualityIssue(
                code="ORPHAN_RELATED_ID",
                detail=", ".join(missing_refs),
                severity="high",
            ))
    elif mentioned_adrs:
        # ADR references found but can't verify — give partial credit
        checks["referenced_adrs_exist"] = True
        score += 0.3
    else:
        checks["referenced_adrs_exist"] = False
        # No ADR references mentioned — don't add to score if no related decisions
        if has_related:
            score += 0.3

    # Check Status section for a valid status value
    status_text = _section_text(content, "## Status")
    status_match = re.search(r"\b([A-Za-z]+)\b", status_text)
    has_valid_status = False
    if status_match:
        status_word = status_match.group(1).lower()
        has_valid_status = status_word in VALID_STATUSES
    checks["valid_status"] = has_valid_status
    if has_valid_status:
        score += 0.3
    else:
        issues.append(QualityIssue(
            code="INVALID_STATUS",
            detail=", ".join(sorted(VALID_STATUSES)),
            severity="high",
        ))

    score = max(0.0, min(1.0, score))
    return {"score": score, "issues": issues, "checks": checks}


def _grade(overall: float) -> str:
    if overall >= 0.85:
        return "A"
    if overall >= 0.70:
        return "B"
    if overall >= 0.55:
        return "C"
    return "D"


def _extract_adr_id(adr_path: Path) -> str:
    m = ADR_ID_RE.match(adr_path.name)
    if m:
        return f"ADR-{int(m.group(1)):03d}"
    return adr_path.stem


# Per-code recommendation strings. Driven by the structured issue code rather
# than human-text matching, so wording changes don't silently break behaviour.
_RECOMMENDATIONS_BY_CODE: Dict[str, str] = {
    "MISSING_SECTION": "Add the missing required sections listed above",
    "DECISION_TOO_SHORT":
        "Expand ## Decision to > 100 characters explaining the rationale",
    "TOO_FEW_ALTERNATIVES":
        "Add at least 2 alternatives in ## Alternatives Considered "
        "(including 'do nothing')",
    "CONSEQUENCES_EMPTY":
        "Fill in ## Consequences with benefits, trade-offs, and risks",
    "NO_REFERENCES":
        "Add at least one entry to ## References (issue, file, or external link)",
    "NO_MEASUREMENTS":
        "Add measurements to ## Consequences (e.g., '50 ms', '10 MB', '30%')",
    "NO_EXTERNAL_LINK": "Add at least one https:// link in ## References",
    "NO_FILE_LINE_REF":
        "Add a file:line reference (e.g., 'src/main.py:42') in ## References",
    "VAGUE_LANGUAGE":
        "Replace vague language in ## Decision with a concrete, "
        "declarative statement",
    "NO_TITLE": "Add a title heading '# ADR-NNN Title' as the first line",
    "ACRONYM_UNEXPLAINED":
        "Define acronyms on first use, e.g., 'REST (Representational "
        "State Transfer)'",
    "CONTEXT_TOO_SHORT":
        "Expand ## Context to > 50 chars; explain the problem and constraints",
    "NO_RELATED_DECISIONS":
        "Reference related ADRs in ## Related Decisions "
        "(or state 'None' with explanation)",
    "ORPHAN_RELATED_ID":
        "Verify that referenced ADR numbers exist in the docs/adr/ directory",
    "INVALID_STATUS":
        "Set a valid status in ## Status: Proposed, Accepted, Deprecated, "
        "Superseded, or Amended",
}


def _recommendations_from_issues(issues: List[QualityIssue]) -> List[str]:
    """Generate concrete action items from structured issue codes."""
    recs: List[str] = []
    for issue in issues:
        rec = _RECOMMENDATIONS_BY_CODE.get(issue.code)
        if rec is None:
            recs.append(issue.message())
        else:
            recs.append(rec)
    return recs


def score_adr_quality(content: str, adr_path: Path) -> Dict:
    """Calculate composite quality score.

    Returns:
    {
      "overall": float,   # weighted: completeness*0.4 + evidence*0.2 + clarity*0.2 + consistency*0.2
      "gates": {
        "completeness": {"score": float, "issues": [...], "checks": {...}},
        "evidence": {"score": float, "issues": [...], "checks": {...}},
        "clarity": {"score": float, "issues": [...], "checks": {...}},
        "consistency": {"score": float, "issues": [...], "checks": {...}},
      },
      "issues": List[str],         # all issues combined, sorted by severity
      "recommendations": List[str],  # concrete action items
      "grade": str,                 # "A" (>=0.85), "B" (>=0.70), "C" (>=0.55), "D" (<0.55)
    }
    """
    adr_dir = adr_path.parent if adr_path.parent.is_dir() else None

    comp = gate_completeness(content)
    evid = gate_evidence(content)
    clar = gate_clarity(content)
    cons = gate_consistency(content, adr_dir)

    overall = (
        comp["score"] * 0.4
        + evid["score"] * 0.2
        + clar["score"] * 0.2
        + cons["score"] * 0.2
    )
    overall = max(0.0, min(1.0, round(overall, 4)))

    # Single-pass triage: collect all QualityIssues across the four gates,
    # then sort by severity (high -> medium -> low). The previous 12-way
    # comprehension was O(4 * 3 * n) and re-evaluated _severity_label
    # repeatedly; this is O(n log n) with a tiny constant.
    all_issues: List[QualityIssue] = [
        issue
        for gate_result in (comp, evid, clar, cons)
        for issue in gate_result["issues"]
    ]
    all_issues.sort(key=lambda i: SEVERITY_ORDER.get(i.severity, 99))

    return {
        "overall": overall,
        "grade": _grade(overall),
        "gates": {
            "completeness": comp,
            "evidence": evid,
            "clarity": clar,
            "consistency": cons,
        },
        "issues": all_issues,
        "recommendations": _recommendations_from_issues(all_issues),
    }


# The threshold `bin/adr-quality` has always exited 1 below. Named here so the
# queue and the readiness report agree with the command rather than each
# carrying their own number.
QUALITY_THRESHOLD = 0.70


def score_path(path: Path) -> Optional[Dict]:
    """Score one ADR file. None when it cannot be read -- never raises.

    Callers on a queue or a hook path must not fail because one record is
    unreadable; adr-lint is what reports a malformed ADR.
    """
    try:
        content = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    try:
        return score_adr_quality(content, path)
    except (ValueError, KeyError, re.error):
        return None


def score_directory(adr_dir: Path, statuses: Optional[List[str]] = None) -> Dict[str, Dict]:
    """Score every ADR in a directory, keyed by ADR id.

    `statuses`, when given, restricts the scan -- the guardian evaluates
    Accepted records on its own cadence so quality decay stays visible instead
    of frozen at the moment of acceptance.
    """
    _load_sibling("adr_schema")
    _load_sibling("adr_catalog")
    from adr_catalog import adr_status, discover_adr_files

    wanted = {status.casefold() for status in statuses} if statuses else None
    scores: Dict[str, Dict] = {}
    for path in discover_adr_files(adr_dir):
        try:
            content = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if wanted is not None:
            status = (adr_status(content) or "").strip().casefold()
            if status not in wanted:
                continue
        try:
            result = score_adr_quality(content, path)
        except (ValueError, KeyError, re.error):
            continue
        scores[_extract_adr_id(path)] = result
    return scores
