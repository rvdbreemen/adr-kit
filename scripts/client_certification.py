"""Validate certification evidence and render evidence-backed support claims."""

from __future__ import annotations

import datetime as dt
import re

CLIENTS = ("claude-code-cli", "codex-cli", "github-copilot-cli")
OUTCOMES = {
    "workflow-discovery", "task-context", "edit-governance", "mcp",
    "pre-commit", "lifecycle", "doctor",
}
FIXTURES = {"generator", "schema", "hook", "installer", "doctor", "package", "adr-lint", "adr-index", "regression"}
SMOKE = {
    "install", "list", "workflow-discovery", "workflow-invocation", "instructions",
    "hook-outcomes", "mcp-initialize", "mcp-list", "mcp-call", "second-install-noop",
    "verified-update", "rollback", "doctor", "uninstall-preserves-user-state",
}
PRESERVATION = {
    "unrelated-config", "instruction-bytes-outside-markers", "local-guide",
    "previous-healthy-payload", "source-checkout",
}
NATIVE_OPTIMIZATION = {
    "native-manifest-layout", "native-discovery-syntax", "client-skill-metadata",
    "concise-prompt-behavior", "native-hook-shape", "no-deprecated-prompt-claim",
}

def _all_true(value: object, required: set[str], label: str, errors: list[str]) -> None:
    if not isinstance(value, dict):
        errors.append(f"{label}: expected object")
        return
    missing = sorted(required - {key for key, passed in value.items() if passed is True})
    if missing:
        errors.append(f"{label}: missing passing evidence: {', '.join(missing)}")


