"""Render the evidence-backed support document from the canonical registries.

Split out of `client_certification.py`, which had grown past the 400-line
support-module budget ADR-010 sets and `tests/test_release_allowlist.py`
enforces. The split follows the seam the module docstring already described:
that file *validates* certification evidence, this one *renders* the claims.

Every section here derives its content from a registry rather than asserting
it. That is not a style preference -- it is the correction TASK-115 and
TASK-138 both landed, and the reason each renderer states its own source.
"""

from __future__ import annotations

CLIENTS = ("claude-code-cli", "codex-cli", "github-copilot-cli")


#: Which manifest event answers each column of the lifecycle table.
LIFECYCLE_COLUMNS = (
    ("Session global", "session-start"),
    ("Prompt/task query", "user-prompt-submit"),
    ("Edit query", "pre-tool-use"),
    ("Post-edit backstop", "post-tool-use"),
    ("Plan exit", "plan-exit"),
    ("Shell tool / PR moment", "pr-create"),
    ("Subagent", "subagent-start"),
    ("Compaction", "pre-compact"),
)


def _lifecycle_rows(labels: dict) -> list:
    """Derive the lifecycle table from the manifest instead of asserting it.

    These rows were three hardcoded strings, which is exactly why the document
    could claim capabilities that did not exist: nothing derived them, so
    nothing could contradict them. `Plan exit | supported (ExitPlanMode)` stayed
    true-looking for as long as somebody had typed it, through a release in
    which that event never fired at all.

    Now each cell is the manifest's own answer for that client -- the native
    event name when the client offers the moment, and an explicit "no native
    event" when it does not. A capability cannot appear here unless it is
    registered, and `--check` fails the build when the file drifts from the
    manifest.

    Falls back to a stated absence rather than raising: this renderer runs
    inside release certification, and a missing manifest should fail the
    manifest's own gate, not the document that reads it.
    """
    import json
    from pathlib import Path as _Path

    manifest_path = _Path(__file__).resolve().parents[1] / "hooks" / "manifest.json"
    try:
        events = {
            event["id"]: event
            for event in json.loads(manifest_path.read_text(encoding="utf-8"))["events"]
        }
    except (OSError, ValueError, KeyError, TypeError):
        return [
            "",
            "## Lifecycle retrieval support",
            "",
            "_Unavailable: hooks/manifest.json could not be read, so no claim is"
            " made here rather than an unverified one._",
        ]

    header = " | ".join(name for name, _ in LIFECYCLE_COLUMNS)
    rows = [
        "",
        "## Lifecycle retrieval support",
        "",
        "Derived from `hooks/manifest.json`, which is the registry of what each",
        "client is *wired for*. A cell names that client's own event, or states",
        "that the client offers none.",
        "",
        "This table makes one claim and not two. It says a moment is registered;",
        "it does not say the wiring behind it works. That second question belongs",
        "to the dispatch tests, which drive every registered event through the",
        "real entrypoint on every client -- and it is a question worth keeping",
        "separate, because `Plan exit | supported (ExitPlanMode)` sat in this file",
        "through a release in which that event never fired. The Evidence column",
        "above says how the wiring was verified.",
        "",
        f"| Client | {header} |",
        "|---|" + "---|" * len(LIFECYCLE_COLUMNS),
    ]
    for client in CLIENTS:
        cells = []
        for _name, event_id in LIFECYCLE_COLUMNS:
            event = events.get(event_id)
            native = (event or {}).get("clients", {}).get(client)
            if not native:
                cells.append("no native event")
                continue
            matcher = (event or {}).get("matcher")
            # A matcher is a regex alternation, so its pipes have to be escaped
            # or they end the table cell and silently shift every column right.
            escaped = str(matcher).replace("|", r"\|") if matcher else ""
            cells.append(f"`{native}`" + (f" / `{escaped}`" if matcher else ""))
        rows.append(f"| {labels[client]} | " + " | ".join(cells) + " |")
    return rows

