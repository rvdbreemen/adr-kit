"""Validate certification evidence.

Rendering the support document lives in `client_support_matrix.py`, which this
module re-exports `support_matrix` from so no caller had to change when the two
were split apart (ADR-010's support-module line budget).
"""

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



# Rendering lives in its own module (ADR-010 line budget). Re-exported so
# `from client_certification import support_matrix, validate` keeps working:
# the seam is internal, and callers should not have to learn about it.
from client_support_matrix import support_matrix  # noqa: E402,F401
