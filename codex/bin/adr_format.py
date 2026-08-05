"""Shared semantic ADR body profiles.

Profiles vary human-facing headings while adr-kit metadata, status history,
relationships, references, and Enforcement remain invariant.  The module is
stdlib-only so every bundled CLI and generated client payload can import it.
"""

from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Optional, Tuple


DEFAULT_PROFILE = "madr"
SUPPORTED_PROFILES = ("madr", "nygard", "canonical")
DETECTED_PROFILES = SUPPORTED_PROFILES + ("hybrid", "unknown")
LEGACY_PROFILES = ("y-statement", "tyree-akerman", "arc42")

PROFILE_CATALOG: Dict[str, Dict[str, object]] = {
    "madr": {
        "label": "MADR 4",
        "preferred": True,
        "template": "adr-template.madr.md",
        "best_for": (
            "Agent-assisted decisions that benefit from explicit drivers, "
            "options, outcome, trade-offs, and confirmation."
        ),
        "trade_off": "The most complete profile, but the longest to author.",
    },
    "nygard": {
        "label": "Nygard",
        "preferred": False,
        "template": "adr-template.nygard.md",
        "best_for": (
            "Concise human-written decisions centered on context, decision, "
            "and consequences."
        ),
        "trade_off": (
            "Faster to scan, with adr-kit extension sections retained for "
            "deterministic gates."
        ),
    },
    "canonical": {
        "label": "adr-kit canonical",
        "preferred": False,
        "template": "adr-template.canonical.md",
        "best_for": (
            "Existing adr-kit repositories and compatibility with the "
            "pre-v0.34 section layout."
        ),
        "trade_off": (
            "Maximum backward compatibility, with less explicit authoring "
            "guidance than MADR."
        ),
    },
}

PROFILE_HEADINGS: Dict[str, Dict[str, str]] = {
    "madr": {
        "status": "Status",
        "history": "Status History",
        "context": "Context and Problem Statement",
        "drivers": "Decision Drivers",
        "alternatives": "Considered Options",
        "decision": "Decision Outcome",
        "decision_contract": "Decision Contract",
        "consequences": "Consequences",
        "related": "Related Decisions",
        "references": "References",
        "enforcement": "Enforcement",
        "confirmation": "Confirmation",
        "open_questions": "Open Questions",
    },
    "nygard": {
        "status": "Status",
        "history": "Status History",
        "context": "Context",
        "drivers": "Decision Drivers",
        "alternatives": "Alternatives Considered",
        "decision": "Decision",
        "decision_contract": "Decision Contract",
        "consequences": "Consequences",
        "related": "Related Decisions",
        "references": "References",
        "enforcement": "Enforcement",
        "confirmation": "Confirmation",
        "open_questions": "Open Questions",
    },
    "canonical": {
        "status": "Status",
        "history": "Status History",
        "context": "Context",
        "drivers": "Decision Drivers",
        "alternatives": "Alternatives Considered",
        "decision": "Decision",
        "decision_contract": "Decision Contract",
        "consequences": "Consequences",
        "related": "Related Decisions",
        "references": "References",
        "enforcement": "Enforcement",
        "confirmation": "Confirmation",
        "open_questions": "Open Questions",
    },
}

REQUIRED_ROLES = (
    "status",
    "context",
    "decision",
    "alternatives",
    "consequences",
    "related",
    "references",
)

PROFILE_REQUIRED_ROLES = {
    "madr": REQUIRED_ROLES + ("drivers",),
    "nygard": REQUIRED_ROLES,
    "canonical": REQUIRED_ROLES,
}