def validate(bundle: object, candidate: str, release_candidate: bool, max_age_days: int) -> list[str]:
    errors: list[str] = []
    if not isinstance(bundle, dict) or bundle.get("schema_version") != 1:
        return ["bundle schema_version must be 1"]
    if bundle.get("candidate_commit") != candidate:
        errors.append("bundle candidate commit mismatch")
    if release_candidate and not re.fullmatch(r"[0-9a-fA-F]{7,64}", candidate):
        errors.append("release-candidate evidence must bind to a real commit hash")
    try:
        age = (dt.date.today() - dt.date.fromisoformat(bundle["contract_date"])).days
        if age < 0 or age > max_age_days:
            errors.append("bundle contract date is stale")
    except (KeyError, TypeError, ValueError):
        errors.append("bundle contract date is invalid")
    records = bundle.get("records")
    if not isinstance(records, list) or [record.get("client") for record in records] != list(CLIENTS):
        return errors + ["records must contain exactly the three clients in canonical order"]
    for record in records:
        client = record["client"]
        prefix = f"{client}"
        if record.get("candidate_commit") != candidate:
            errors.append(f"{prefix}: candidate commit mismatch")
        if record.get("contract_date") != bundle.get("contract_date"):
            errors.append(f"{prefix}: contract date mismatch")
        for key in ("client_version", "adr_kit_version"):
            if not record.get(key):
                errors.append(f"{prefix}: {key} missing")
        if record.get("surface") != "cli" or record.get("os") != "windows":
            errors.append(f"{prefix}: only the Windows CLI identity is certifiable")
        if release_candidate and record.get("evidence_mode") != "native":
            errors.append(f"{prefix}: native release-candidate evidence missing")
        if release_candidate and (
            record.get("working_tree_clean") is not True
            or not re.fullmatch(
                r"[0-9a-f]{64}",
                str(record.get("artifact_sha256", "")),
            )
        ):
            errors.append(
                f"{prefix}: clean commit-bound artifact hash missing"
            )
        if not record.get("environment_fingerprint") or not record.get("evidence_links"):
            errors.append(f"{prefix}: retained redacted environment/log evidence missing")
        _all_true(record.get("required_outcomes"), OUTCOMES, f"{prefix} outcomes", errors)
        _all_true(record.get("fixtures"), FIXTURES, f"{prefix} fixtures", errors)
        _all_true(record.get("native_smoke"), SMOKE, f"{prefix} native smoke", errors)
        _all_true(record.get("lifecycle_preservation"), PRESERVATION, f"{prefix} preservation", errors)
        _all_true(record.get("native_optimization"), NATIVE_OPTIMIZATION, f"{prefix} native optimization", errors)
        if record.get("native_optimization", {}).get("deprecated-prompt-first-class") is True:
            errors.append(f"{prefix}: deprecated prompt surface advertised")
        platforms = record.get("platforms", {})
        if platforms.get("windows", {}).get("status") != "pass":
            errors.append(f"{prefix}: Windows evidence is not passing")
        for platform in ("macos", "linux"):
            status = platforms.get(platform, {}).get("status")
            reason = platforms.get(platform, {}).get("reason")
            if status not in {"pass", "fail", "not-run"} or (status == "not-run" and not reason):
                errors.append(f"{prefix}: {platform} needs a result or not-run reason")
        benchmarks = record.get("benchmarks", [])
        states = {item.get("state"): item for item in benchmarks if isinstance(item, dict)}
        for state, limits in {"cold": (1000, 2000, 5000), "warm": (150, 500, 1000)}.items():
            item = states.get(state)
            if not item:
                errors.append(f"{prefix}: {state} benchmark missing")
                continue
            if item.get("samples", 0) < 5 or item.get("timed_out") is not False:
                errors.append(f"{prefix}: {state} benchmark method/timeout failed")
            if not item.get("method_id") or item.get("hard_timeout_ms") != limits[2]:
                errors.append(f"{prefix}: {state} benchmark method/timeout failed")
            if item.get("p50_ms", 1e99) > limits[0] or item.get("p95_ms", 1e99) > limits[1] or item.get("max_ms", 1e99) > limits[2]:
                errors.append(f"{prefix}: {state} latency budget failed")
            if item.get("p95_ms", 1e99) > item.get("baseline_p95_ms", 0) * 1.2:
                errors.append(f"{prefix}: {state} p95 regressed more than 20%")
            if state == "warm" and item.get("writes") != 0:
                errors.append(f"{prefix}: unchanged generation rewrote output")
        inventory = record.get("inventory", {})
        if inventory.get("bin_baseline") != 27 or inventory.get("scripts_baseline") != 3:
            errors.append(f"{prefix}: executable baseline missing")
        if inventory.get("task_40_added", 99) > 4 and not inventory.get("exception"):
            errors.append(f"{prefix}: executable budget exceeded")
        dependencies = record.get("dependencies", {})
        if dependencies.get("runtime") != [] or dependencies.get("development_in_runtime") is not False:
            errors.append(f"{prefix}: runtime dependency policy failed")
        for pin in dependencies.get("exact_pins", []):
            required = {
                "adr",
                "compatibility_reason",
                "review_after",
                "update_mechanism",
                "removal_test",
            }
            if not isinstance(pin, dict) or not required.issubset(pin):
                errors.append(f"{prefix}: exact dependency pin lacks evidence")
        if not record.get("source_links"):
            errors.append(f"{prefix}: source links missing")
        policy = record.get("release_policy", {})
        if not policy.get("archive_allowlist_clean") or not policy.get("consolidated_candidate"):
            errors.append(f"{prefix}: release archive/candidate policy failed")
        if policy.get("stable_releases_today", 99) >= 1 and not all(
            policy.get(key) for key in ("emergency_reason", "affected_versions", "rollback_proof", "changelog", "followup_review")
        ):
            errors.append(f"{prefix}: same-day stable release limit exceeded")
        if policy.get("default_or_hook_reversal") and not policy.get("superseding_proposed_adr"):
            errors.append(f"{prefix}: policy reversal lacks Proposed ADR")
    return errors


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
        "",
        "### Known degradation: no fail-closed edit floor on GitHub Copilot CLI",
        "",
        "ADR-004 names the pre-edit tier the *fail-closed* floor of the injection",
        "model: the one place that refuses rather than degrades, because an edit is",
        "the last moment before a decision is violated in code. Copilot CLI exposes",
        "no pre-tool-use event that can carry model context, so on that client the",
        "floor does not exist. What runs instead is a backstop, and a backstop is a",
        "weaker guarantee by construction: `postToolUse` reports drift after the",
        "edit has already been written, and the generated workflow prompts ask for",
        "an ADR lookup before editing, which is instruction rather than enforcement.",
        "",
        "This is stated here rather than left to be inferred from a null in",
        "`hooks/manifest.json`. The enforcement that does not weaken is the",
        "pre-commit hook, which is client-independent: a violation is caught before",
        "the commit lands on every client, including this one.",
        "",
        "IDE, cloud, preview, wrappers, legacy surfaces, and TASK-43 clients are not promoted by this matrix.",
        "",
    ])
    return "\n".join(lines)
