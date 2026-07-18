#!/usr/bin/env python3
"""Refresh the frozen OTGW-firmware ADR compatibility corpus.

Only numbered ADR Markdown files and the source repository license are copied.
The adjacent checkout is never needed by the tests themselves.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
from collections import Counter
from datetime import date
from pathlib import Path
from typing import Dict, List


ROOT = Path(__file__).resolve().parent.parent
TARGET = ROOT / "tests" / "testsets" / "otgw-firmware"
ADR_NAME_RE = re.compile(r"^ADR-\d{3,4}-.*\.md$", re.IGNORECASE)


def _git(source: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(source), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "git command failed")
    return result.stdout.strip()


def _json_command(*args: str) -> tuple[int, Dict]:
    result = subprocess.run(
        [sys.executable, *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
        cwd=str(ROOT),
    )
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            f"command produced invalid JSON: {' '.join(args)}\n{result.stderr}"
        ) from exc
    return result.returncode, payload


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _numbered_adr_changes(source: Path) -> List[str]:
    status = _git(source, "status", "--porcelain", "--", "docs/adr")
    changes: List[str] = []
    for line in status.splitlines():
        normalized = line.replace("\\", "/")
        name = normalized.rsplit("/", 1)[-1].strip('"')
        if ADR_NAME_RE.match(name):
            changes.append(line)
    return changes


def refresh(source: Path) -> Dict:
    source = source.resolve()
    source_adrs = source / "docs" / "adr"
    source_license = source / "LICENSE"
    if not source_adrs.is_dir() or not source_license.is_file():
        raise RuntimeError(
            f"{source} is not an OTGW-firmware checkout with docs/adr and LICENSE"
        )

    dirty_adrs = _numbered_adr_changes(source)
    if dirty_adrs:
        raise RuntimeError(
            "refusing to snapshot modified/untracked numbered ADRs:\n"
            + "\n".join(dirty_adrs)
        )

    source_files = sorted(
        (
            path
            for path in source_adrs.iterdir()
            if path.is_file() and ADR_NAME_RE.match(path.name)
        ),
        key=lambda path: path.name.casefold(),
    )
    if not source_files:
        raise RuntimeError(f"no numbered ADR files found in {source_adrs}")

    target_adrs = TARGET / "adrs"
    target_adrs.mkdir(parents=True, exist_ok=True)
    expected_names = {path.name for path in source_files}
    for stale in target_adrs.iterdir():
        if stale.is_file() and ADR_NAME_RE.match(stale.name):
            if stale.name not in expected_names:
                stale.unlink()
    for source_file in source_files:
        shutil.copyfile(source_file, target_adrs / source_file.name)
    shutil.copyfile(source_license, TARGET / "LICENSE")

    plan_code, plan = _json_command(
        str(ROOT / "bin" / "adr-migrate"),
        "--plan",
        "--format",
        "json",
        str(target_adrs),
    )
    if plan_code != 0:
        raise RuntimeError("migration planner failed for the copied corpus")
    dry_run_code, dry_run = _json_command(
        str(ROOT / "bin" / "adr-migrate"),
        "--dry-run",
        "--format",
        "json",
        str(target_adrs),
    )

    file_entries = [
        {
            "path": f"adrs/{path.name}",
            "bytes": path.stat().st_size,
            "sha256": _sha256(path),
        }
        for path in sorted(target_adrs.iterdir(), key=lambda item: item.name.casefold())
        if path.is_file() and ADR_NAME_RE.match(path.name)
    ]
    format_counts = Counter(
        item["detected_format"] for item in plan.get("files", [])
    )
    action_counts = Counter(item["action"] for item in plan.get("files", []))

    manifest = {
        "schema_version": 1,
        "corpus": "otgw-firmware-adrs",
        "captured_on": date.today().isoformat(),
        "license": "GPL-3.0-only",
        "source": {
            "repository_url": _git(source, "remote", "get-url", "origin"),
            "revision": _git(source, "rev-parse", "HEAD"),
            "adr_tree_revision": _git(
                source,
                "log",
                "-1",
                "--format=%H",
                "--",
                "docs/adr",
            ),
            "path": "docs/adr",
            "numbered_adrs_clean": True,
        },
        "baseline": {
            "file_count": len(file_entries),
            "total_bytes": sum(item["bytes"] for item in file_entries),
            "migration_plan": {
                "format_counts": dict(sorted(format_counts.items())),
                "action_counts": dict(sorted(action_counts.items())),
                "deterministic": plan["summary"]["deterministic"],
                "guided": plan["summary"]["guided"],
                "notices": plan["summary"]["notices"],
            },
            "metadata_dry_run": {
                "exit_code": dry_run_code,
                "changed": dry_run["summary"]["changed"],
                "failed": dry_run["summary"]["failed"],
            },
        },
        "files": file_entries,
    }
    (TARGET / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Refresh the frozen OTGW-firmware ADR test corpus."
    )
    parser.add_argument(
        "--source",
        default=str(ROOT.parent / "OTGW-firmware"),
        help="Path to the OTGW-firmware checkout (default: ../OTGW-firmware).",
    )
    args = parser.parse_args()
    try:
        manifest = refresh(Path(args.source))
    except RuntimeError as exc:
        print(f"refresh-otgw-corpus: {exc}", file=sys.stderr)
        return 2
    baseline = manifest["baseline"]
    print(
        "refreshed OTGW ADR corpus: "
        f"{baseline['file_count']} files, "
        f"{baseline['total_bytes']} bytes, "
        f"revision {manifest['source']['revision']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
