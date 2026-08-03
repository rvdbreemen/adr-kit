"""Read the git history for decision-shaped evidence (spec R1, TASK-80).

The bootstrap scanners walk the working tree, which shows what the project is.
The history shows how it got that way -- and the *why* of an existing codebase
lives there, in the commit that says "switch to X because Y", in the merge that
introduced a subsystem, and in the file everybody keeps rewriting.

`.git/**` sits in the scanner's skip list, so none of that reached the candidate
set. This module is the missing half. It is deliberately separate from the tree
scanners for one reason: its findings are *weaker*. A commit subject is a claim
someone typed once, in a hurry, possibly wrong, and possibly about a decision
that was reversed three commits later. A file that exists is a fact. Mixing the
two into one undifferentiated list would let the weaker evidence borrow the
authority of the stronger, so every candidate here is stamped `source:
"history"` and carries the commit it came from.

Everything fails open. No git, no repository, a shallow clone, a repository with
one commit -- each yields an empty list, never an error. A bootstrap scan that
refuses to run because the history is thin is worse than one that scans what it
can and says so.
"""

from __future__ import annotations

import re
import shutil
import subprocess
from collections import Counter
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# How far back to look. A bootstrap scan wants the shape of the project, not an
# exhaustive audit, and every additional thousand commits buys less signal than
# the last. Overridable by the caller.
DEFAULT_MAX_COMMITS = 2000

# A subject line reads as decision-shaped when it announces a change of
# direction rather than a change of code. These are matched on the subject only:
# a commit body is where people paste stack traces.
DECISION_SUBJECT_RE = re.compile(
    r"(?ix)\b("
    r"switch(?:ed|ing)?\s+to|migrat(?:e|ed|ing)\s+to|replac(?:e|ed|ing)\s+\w+\s+with|"
    r"mov(?:e|ed|ing)\s+(?:to|off)|drop(?:ped|ping)?\s+support|"
    r"adopt(?:ed|ing)?|standardi[sz]e(?:d|ing)?\s+on|"
    r"rewrite|rewrote|revert(?:ed)?\s+to|"
    r"introduc(?:e|ed|ing)\s+\w+|deprecat(?:e|ed|ing)|"
    r"choose|chose|decide[d]?\s+to"
    r")\b"
)

# Churn only means something above a floor. Two edits to a file over five years
# is not a contested area, it is a file.
CHURN_MIN_COMMITS = 8
CHURN_TOP_N = 8

# Merge subjects that say nothing. "Merge branch 'main'" is bookkeeping.
UNINTERESTING_MERGE_RE = re.compile(
    r"(?i)^merge\s+(?:branch|remote-tracking\s+branch|pull\s+request)\b"
)

SKIP_PATH_RE = re.compile(
    r"(?i)(^|/)(\.git|node_modules|vendor|dist|build|__pycache__|"
    r"\.venv|venv|target|coverage)(/|$)"
)


def _git(root: Path, args: List[str], timeout: int = 30) -> Optional[str]:
    """Run a read-only git command. Any failure is None, never an exception."""
    if shutil.which("git") is None:
        return None
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=str(root),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if result.returncode != 0:
        return None
    return result.stdout


def is_git_repository(root: Path) -> bool:
    out = _git(root, ["rev-parse", "--is-inside-work-tree"], timeout=10)
    return bool(out and out.strip() == "true")


def _commits(root: Path, max_commits: int) -> List[Tuple[str, str, str]]:
    """(short sha, iso date, subject) newest first. Empty on any problem."""
    out = _git(
        root,
        ["log", f"--max-count={max_commits}", "--no-merges",
         "--date=short", "--pretty=format:%h\x1f%ad\x1f%s"],
    )
    if not out:
        return []
    rows: List[Tuple[str, str, str]] = []
    for line in out.splitlines():
        parts = line.split("\x1f")
        if len(parts) == 3 and parts[2].strip():
            rows.append((parts[0], parts[1], parts[2].strip()))
    return rows