def _enforcement_rows(labels: dict) -> list:
    """State which tiers block, from the two files that decide it.

    This section replaces a hardcoded paragraph that attributed to ADR-004 the
    option ADR-004 rejected: it called the pre-edit tier "the *fail-closed*
    floor of the injection model". ADR-004 says the opposite twice -- injection
    hooks "never block; they steer", and a fail-closed edit gate is listed under
    the rejected alternatives ("Blocking belongs at commit, not keystroke").
    The paragraph then contradicted itself four sentences later by naming the
    pre-commit hook as the enforcement that does not weaken.

    It was hardcoded, which is the same reason `_lifecycle_rows` gives for the
    claims it had to remove: nothing derived it, so nothing could contradict it.
    The per-client half is now the manifest's own answer plus whatever
    `clients/capabilities.json` declares, so a tier cannot be claimed here
    unless it is registered, and cannot be claimed as enforcing on a client that
    declares it advisory.

    Falls back to a stated absence rather than raising, for the same reason
    `_lifecycle_rows` does.
    """
    manifest, capabilities = _read_contract_sources()
    if manifest is None or capabilities is None:
        return [
            "",
            "## Where enforcement is fail-closed",
            "",
            "_Unavailable: `hooks/manifest.json` or `clients/capabilities.json`"
            " could not be read, so no claim is made here rather than an"
            " unverified one._",
        ]

    pr_clients = manifest.get("pr-create", {}).get("clients", {})
    rows = [
        "",
        "## Where enforcement is fail-closed",
        "",
        "Derived from `hooks/manifest.json` and `clients/capabilities.json`.",
        "",
        "ADR-004 puts all three injection tiers -- session, edit and task -- on",
        "the fail-open side without exception: they steer, and none of them",
        "blocks. It rejected a fail-closed edit gate by name, because legitimate",
        "compliant edits touch governed paths constantly, so blocking belongs at",
        "commit rather than at keystroke. There is no pre-edit floor on any",
        "client, and the absence of one is not a degradation.",
        "",
        "Two tiers block, and neither is an injection tier:",
        "",
        "* **Commit tier** (ADR-004) -- `bin/adr-judge` at pre-commit and in CI.",
        "  Client-independent, because `git commit` happens whether or not an",
        "  agent is running. A violation is caught before the commit lands on",
        "  every client in this table, and on no client at all.",
        "* **Pull-request tier** (ADR-023) -- `hooks/adr_pr_guard.py` on",
        "  `gh pr create`. Client-qualified: a client that has no permission",
        "  decision to return cannot stop the tool call, and where it cannot the",
        "  branch is still judged and the verdict shown, labelled as advisory.",
        "",
        "| Client | Pull-request tier |",
        "|---|---|",
    ]
    for client in CLIENTS:
        advisory = next(
            (
                entry
                for entry in _degradations(capabilities, client)
                if entry.get("outcome") == "enforcement"
            ),
            None,
        )
        if not pr_clients.get(client):
            cell = "no native event: the commit tier is the only floor here"
        elif advisory:
            cell = f"advisory only (`{advisory.get('id', 'declared degradation')}`)"
        else:
            cell = f"enforced at `{pr_clients[client]}`"
        rows.append(f"| {labels[client]} | {cell} |")
    return rows


def _degradation_rows(labels: dict) -> list:
    """Render every declared degradation, and claim no others.

    The heading this replaces named one degradation for one client in prose.
    Prose cannot be checked against the registry, so the section could describe
    a weakening that was never declared -- which is what it did.
    """
    _manifest, capabilities = _read_contract_sources()
    if capabilities is None:
        return []
    rows = [
        "",
        "## Known degradations",
        "",
        "Every entry is declared in `clients/capabilities.json`, with its reason,",
        "its user-visible effect and the backstop that still holds (ADR-010,",
        "ADR-023). A weakening that is not declared there does not appear here.",
        "",
        "| Client | Outcome | Reason | User effect | Backstop |",
        "|---|---|---|---|---|",
    ]
    found = False
    for client in CLIENTS:
        for entry in _degradations(capabilities, client):
            found = True
            cells = [
                labels[client],
                f"`{entry.get('outcome', '?')}`",
                str(entry.get("reason", "")).replace("|", r"\|"),
                str(entry.get("user_effect", "")).replace("|", r"\|"),
                str(entry.get("backstop", "")).replace("|", r"\|"),
            ]
            rows.append("| " + " | ".join(cells) + " |")
    return rows if found else []


def _degradations(capabilities: dict, client: str) -> list:
    for entry in capabilities.get("clients", []):
        if isinstance(entry, dict) and entry.get("id") == client:
            declared = entry.get("degradations")
            return [item for item in declared if isinstance(item, dict)] if isinstance(declared, list) else []
    return []