_FORMAT_LINE_RE = re.compile(
    r"^\s*format\s*:\s*[\"']?([a-z-]+)[\"']?\s*$", re.IGNORECASE | re.MULTILINE
)
_STATUS_LINE_RE = re.compile(r"^\s*status\s*:", re.IGNORECASE | re.MULTILINE)
_CANONICAL_FILENAME_RE = re.compile(
    r"^ADR-\d{3,4}-[a-z0-9]+(?:-[a-z0-9]+)*\.md$",
    re.IGNORECASE,
)
_LEGACY_NUMBER_RE = re.compile(
    r"^(?:ADR[-_ ]?)?0*(\d{1,4})[-_. ]+(.+?)\.md$",
    re.IGNORECASE,
)
_HEADING_NUMBER_RE = re.compile(
    r"^#\s+(?:ADR[-_ ]?)?0*(\d{1,4})[.:\s-]+(.+?)\s*$",
    re.IGNORECASE | re.MULTILINE,
)
_TITLE_RE = re.compile(r"^#\s+(.+?)\s*$", re.MULTILINE)
_ARC42_RE = re.compile(
    r"^#{1,3}\s+(?:9(?:\.\d+)*[.:\s-]+)?architecture\s+decisions?\s*$",
    re.IGNORECASE | re.MULTILINE,
)
_TYREE_LABEL_RE = re.compile(
    r"^(?:#{1,6}\s+|\*\*)?"
    r"(issue|decision|status|group|assumptions|constraints|positions|"
    r"argument|implications|related decisions|related requirements|"
    r"related artifacts|related principles|notes)"
    r"(?:\*\*)?\s*:?\s*$",
    re.IGNORECASE | re.MULTILINE,
)


class AdrFormatError(ValueError):
    """Raised when a profile or document shape cannot be handled safely."""


def _validate_profile_catalog_contract() -> None:
    catalog_ids = tuple(PROFILE_CATALOG)
    if catalog_ids != SUPPORTED_PROFILES:
        raise AdrFormatError(
            "ADR profile catalog drift: expected "
            + ", ".join(SUPPORTED_PROFILES)
            + "; found "
            + ", ".join(catalog_ids)
        )
    preferred = tuple(
        profile
        for profile, metadata in PROFILE_CATALOG.items()
        if metadata.get("preferred") is True
    )
    if preferred != (DEFAULT_PROFILE,):
        raise AdrFormatError(
            f"ADR profile catalog must mark only {DEFAULT_PROFILE!r} as preferred"
        )


def profile_template_path(profile: object, template_dir: Path) -> Path:
    """Resolve one approved profile to its shipped template or fail closed."""
    _validate_profile_catalog_contract()
    normalized = normalize_profile(profile)
    template_name = str(PROFILE_CATALOG[normalized]["template"])
    path = template_dir / template_name
    if not path.is_file():
        raise AdrFormatError(
            f"shipped ADR profile {normalized!r} is unavailable: "
            f"missing template {path}"
        )
    return path


def profile_catalog(template_dir: Path) -> List[Dict[str, object]]:
    """Return the ordered, agent-readable catalog and installed availability."""
    _validate_profile_catalog_contract()
    catalog: List[Dict[str, object]] = []
    for profile in SUPPORTED_PROFILES:
        metadata = PROFILE_CATALOG[profile]
        path = template_dir / str(metadata["template"])
        catalog.append(
            {
                "id": profile,
                "label": metadata["label"],
                "preferred": metadata["preferred"],
                "template": str(path),
                "available": path.is_file(),
                "best_for": metadata["best_for"],
                "trade_off": metadata["trade_off"],
            }
        )
    return catalog


def normalize_profile(value: object, *, default: Optional[str] = None) -> str:
    if value is None or value == "":
        if default is None:
            raise AdrFormatError("ADR format profile is required")
        return default
    if not isinstance(value, str):
        raise AdrFormatError("ADR format profile must be a string")
    profile = value.strip().lower()
    if profile == "adr-kit":
        profile = "canonical"
    if profile not in SUPPORTED_PROFILES:
        raise AdrFormatError(
            f"unsupported ADR format {value!r}; choose one of: "
            + ", ".join(SUPPORTED_PROFILES)
        )
    return profile


def configured_profile(config: Dict, *, default: str = DEFAULT_PROFILE) -> str:
    template = config.get("template", {})
    if not isinstance(template, dict):
        raise AdrFormatError("config.template must be an object")
    return normalize_profile(template.get("profile"), default=default)


def _leading_frontmatter(text: str) -> str:
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return ""
    for index, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            return "\n".join(lines[1:index])
    return ""


def declared_profile(text: str) -> Optional[str]:
    raw = _leading_frontmatter(text)
    match = _FORMAT_LINE_RE.search(raw)
    if not match:
        return None
    value = match.group(1).lower()
    return "canonical" if value == "adr-kit" else value