def scan_decision_subjects(root: Path, max_commits: int) -> List[Dict]:
    """Commits whose subject announces a change of direction."""
    candidates: List[Dict] = []
    seen_subjects: set[str] = set()
    for sha, date, subject in _commits(root, max_commits):
        if UNINTERESTING_MERGE_RE.match(subject):
            continue
        if not DECISION_SUBJECT_RE.search(subject):
            continue
        # Conventional-commit prefixes repeat forever; dedupe on the payload.
        normalized = re.sub(r"^\w+(\([^)]*\))?!?:\s*", "", subject).casefold()
        if normalized in seen_subjects:
            continue
        seen_subjects.add(normalized)
        candidates.append(
            {
                "id": f"history-subject-{sha}",
                "title": subject,
                "decision_type": "history-claim",
                "source": "history",
                "evidence_files": [],
                "details": {
                    "commit": sha,
                    "date": date,
                    "why_this_is_weak": (
                        "A commit subject is a claim typed once. It may be wrong, "
                        "and the decision may have been reversed since. Confirm "
                        "against the code before writing an ADR from it."
                    ),
                },
            }
        )
    return candidates


def scan_churn(root: Path, max_commits: int) -> List[Dict]:
    """Files rewritten often enough to suggest a contested design area."""
    out = _git(
        root,
        ["log", f"--max-count={max_commits}", "--no-merges",
         "--name-only", "--pretty=format:"],
    )
    if not out:
        return []
    counter: Counter = Counter()
    for line in out.splitlines():
        path = line.strip()
        if not path or SKIP_PATH_RE.search(path):
            continue
        counter[path] += 1

    hot = [(path, n) for path, n in counter.most_common(CHURN_TOP_N) if n >= CHURN_MIN_COMMITS]
    if not hot:
        return []
    return [
        {
            "id": "history-churn",
            "title": (
                "Some files are rewritten far more often than the rest, which "
                "usually marks a design nobody has settled."
            ),
            "decision_type": "history-signal",
            "source": "history",
            "evidence_files": [path for path, _ in hot],
            "details": {
                "churn": [{"path": path, "commits": n} for path, n in hot],
                "window_commits": max_commits,
                "why_this_is_weak": (
                    "Churn shows where the effort went, not what was decided. "
                    "It points at a question worth asking, not at an answer."
                ),
            },
        }
    ]


def scan_first_appearance(root: Path, paths: List[str]) -> List[Dict]:
    """When each dependency or tooling marker first entered the repository.

    The order in which subsystems appeared is the closest thing a repository
    has to a timeline of its decisions, and it costs one `git log` per path.
    """
    rows: List[Dict] = []
    for path in paths:
        out = _git(
            root,
            ["log", "--diff-filter=A", "--follow", "--date=short",
             "--pretty=format:%h\x1f%ad\x1f%s", "--max-count=1", "--", path],
        )
        if not out or not out.strip():
            continue
        parts = out.strip().splitlines()[0].split("\x1f")
        if len(parts) != 3:
            continue
        rows.append({"path": path, "commit": parts[0], "date": parts[1], "subject": parts[2]})
    if not rows:
        return []
    rows.sort(key=lambda row: row["date"])
    return [
        {
            "id": "history-first-appearance",
            "title": (
                "The order in which the project's tooling and dependencies "
                "arrived, which is the closest thing to a timeline of its decisions."
            ),
            "decision_type": "history-signal",
            "source": "history",
            "evidence_files": [row["path"] for row in rows],
            "details": {"arrivals": rows},
        }
    ]


def scan_history(
    root: Path,
    tracked_paths: Optional[List[str]] = None,
    max_commits: int = DEFAULT_MAX_COMMITS,
) -> Dict:
    """Return {"candidates": [...], "available": bool, "reason": str|None}.

    Never raises. A repository without git, without history, or with git
    unavailable yields an empty candidate list and a reason -- a bootstrap scan
    that refuses to run because the history is thin is worse than one that
    scans what it can and says which half is missing.
    """
    if shutil.which("git") is None:
        return {"candidates": [], "available": False, "reason": "git is not on PATH"}
    if not is_git_repository(root):
        return {"candidates": [], "available": False, "reason": "not a git repository"}
    if not _commits(root, 1):
        return {"candidates": [], "available": False, "reason": "no commits to read"}

    candidates: List[Dict] = []
    candidates.extend(scan_decision_subjects(root, max_commits))
    candidates.extend(scan_churn(root, max_commits))
    if tracked_paths:
        candidates.extend(scan_first_appearance(root, tracked_paths))
    return {"candidates": candidates, "available": True, "reason": None}