def _read_contract_sources() -> tuple:
    """The manifest events by id and the capability registry, or (None, None)."""
    import json
    from pathlib import Path as _Path

    root = _Path(__file__).resolve().parents[1]
    try:
        events = {
            event["id"]: event
            for event in json.loads(
                (root / "hooks" / "manifest.json").read_text(encoding="utf-8")
            )["events"]
        }
    except (OSError, ValueError, KeyError, TypeError):
        events = None
    try:
        capabilities = json.loads(
            (root / "clients" / "capabilities.json").read_text(encoding="utf-8")
        )
    except (OSError, ValueError):
        capabilities = None
    return events, capabilities


def _probe_rows(labels: dict) -> list:
    """Report what a real client answered, separately from what we believe.

    The table above is derived from our own manifest, so it says what adr-kit is
    wired for. This section says what an installed binary actually emitted, and
    the two are deliberately not merged: every hook defect this kit has shipped
    was an event we had registered and the client never reached, and a document
    that folds the two together cannot show that gap.

    Absent evidence is `not-run`, never `unsupported`. A probe that did not run,
    or a prompt that used no tools, proves nothing about a capability -- and
    writing the stronger word is exactly how this document acquired the claims
    it had to be rewritten to remove.
    """
    import json
    from pathlib import Path as _Path

    root = _Path(__file__).resolve().parents[1]
    probes = sorted((root / "tests" / "certification").glob("probe-*.json"))
    if not probes:
        return []
    records = []
    for path in probes:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        for record in payload.get("records", []):
            if isinstance(record, dict) and record.get("client") in labels:
                records.append((path.name, record))
    if not records:
        return []

    rows = [
        "",
        "## Observed client evidence",
        "",
        "What an installed binary reported, from its own event stream. Separate",
        "from the table above on purpose: that one says what adr-kit is wired",
        "for, this one says what a client did. Every hook defect this kit has",
        "shipped lived in the gap between the two.",
        "",
        "An event that does not appear here is `not-observed`, not unsupported.",
        "A probe run that used no tools cannot produce a tool event, and reading",
        "that silence as a missing capability is how this document acquired the",
        "claims it had to be rewritten to remove.",
        "",
        "| Client | Version | Platform | Evidence | Observed events |",
        "|---|---|---|---|---|",
    ]
    for source, record in records:
        observed = record.get("observed_events") or []
        detail = (
            ", ".join(f"`{event}`" for event in observed)
            if observed
            else f"_{record.get('reason', 'not run')}_"
        )
        rows.append(
            f"| {labels[record['client']]} | {record.get('version') or 'unknown'} | "
            f"{record.get('platform') or 'unknown'} | {record.get('evidence_mode')} | "
            f"{detail} |"
        )
    rows.extend([
        "",
        "Source: " + ", ".join(f"`tests/certification/{name}`"
                               for name in sorted({name for name, _ in records})) + ".",
        "Regenerate with `python scripts/probe-client-events.py`, which exits 0"
        " when a client is absent because an unmeasured client is a normal"
        " outcome rather than a failure.",
    ])
    return rows

def support_matrix(bundle: dict) -> str:
    labels = {
        "claude-code-cli": "Claude Code CLI",
        "codex-cli": "Codex CLI",
        "github-copilot-cli": "GitHub Copilot CLI",
    }
    records = {item["client"]: item for item in bundle["records"]}
    if set(records) != set(CLIENTS) or len(bundle["records"]) != len(CLIENTS):
        raise ValueError("support matrix requires exactly the three clients")
    lines = [
        "<!-- Generated from certification evidence; do not edit. -->",
        "# ADR Kit client support",
        "",
        "| Client | Surface | Windows | macOS | Linux | Evidence |",
        "|---|---|---|---|---|---|",
    ]
    for client in CLIENTS:
        record = records[client]
        status = "certified" if record["evidence_mode"] == "native" else "simulated only"
        platforms = record["platforms"]
        lines.append(
            f"| {labels[client]} | CLI | {platforms['windows']['status']} | "
            f"{platforms['macos']['status']} | {platforms['linux']['status']} | {status} |"
        )
    lines.extend(_lifecycle_rows(labels))
    lines.extend(_probe_rows(labels))
    lines.extend([
        "",
        "All retrieval is local, bounded, and index-first. Unsupported native lifecycle events are not advertised; deterministic pre-commit enforcement remains the backstop.",
    ])
    lines.extend(_enforcement_rows(labels))
    lines.extend(_degradation_rows(labels))
    lines.extend([
        "",
        "IDE, cloud, preview, wrappers, legacy surfaces, and TASK-43 clients are not promoted by this matrix.",
        "",
    ])
    return "\n".join(lines)