def _lines_outside_fences(text: str) -> List[str]:
    output: List[str] = []
    fence: Optional[str] = None
    for line in text.splitlines():
        stripped = line.lstrip()
        marker = stripped[:3]
        if marker in {"```", "~~~"}:
            if fence is None:
                fence = marker
            elif marker == fence:
                fence = None
            continue
        if fence is None:
            output.append(line)
    return output


def h2_headings(text: str) -> List[str]:
    headings: List[str] = []
    for line in _lines_outside_fences(text):
        match = re.match(r"^##\s+(.+?)\s*#*\s*$", line)
        if match:
            headings.append(match.group(1).strip())
    return headings


def unresolved_open_questions(text: str) -> List[str]:
    """Return stable unresolved items from the optional Open Questions role."""
    section = section_text(text, "open_questions")
    if not section:
        return []
    questions: List[str] = []
    for raw_line in section.splitlines():
        line = raw_line.strip()
        if not line or line.startswith(("```", "<!--", "-->")):
            continue
        normalized = re.sub(r"^\s*[-*+]\s+", "", line).strip()
        if normalized.casefold().rstrip(".") in {
            "none",
            "no open questions",
            "no unresolved questions",
        }:
            continue
        if re.match(r"^\[[xX]\]\s+", normalized):
            continue
        if re.match(r"^(?:answered|resolved)\s*:", normalized, re.IGNORECASE):
            continue
        unchecked = re.match(r"^\[\s\]\s+(.+)$", normalized)
        if unchecked:
            candidate = unchecked.group(1)
        elif re.match(r"^[-*+]\s+", line) or normalized.endswith("?"):
            candidate = normalized
        else:
            continue
        candidate = re.sub(r"[`*_]", "", candidate)
        candidate = re.sub(r"\s+", " ", candidate).strip()
        if candidate:
            questions.append(candidate)
    return sorted(dict.fromkeys(questions), key=str.casefold)


def _normalise_question(raw: str) -> str:
    """One question's identity, independent of how it is marked up.

    The same text has to match across two revisions of a file, and between an
    unanswered `- [ ] Why X?` and its answered `- [x] Why X? — **Answered ...**`
    form. Markup and whitespace are noise for that comparison; the words are not.
    """
    text = re.sub(r"^\s*[-*+]\s+", "", raw.strip())
    text = re.sub(r"^\[[ xX]\]\s*", "", text)
    # Everything from the answer marker on belongs to the answer, not the question.
    text = re.split(r"\s+[—-]{1,2}\s+\*\*Answered\b", text)[0]
    text = re.sub(r"[`*_]", "", text)
    return re.sub(r"\s+", " ", text).strip()


def all_open_questions(text: str) -> "Dict[str, bool]":
    """Every question in the Open Questions role, mapped to whether it is answered.

    `unresolved_open_questions` deliberately drops answered items, which is right
    for "what still blocks acceptance" and useless for "what was here before".
    Telling an answered question from a deleted one is the whole point of the
    append-only rule (ADR-022): both leave the unresolved list empty, and only
    one of them preserved the reasoning.
    """
    section = section_text(text, "open_questions")
    if not section:
        return {}
    found: Dict[str, bool] = {}
    for raw_line in section.splitlines():
        line = raw_line.strip()
        if not line or line.startswith(("```", "<!--", "-->")):
            continue
        stripped = re.sub(r"^\s*[-*+]\s+", "", line).strip()
        if stripped.casefold().rstrip(".") in {
            "none",
            "no open questions",
            "no unresolved questions",
        }:
            continue
        answered = bool(re.match(r"^\[[xX]\]\s+", stripped))
        if not answered and not (
            re.match(r"^\[\s\]\s+", stripped)
            or re.match(r"^[-*+]\s+", line)
            or stripped.endswith("?")
        ):
            continue
        question = _normalise_question(line)
        if not question:
            continue
        # An answered form wins: a question listed twice, once each way, is
        # answered.
        found[question] = found.get(question, False) or answered
    return found


