#!/usr/bin/env python3
"""Certify deterministic ADR Grilling paths against their latency budgets."""

from __future__ import annotations

import argparse
import json
import platform
import statistics
import subprocess
import sys
import tempfile
import time
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BIN = ROOT / "bin"
sys.path.insert(0, str(BIN))

from adr_readiness import build_readiness_report  # noqa: E402
from adr_schema import render_frontmatter  # noqa: E402


def _fixture(root: Path, count: int = 50) -> Path:
    adr_dir = root / "docs" / "adr"
    adr_dir.mkdir(parents=True)
    (root / "src").mkdir()
    for number in range(1, count + 1):
        path = f"src/component-{number:03d}.py"
        (root / path).write_text("VALUE = 1\n", encoding="utf-8")
        metadata = {
            "id": f"ADR-{number:03d}",
            "title": f"Decision {number}",
            "status": "Proposed",
            "date": "2026-07-20",
            "binding": False,
            "gate": None,
            "documents_shipped": number % 3 == 0,
            "verified_in": [path],
            "supersedes": [],
            "superseded_by": None,
            "format": "madr",
        }
        body = (
            f"# ADR-{number:03d} Decision {number}\n\n"
            "## Status\n\nProposed, 2026-07-20.\n\n"
            "## Context and Problem Statement\n\nA stable choice is required.\n\n"
            "## Decision Drivers\n\n* Determinism.\n\n"
            "## Considered Options\n\n* Local.\n* Hosted.\n\n"
            "## Decision Outcome\n\nChosen option: **Local**, because it is bounded.\n\n"
            "## Consequences\n\nThe local implementation must be maintained.\n\n"
            "## Open Questions\n\nNone.\n\n"
            "## Related Decisions\n\n* None.\n\n"
            f"## References\n\n* {path}:1\n"
        )
        (adr_dir / f"ADR-{number:03d}-decision-{number}.md").write_text(
            render_frontmatter(metadata) + body, encoding="utf-8"
        )
    return adr_dir


def _measure(operation, samples: int) -> dict[str, float | int]:
    operation()
    values = []
    for _ in range(samples):
        started = time.perf_counter_ns()
        operation()
        values.append((time.perf_counter_ns() - started) / 1_000_000)
    ordered = sorted(values)
    p95_index = max(0, min(len(ordered) - 1, int(len(ordered) * 0.95) - 1))
    return {
        "samples": samples,
        "median_ms": round(statistics.median(ordered), 3),
        "p50_ms": round(statistics.median(ordered), 3),
        "p95_ms": round(ordered[p95_index], 3),
        "max_ms": round(max(ordered), 3),
    }


def _run(command: list[str], cwd: Path, *, input_text: str | None = None) -> bytes:
    result = subprocess.run(
        command,
        cwd=cwd,
        input=input_text,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=10,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr or result.stdout)
    return result.stdout.encode("utf-8")


