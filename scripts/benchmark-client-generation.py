#!/usr/bin/env python3
"""Measure clean and warm deterministic client generation."""

from __future__ import annotations

import argparse
import json
import math
import os
import statistics
import subprocess
import sys
import tempfile
import time
import tracemalloc
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BUILD = ROOT / "scripts" / "build-client-adapters.py"
BASELINE = json.loads(
    (ROOT / "packaging" / "client-generation-baseline.json").read_text(
        encoding="utf-8"
    )
)
BASELINE_P95_MS = BASELINE["p95_ms"]
sys.path.insert(0, str(ROOT / "scripts"))
from client_generation import generate  # noqa: E402


def percentile(values: list[float], fraction: float) -> float:
    return sorted(values)[max(0, math.ceil(fraction * len(values)) - 1)]


def invoke(output: Path, check: bool, timeout: float) -> tuple[float, dict]:
    command = [
        sys.executable,
        str(BUILD),
        "--root",
        str(ROOT),
        "--output-root",
        str(output),
        "--format",
        "json",
    ]
    if check:
        command.append("--check")
    started = time.perf_counter()
    result = subprocess.run(
        command, capture_output=True, text=True, encoding="utf-8", timeout=timeout
    )
    elapsed = (time.perf_counter() - started) * 1000
    if result.returncode:
        raise RuntimeError(result.stdout + result.stderr)
    return elapsed, json.loads(result.stdout)


def summarize(samples: list[tuple[float, dict]], state: str) -> dict:
    elapsed = [sample[0] for sample in samples]
    stats = [sample[1]["stats"] for sample in samples]
    return {
        "state": state,
        "sample_count": len(samples),
        "process_startup_included": state == "clean-full",
        "elapsed_ms": {
            "p50": round(statistics.median(elapsed), 3),
            "p95": round(percentile(elapsed, 0.95), 3),
            "max": round(max(elapsed), 3),
        },
        "files_read": max(item["files_read"] for item in stats),
        "bytes_read": max(item["bytes_read"] for item in stats),
        "files_written": max(item["files_written"] for item in stats),
        "bytes_written": max(item["bytes_written"] for item in stats),
    }


def invoke_warm(output: Path) -> tuple[float, dict]:
    started = time.perf_counter()
    stats, drift = generate(ROOT, output, check=False)
    elapsed = (time.perf_counter() - started) * 1000
    if drift:
        raise RuntimeError("warm generation unexpectedly drifted")
    return elapsed, {"stats": stats.as_dict()}


def startup_calibration(samples: int) -> dict:
    values = []
    for _ in range(samples):
        started = time.perf_counter()
        subprocess.run([sys.executable, "-c", "pass"], check=True)
        values.append((time.perf_counter() - started) * 1000)
    return {
        "sample_count": samples,
        "p50_ms": round(statistics.median(values), 3),
        "p95_ms": round(percentile(values, 0.95), 3),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--samples", type=int, default=11)
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "packaging" / "client-generation-benchmark.json",
    )
    args = parser.parse_args(argv)
    if args.samples < 5:
        parser.error("--samples must be at least 5")

    clean_samples: list[tuple[float, dict]] = []
    warm_samples: list[tuple[float, dict]] = []
    with tempfile.TemporaryDirectory(prefix="adr-kit-generation-") as temporary:
        workspace = Path(temporary)
        for index in range(args.samples):
            clean_samples.append(invoke(workspace / f"clean-{index:03d}", False, 5.0))
        warm_root = workspace / "warm"
        invoke(warm_root, False, 5.0)
        for _ in range(args.samples):
            warm_samples.append(invoke_warm(warm_root))
        tracemalloc.start()
        invoke_warm(warm_root)
        _, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

    clean = summarize(clean_samples, "clean-full")
    warm = summarize(warm_samples, "warm-unchanged")
    regressions = [
        name
        for name, result in (("clean", clean), ("warm", warm))
        if result["elapsed_ms"]["p95"] > BASELINE_P95_MS[name] * 1.2
    ]
    passed = (
        clean["elapsed_ms"]["p50"] <= 1000
        and clean["elapsed_ms"]["p95"] <= 2000
        and clean["elapsed_ms"]["max"] <= 5000
        and warm["elapsed_ms"]["p50"] <= 150
        and warm["elapsed_ms"]["p95"] <= 500
        and warm["elapsed_ms"]["max"] <= 1000
        and warm["files_written"] == 0
        and not regressions
    )
    evidence = {
        "schema_version": 1,
        "platform": {
            "os": os.name,
            "python": sys.version.split()[0],
            "reference": "windows-native" if os.name == "nt" else "best-effort",
        },
        "methodology": {
            "generator": "scripts/build-client-adapters.py",
            "generator_count": 1,
            "cache": "disposable stat-keyed hot path; byte validation on cache miss",
            "cold_state": "new empty output root per sample",
            "warm_state": "persistent Python host, stat-validated fingerprint no-op",
            "warm_process_startup": "amortized once per persistent agent or release host",
            "hard_timeouts_ms": {"clean": 5000, "warm": 1000},
        },
        "standalone_python_startup": startup_calibration(args.samples),
        "approved_baseline_p95_ms": BASELINE_P95_MS,
        "regression_threshold_percent": BASELINE["regression_threshold_percent"],
        "peak_memory_bytes": peak,
        "clean": clean,
        "warm": warm,
        "regressions": regressions,
        "passed": passed,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(evidence, indent=2, sort_keys=True) + "\n"
    if not args.output.exists() or args.output.read_text(encoding="utf-8") != payload:
        temporary = args.output.with_suffix(args.output.suffix + ".tmp")
        temporary.write_text(payload, encoding="utf-8", newline="\n")
        os.replace(temporary, args.output)
    print(json.dumps(evidence, sort_keys=True))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