@lru_cache(maxsize=256)
def detect_profile(text: str) -> str:
    declared = declared_profile(text)
    if declared is not None:
        return declared if declared in SUPPORTED_PROFILES else "unknown"

    ordered_headings = h2_headings(text)
    headings = set(ordered_headings)
    madr_unique = {
        PROFILE_HEADINGS["madr"]["context"],
        PROFILE_HEADINGS["madr"]["alternatives"],
        PROFILE_HEADINGS["madr"]["decision"],
    }
    canonical_required = set(required_heading_names("canonical"))
    nygard_core = {"Status", "Context", "Decision", "Consequences"}

    madr_hits = len(madr_unique & headings)
    canonical_match = canonical_required.issubset(headings)
    nygard_match = nygard_core.issubset(headings)

    has_frontmatter_status = bool(_STATUS_LINE_RE.search(_leading_frontmatter(text)))
    if madr_hits >= 2 and (canonical_match or {"Context", "Decision"} <= headings):
        return "hybrid"
    if madr_hits >= 2 or (madr_hits >= 1 and has_frontmatter_status):
        return "madr"
    if canonical_match:
        # The extended Nygard profile deliberately shares canonical heading
        # names. Its defining order puts Consequences before Alternatives,
        # while the historical canonical profile does the reverse.
        consequences = ordered_headings.index("Consequences")
        alternatives = ordered_headings.index("Alternatives Considered")
        return "nygard" if consequences < alternatives else "canonical"
    if nygard_match:
        return "nygard"
    return "unknown"


def detect_legacy_profile(text: str) -> Optional[str]:
    """Identify common unsupported ADR families using conservative markers.

    Supported profiles win before this function is considered. The detectors
    intentionally require distinctive structures so ordinary Markdown is not
    mislabeled as a migration candidate.
    """
    if detect_profile(text) != "unknown":
        return None
    visible = "\n".join(_lines_outside_fences(text))
    lowered = visible.casefold()
    cursor = 0
    y_statement_markers = (
        ("in the context of",),
        ("facing",),
        (
            "we decided for",
            "we decided to",
            "we have decided for",
            "we have decided to",
        ),
        ("neglected",),
        ("to achieve",),
        ("accepting",),
    )
    y_statement = True
    for alternatives in y_statement_markers:
        positions = [
            lowered.find(marker, cursor)
            for marker in alternatives
            if lowered.find(marker, cursor) >= 0
        ]
        if not positions:
            y_statement = False
            break
        cursor = min(positions) + 1
    if y_statement:
        return "y-statement"

    labels = {match.casefold() for match in _TYREE_LABEL_RE.findall(visible)}
    tyree_distinctive = {
        "issue",
        "decision",
        "assumptions",
        "constraints",
        "positions",
        "argument",
        "implications",
    }
    if {"issue", "decision"} <= labels and len(labels & tyree_distinctive) >= 5:
        return "tyree-akerman"

    if _ARC42_RE.search(visible):
        return "arc42"
    return None


def classify_format(text: str) -> str:
    """Return a supported, legacy, hybrid, or unknown format classification."""
    profile = detect_profile(text)
    if profile != "unknown":
        return profile
    return detect_legacy_profile(text) or "unknown"


def is_canonical_filename(path: Path) -> bool:
    return bool(_CANONICAL_FILENAME_RE.fullmatch(path.name))


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.casefold()).strip("-")
    return slug or "decision"


def suggested_filename(path: Path, text: str) -> Optional[str]:
    """Suggest an adr-kit filename when a legacy number can be inferred."""
    number: Optional[int] = None
    title: Optional[str] = None

    filename_match = _LEGACY_NUMBER_RE.match(path.name)
    if filename_match:
        number = int(filename_match.group(1))
        title = filename_match.group(2)

    heading_match = _HEADING_NUMBER_RE.search(text)
    if heading_match:
        number = int(heading_match.group(1))
        title = heading_match.group(2)

    if number is None:
        return None
    if not title:
        title_match = _TITLE_RE.search(text)
        title = title_match.group(1) if title_match else "decision"
    return f"ADR-{number:03d}-{_slugify(title)}.md"