def benchmark(samples: int) -> dict:
    with tempfile.TemporaryDirectory(prefix="adr-grilling-benchmark-") as raw:
        root = Path(raw)
        adr_dir = _fixture(root)
        changed = [f"src/change-{index:03d}.py" for index in range(500)]
        source = "\n".join(f"implements ADR-{number:03d}" for number in range(1, 51))
        for index, path in enumerate(changed):
            (root / path).write_text(f"VALUE = {index}\n", encoding="utf-8")
        _run(["git", "init"], root)
        _run(["git", "config", "user.email", "benchmark@example.com"], root)
        _run(["git", "config", "user.name", "ADR Kit Benchmark"], root)
        _run(["git", "add", "."], root)
        _run(["git", "commit", "-m", "benchmark base"], root)
        base = _run(["git", "rev-parse", "HEAD"], root).decode().strip()
        for index, path in enumerate(changed):
            adr_number = (index % 50) + 1
            (root / path).write_text(
                f"VALUE = {index + 1}  # implements ADR-{adr_number:03d}\n",
                encoding="utf-8",
            )
        _run(["git", "add", "src"], root)
        _run(["git", "commit", "-m", "benchmark head"], root)
        head = _run(["git", "rev-parse", "HEAD"], root).decode().strip()

        core = lambda: build_readiness_report(  # noqa: E731
            adr_dir, evaluated_on=date(2026, 7, 20), all_proposed=True
        )
        linkage = lambda: build_readiness_report(  # noqa: E731
            adr_dir,
            evaluated_on=date(2026, 7, 20),
            all_proposed=True,
            changed_paths=changed,
            source_text=source,
        )
        single_cli = lambda: _run(  # noqa: E731
            [
                sys.executable,
                str(BIN / "adr-readiness"),
                "ADR-001",
                "--repo-root",
                str(root),
                "--today",
                "2026-07-20",
                "--format",
                "json",
            ],
            root,
        )
        all_cli = lambda: _run(  # noqa: E731
            [
                sys.executable,
                str(BIN / "adr-readiness"),
                "--all-proposed",
                "--repo-root",
                str(root),
                "--today",
                "2026-07-20",
                "--format",
                "json",
            ],
            root,
        )
        status_cli = lambda: _run(  # noqa: E731
            [
                sys.executable,
                str(BIN / "adr-status"),
                "--adr-dir",
                str(adr_dir),
                "--format",
                "json",
            ],
            root,
        )
        context_cli = lambda: _run(  # noqa: E731
            [
                sys.executable,
                str(BIN / "adr-context"),
                "--adr-dir",
                str(adr_dir),
                "--format",
                "json",
                "local decision",
            ],
            root,
        )

        def ci_action() -> bytes:
            result = subprocess.run(
                [
                    sys.executable,
                    str(BIN / "adr-readiness-ci"),
                    "--repo-root",
                    str(root),
                    "--base",
                    base,
                    "--head",
                    head,
                    "--today",
                    "2026-07-20",
                ],
                cwd=root,
                capture_output=True,
                text=True,
                encoding="utf-8",
                timeout=10,
            )
            if result.returncode not in (0, 1):
                raise RuntimeError(result.stderr or result.stdout)
            return result.stdout.encode("utf-8")
        request = json.dumps(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {
                    "name": "adr_readiness",
                    "arguments": {
                        "all_proposed": True,
                        "today": "2026-07-20",
                    },
                },
            }
        )
        server = subprocess.Popen(
            [
                sys.executable,
                str(BIN / "adr-mcp"),
                "--root",
                str(root),
            ],
            cwd=root,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            encoding="utf-8",
        )

        def mcp() -> str:
            assert server.stdin is not None and server.stdout is not None
            server.stdin.write(request + "\n")
            server.stdin.flush()
            line = server.stdout.readline()
            if not line:
                raise RuntimeError("adr-mcp closed before returning a response")
            payload = json.loads(line)
            if "error" in payload:
                raise RuntimeError(str(payload["error"]))
            return line

        try:
            measurements = {
                "core_50_adrs": _measure(core, samples),
                "linkage_500_paths_50_adrs": _measure(linkage, samples),
                "single_adr_cli": _measure(single_cli, samples),
                "all_proposed_cli": _measure(all_cli, samples),
                "mcp_all_proposed": _measure(mcp, samples),
                "baseline_adr_status": _measure(status_cli, samples),
                "baseline_adr_context": _measure(context_cli, samples),
                "ci_action_500_paths_50_adrs": _measure(ci_action, samples),
            }
        finally:
            if server.stdin is not None:
                server.stdin.close()
            server.wait(timeout=5)
        measurements["mcp_all_proposed"]["adapter_overhead_ms"] = round(
            float(measurements["mcp_all_proposed"]["p95_ms"])
            - float(measurements["all_proposed_cli"]["p95_ms"]),
            3,
        )
        budgets = {
            "core_50_adrs": 100,
            "linkage_500_paths_50_adrs": 250,
            "single_adr_cli": 500,
            "all_proposed_cli": 1000,
            "ci_action_500_paths_50_adrs": 5000,
        }
        results = {
            name: {
                "budget_p95_ms": budget,
                "passed": float(measurements[name]["p95_ms"]) <= budget,
            }
            for name, budget in budgets.items()
        }
        results["all_proposed_hard"] = {
            "budget_max_ms": 2000,
            "passed": float(measurements["all_proposed_cli"]["max_ms"]) <= 2000,
        }
        results["linkage_hard"] = {
            "budget_max_ms": 1000,
            "passed": float(
                measurements["linkage_500_paths_50_adrs"]["max_ms"]
            )
            <= 1000,
        }
        results["mcp_overhead"] = {
            "budget_ms": 100,
            "passed": float(
                measurements["mcp_all_proposed"]["adapter_overhead_ms"]
            )
            <= 100,
        }
        return {
            "schema_version": 1,
            "environment": {
                "platform": platform.platform(),
                "python": platform.python_version(),
            },
            "fixture": {"adrs": 50, "changed_paths": 500},
            "measurements": measurements,
            "results": results,
            "passed": all(item["passed"] for item in results.values()),
        }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--samples", type=int, default=30)
    args = parser.parse_args()
    if args.samples < 1:
        parser.error("--samples must be positive")
    report = benchmark(args.samples)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
