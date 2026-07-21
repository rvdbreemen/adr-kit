"""Safe GitHub reporting for a deterministic ADR readiness report."""

from __future__ import annotations

import json
import re
from pathlib import Path


def github_escape(value: object) -> str:
    return (
        str(value)
        .replace("%", "%25")
        .replace("\r", "%0D")
        .replace("\n", "%0A")
    )


def markdown_escape(value: object) -> str:
    return (
        re.sub(r"[\x00-\x1f\x7f]+", " ", str(value))
        .replace("`", "'")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def _source_command(path: str) -> str:
    clean = re.sub(r"[\x00-\x1f\x7f]+", " ", path).replace('"', '\\"')
    return f'/adr-kit:grill --source "{clean}"'


def render_summary(report: dict) -> str:
    lines = [
        "## ADR readiness",
        "",
        f"Evaluated: `{markdown_escape(report.get('evaluated_on', 'unknown'))}`",
        "",
    ]
    for item in report.get("adrs", []):
        link = item.get("implementation_link", {})
        if not link.get("linked") and item.get("status") != "Proposed":
            continue
        label = "BLOCK" if link.get("blocking_proposed") else "INFO"
        command = item.get("next_command") or f"/adr-kit:grill {item.get('adr_id')}"
        evidence = ", ".join(
            str(entry.get("code", "")) for entry in link.get("evidence", [])
        ) or "none"
        lines.extend(
            [
                f"- [{label}] **{markdown_escape(item.get('adr_id'))}** - "
                f"`{markdown_escape(item.get('classification'))}` - "
                f"{markdown_escape(item.get('title'))}",
                f"  - Evidence: `{markdown_escape(evidence)}`",
                f"  - Next: `{markdown_escape(command)}`",
            ]
        )
    for advisory in report.get("advisories", []):
        command = advisory.get("next_command") or _source_command(
            str(advisory.get("path", ""))
        )
        lines.extend(
            [
                f"- [ADVISORY] `{markdown_escape(advisory.get('code'))}` - "
                f"`{markdown_escape(advisory.get('classification', 'not-an-adr'))}` - "
                f"`{markdown_escape(advisory.get('path'))}`",
                f"  - Evidence: `{markdown_escape(advisory.get('message'))}`",
                f"  - Next: `{markdown_escape(command)}`",
            ]
        )
    if len(lines) == 4:
        lines.append("- No ADR readiness findings.")
    return "\n".join(lines) + "\n"


def output_values(report: dict) -> dict[str, str]:
    blocking = list(report.get("summary", {}).get("blocking_proposed", []))
    return {
        "blocking-count": str(len(blocking)),
        "blocking-adrs": json.dumps(blocking, separators=(",", ":")),
        "advisory-count": str(report.get("summary", {}).get("advisory_count", 0)),
        "schema-version": str(report.get("schema_version", "")),
        "conclusion": "blocked" if blocking else "advisory-or-clean",
    }


def write_outputs(path: Path, values: dict[str, str]) -> None:
    with path.open("a", encoding="utf-8", newline="\n") as stream:
        for key in sorted(values):
            value = values[key].replace("\r", "").replace("\n", "")
            stream.write(f"{key}={value}\n")


def annotations(report: dict) -> list[str]:
    lines = []
    for item in report.get("adrs", []):
        link = item.get("implementation_link", {})
        if not link.get("blocking_proposed"):
            continue
        evidence = ",".join(
            str(entry.get("code", "")) for entry in link.get("evidence", [])
        )
        message = (
            f"{item.get('adr_id')} is {item.get('classification')}; "
            f"evidence={evidence}; next={item.get('next_command')}"
        )
        lines.append(
            f"::error title=ADR readiness block::{github_escape(message)}"
        )
    for advisory in report.get("advisories", []):
        command = advisory.get("next_command") or _source_command(
            str(advisory.get("path", ""))
        )
        message = (
            f"{advisory.get('code')} "
            f"classification={advisory.get('classification', 'not-an-adr')} "
            f"path={advisory.get('path')}; "
            f"evidence={advisory.get('message')}; next={command}"
        )
        lines.append(
            f"::notice title=ADR review advisory::{github_escape(message)}"
        )
    return lines