def migration_notice(
    text: str,
    path: Path,
    *,
    metadata_changed: bool = False,
    metadata_issues: Optional[List[str]] = None,
    migrate_command: str = "bin/adr-migrate",
) -> Optional[Dict]:
    """Build a read-only migration recommendation for one document.

    The result is deliberately data-only so lint, install, upgrade, and the
    migration CLI can render the same advice. No function in this module writes
    files.
    """
    classification = classify_format(text)
    issues = list(metadata_issues or [])
    canonical_name = is_canonical_filename(path)
    rename_to = None if canonical_name else suggested_filename(path, text)
    missing_sections: List[str] = []
    if classification in SUPPORTED_PROFILES:
        present = {item.casefold() for item in h2_headings(text)}
        missing_sections = [
            name
            for name in required_heading_names(classification)
            if name.casefold() not in present
        ]

    if (
        classification in SUPPORTED_PROFILES
        and not metadata_changed
        and not issues
        and canonical_name
        and not missing_sections
    ):
        return None

    quoted_path = '"' + str(path).replace('"', '\\"') + '"'
    quoted_command = '"' + migrate_command.replace('"', '\\"') + '"'
    command_prefix = f"python {quoted_command}"
    base = {
        "file": str(path),
        "detected_format": classification,
        "supported": classification in SUPPORTED_PROFILES,
        "metadata_change": metadata_changed,
        "metadata_issues": issues,
        "missing_sections": missing_sections,
        "rename_to": rename_to,
        "writes_automatically": False,
    }

    if classification in SUPPORTED_PROFILES and not issues:
        reasons: List[str] = []
        if metadata_changed:
            reasons.append("canonical metadata can be added deterministically")
        if missing_sections:
            reasons.append(
                "required extension sections can be added deterministically"
            )
        if not canonical_name:
            reasons.append("the filename needs adr-kit normalization")
        profile_option = f" --to-profile {classification}"
        return {
            **base,
            "action": "deterministic-preview",
            "deterministic": True,
            "message": (
                f"Detected supported {classification} ADR; "
                + "; ".join(reasons)
                + "."
            ),
            "preview_command": (
                f"{command_prefix} --dry-run{profile_option} {quoted_path}"
            ),
            "apply_command": (
                f"{command_prefix}{profile_option} {quoted_path}"
            ),
            "guided_command": None,
        }

    if classification in LEGACY_PROFILES:
        family = {
            "y-statement": "Y-Statement",
            "tyree-akerman": "Tyree/Akerman",
            "arc42": "arc42 decision section",
        }[classification]
        return {
            **base,
            "action": "guided-migration",
            "deterministic": False,
            "message": (
                f"Detected {family}; mapping its semantics requires review, "
                "so adr-kit will not guess or rewrite it automatically."
            ),
            "preview_command": None,
            "apply_command": None,
            "guided_command": f'/adr-kit:migrate {quoted_path}',
        }

    if classification == "hybrid":
        message = (
            "Detected a hybrid of supported ADR headings; select the actual "
            "source profile before conversion."
        )
    elif issues:
        message = (
            "Detected an ADR whose metadata cannot be normalized safely: "
            + "; ".join(issues)
        )
    else:
        message = (
            "ADR format is unknown; use guided migration to map its semantic "
            "sections without fabricating content."
        )
    return {
        **base,
        "action": "guided-migration",
        "deterministic": False,
        "message": message,
        "preview_command": None,
        "apply_command": None,
        "guided_command": f'/adr-kit:migrate {quoted_path}',
    }


def is_migration_candidate(path: Path, text: str) -> bool:
    """Return whether a Markdown file belongs in format discovery."""
    if path.name.casefold() in {"readme.md", "adr-index.md"}:
        return False
    if re.match(r"^ADR-\d{1,4}-.*\.md$", path.name, re.IGNORECASE):
        return True
    return classify_format(text) != "unknown"


def heading(profile: str, role: str) -> str:
    normalized = normalize_profile(profile)
    try:
        return PROFILE_HEADINGS[normalized][role]
    except KeyError as exc:
        raise AdrFormatError(f"unknown ADR semantic role: {role}") from exc


def required_heading_names(profile: str) -> List[str]:
    normalized = normalize_profile(profile)
    return [heading(normalized, role) for role in PROFILE_REQUIRED_ROLES[normalized]]


def required_headings(profile: str) -> List[str]:
    return [f"## {name}" for name in required_heading_names(profile)]


