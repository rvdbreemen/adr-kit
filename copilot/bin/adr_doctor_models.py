"""Versioned doctor output models and rendering."""

from __future__ import annotations

from pathlib import Path
from typing import Any

SCHEMA_VERSION = 1
FAILURE_STATUSES = {"failed", "stale"}
STATUS_ORDER = {
    "failed": 8,
    "stale": 7,
    "trust-pending": 6,
    "degraded": 5,
    "repaired": 4,
    "disabled": 3,
    "unsupported": 2,
    "healthy": 1,
}


def check(
    check_id: str,
    *,
    status: str,
    client: str = "common",
    summary: str,
    evidence: list[dict[str, Any]] | None = None,
    repairs: list[dict[str, Any]] | None = None,
    degradations: list[dict[str, Any]] | None = None,
    actions: list[dict[str, Any]] | None = None,
    required: bool = True,
    extension: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "id": check_id,
        "client": client,
        "status": status,
        "required": required,
        "summary": summary,
        "evidence": evidence or [],
        "repairs": repairs or [],
        "degradations": degradations or [],
        "actions": actions or [],
        "extension": extension,
    }


def benchmark_extension(
    *,
    method_id: str,
    state: str,
    sample_count: int,
    reference_fixture: str,
    budget: dict[str, float | int],
    measurements: dict[str, float | int | None] | None = None,
) -> dict[str, Any]:
    values = {"p50_ms": None, "p95_ms": None, "max_ms": None}
    values.update(measurements or {})
    return {
        "contract_version": 1,
        "kind": "latency-benchmark",
        "method_id": method_id,
        "state": state,
        "sample_count": sample_count,
        "reference_fixture": reference_fixture,
        "measurements": values,
        "budget": budget,
    }


def build_report(
    *,
    root: Path,
    mode: str,
    adr: dict[str, Any],
    checks: list[dict[str, Any]],
    repairs: list[dict[str, Any]],
) -> dict[str, Any]:
    client_status = {}
    for client in ("claude", "codex", "copilot"):
        relevant = [item["status"] for item in checks if item["client"] == client]
        client_status[client] = (
            max(relevant, key=lambda value: STATUS_ORDER.get(value, 0))
            if relevant
            else "unsupported"
        )
    required_failures = [
        item for item in checks
        if item["required"] and item["status"] in FAILURE_STATUSES
    ]
    exit_code = 1 if adr.get("exit_code") or required_failures else 0
    statuses = [item["status"] for item in checks]
    if exit_code:
        overall = "failed"
    elif "degraded" in statuses or "trust-pending" in statuses:
        overall = "degraded"
    elif repairs or "repaired" in statuses:
        overall = "repaired"
    else:
        overall = "healthy"
    return {
        "schema_version": SCHEMA_VERSION,
        "mode": mode,
        "root": str(root),
        "overall_status": overall,
        "clients": client_status,
        "summary": {
            "index_ok": adr.get("summary", {}).get("index_ok", False),
            "lint_ok": adr.get("summary", {}).get("lint_ok", False),
            "findings": adr.get("summary", {}).get("findings", 0),
            "checks": len(checks),
            "repairs": len(repairs),
            "required_failures": len(required_failures),
            "adr_findings": adr.get("summary", {}).get("findings", 0),
        },
        "checks": checks,
        "repairs": repairs,
        "adr": adr,
        # Stable legacy fields retained for existing CI consumers.
        "adr_dir": adr.get("adr_dir"),
        "repo_root": adr.get("repo_root"),
        "index": adr.get("index", {}),
        "lint": adr.get("lint", {}),
        "findings": adr.get("findings", []),
        "audit": adr.get("audit", {}),
        "exit_code": exit_code,
    }


def render_human(report: dict[str, Any]) -> str:
    lines = [
        f"adr-doctor: {report['overall_status']} ({report['mode']})",
        "clients: " + ", ".join(
            f"{name}={status}" for name, status in report["clients"].items()
        ),
        (
            f"checks={report['summary']['checks']} "
            f"repairs={report['summary']['repairs']} "
            f"adr_findings={report['summary']['adr_findings']}"
        ),
    ]
    for item in report["checks"]:
        lines.append(
            f"  {item['status']}: {item['client']}/{item['id']} "
            f"{item['summary']}"
        )
        for action in item["actions"]:
            lines.append(f"    action: {action.get('command') or action.get('detail')}")
    for repair in report["repairs"]:
        lines.append(f"  repaired: {repair['path']} ({repair['kind']})")
    return "\n".join(lines)