def profile_for_text(text: str, *, fallback: Optional[str] = None) -> str:
    profile = detect_profile(text)
    if profile in SUPPORTED_PROFILES:
        return profile
    if profile == "unknown" and fallback is not None:
        return normalize_profile(fallback)
    raise AdrFormatError(
        f"ADR body format is {profile}; add frontmatter format: "
        + " | ".join(SUPPORTED_PROFILES)
        + " or migrate the document"
    )


def section_text(
    text: str,
    role: str,
    *,
    profile: Optional[str] = None,
    tolerant: bool = True,
) -> str:
    profiles: List[str] = []
    if profile is not None:
        profiles.append(normalize_profile(profile))
    else:
        detected = detect_profile(text)
        if detected in SUPPORTED_PROFILES:
            profiles.append(detected)
    if tolerant:
        profiles.extend(p for p in SUPPORTED_PROFILES if p not in profiles)

    names: List[str] = []
    for item in profiles:
        name = heading(item, role)
        if name not in names:
            names.append(name)
    for name in names:
        match = re.search(
            rf"^##\s+{re.escape(name)}\s*$\n(.*?)(?=^##\s+|\Z)",
            text,
            re.IGNORECASE | re.MULTILINE | re.DOTALL,
        )
        if match:
            return match.group(1).strip()
    return ""


def replace_role_heading(text: str, role: str, source: str, target: str) -> str:
    old = heading(source, role)
    new = heading(target, role)
    if old == new:
        return text
    return re.sub(
        rf"^(##\s+){re.escape(old)}(\s*)$",
        rf"\g<1>{new}\g<2>",
        text,
        count=1,
        flags=re.IGNORECASE | re.MULTILINE,
    )


def has_role_heading(text: str, profile: str, role: str) -> bool:
    expected = heading(profile, role).casefold()
    return any(item.casefold() == expected for item in h2_headings(text))


def _append_missing_role(text: str, profile: str, role: str) -> str:
    placeholders = {
        "drivers": "- TODO: capture the decision drivers.",
        "alternatives": "- TODO: record the considered options.",
        "related": "- None.",
        "references": "- TODO: add verifiable references.",
    }
    content = placeholders.get(role, f"TODO: migrate the {role} content.")
    block = f"## {heading(profile, role)}\n\n{content}\n\n"
    enforcement = re.search(r"^##\s+Enforcement\s*$", text, re.MULTILINE)
    if enforcement:
        return text[: enforcement.start()] + block + text[enforcement.start() :]
    return text.rstrip() + "\n\n" + block


def set_frontmatter_profile(text: str, profile: str) -> str:
    normalized = normalize_profile(profile)
    raw = _leading_frontmatter(text)
    if not raw:
        raise AdrFormatError("canonical frontmatter is required before format conversion")
    if _FORMAT_LINE_RE.search(raw):
        return _FORMAT_LINE_RE.sub(f'format: "{normalized}"', text, count=1)
    closing = text.find("\n---", 3)
    if closing == -1:
        raise AdrFormatError("unterminated frontmatter")
    return text[:closing] + f'\nformat: "{normalized}"' + text[closing:]


def convert_profile(
    text: str,
    target: str,
    *,
    source: Optional[str] = None,
) -> Tuple[str, str]:
    target_profile = normalize_profile(target)
    source_profile = normalize_profile(source) if source else profile_for_text(text)
    declared = declared_profile(text)
    if (
        source is not None
        and declared in SUPPORTED_PROFILES
        and declared != source_profile
    ):
        raise AdrFormatError(
            f"--from-profile {source_profile!r} conflicts with declared "
            f"format {declared!r}"
        )
    missing_core = [
        role
        for role in ("context", "decision", "consequences")
        if not has_role_heading(text, source_profile, role)
    ]
    if missing_core:
        raise AdrFormatError(
            f"{source_profile} source is missing required semantic section(s): "
            + ", ".join(missing_core)
        )
    converted = text
    for role in ("context", "drivers", "alternatives", "decision", "consequences"):
        converted = replace_role_heading(converted, role, source_profile, target_profile)
    for role in PROFILE_REQUIRED_ROLES[target_profile]:
        if not has_role_heading(converted, target_profile, role):
            converted = _append_missing_role(converted, target_profile, role)
    converted = set_frontmatter_profile(converted, target_profile)
    return converted, source_profile
