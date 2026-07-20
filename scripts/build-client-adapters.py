#!/usr/bin/env python3
"""Generate or drift-check the three supported ADR Kit client adapters."""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path

from client_generation import GenerationError, generate
from client_certification import support_matrix, validate
from client_evidence import CertificationError, assemble_native_bundle, write_bundle


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="fail when generated files drift")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent.parent)
    parser.add_argument("--output-root", type=Path)
    parser.add_argument("--format", choices=("human", "json"), default="human")
    parser.add_argument("--certify", type=Path)
    parser.add_argument("--candidate-commit")
    parser.add_argument("--release-candidate", action="store_true")
    parser.add_argument("--support-output", type=Path)
    parser.add_argument(
        "--assemble-native-evidence",
        type=Path,
        metavar="DIRECTORY",
        help="assemble DIRECTORY/{claude,codex,copilot}/windows-native.json",
    )
    parser.add_argument("--evidence-output", type=Path)
    args = parser.parse_args(argv)
    if args.assemble_native_evidence:
        if not args.candidate_commit or not args.evidence_output:
            parser.error(
                "--assemble-native-evidence requires --candidate-commit and "
                "--evidence-output"
            )
        try:
            bundle = assemble_native_bundle(
                args.assemble_native_evidence,
                args.root.resolve(),
                args.candidate_commit,
            )
            matched = write_bundle(args.evidence_output, bundle, args.check)
        except (CertificationError, OSError) as exc:
            result = {"passed": False, "errors": [str(exc)]}
            print(
                json.dumps(result, sort_keys=True)
                if args.format == "json"
                else f"native evidence assembly failed: {exc}"
            )
            return 1
        result = {
            "passed": matched,
            "check": args.check,
            "candidate_commit": args.candidate_commit,
            "output": str(args.evidence_output),
            "errors": [] if matched else ["assembled evidence bundle drift"],
        }
        print(
            json.dumps(result, sort_keys=True)
            if args.format == "json"
            else (
                "Native evidence bundle "
                + ("validated" if args.check else "assembled")
            )
        )
        return 0 if matched else 1
    if args.certify:
        if not args.candidate_commit:
            parser.error("--certify requires --candidate-commit")
        if not re.fullmatch(
            r"[0-9a-fA-F]{7,64}|simulated-[a-z0-9-]+", args.candidate_commit
        ):
            parser.error("candidate commit must be a commit hash or simulated fixture id")
        try:
            bundle = json.loads(args.certify.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            print(f"certification bundle error: {exc}", file=sys.stderr)
            return 2
        errors = validate(bundle, args.candidate_commit, args.release_candidate, 30)
        if args.support_output and not errors:
            payload = support_matrix(bundle)
            if args.check:
                if (
                    not args.support_output.is_file()
                    or args.support_output.read_text(encoding="utf-8") != payload
                ):
                    errors.append("generated support matrix drift")
            else:
                args.support_output.parent.mkdir(parents=True, exist_ok=True)
                if (
                    not args.support_output.is_file()
                    or args.support_output.read_text(encoding="utf-8") != payload
                ):
                    args.support_output.write_text(
                        payload, encoding="utf-8", newline="\n"
                    )
        result = {
            "passed": not errors,
            "release_candidate": args.release_candidate,
            "errors": errors,
        }
        print(
            json.dumps(result, sort_keys=True)
            if args.format == "json"
            else ("\n".join(errors) if errors else "Three-client certification gate passed")
        )
        return 1 if errors else 0
    started = time.perf_counter_ns()
    try:
        stats, drift = generate(args.root, args.output_root, args.check)
    except (GenerationError, OSError) as exc:
        print(f"client adapter generation failed: {exc}", file=sys.stderr)
        return 2
    result = {
        "status": "drift" if drift else "clean",
        "check": args.check,
        "drift": drift,
        "stats": stats.as_dict(),
        "elapsed_ms": round((time.perf_counter_ns() - started) / 1_000_000, 3),
    }
    if args.format == "json":
        print(json.dumps(result, sort_keys=True))
    elif drift and args.check:
        print("Client adapter drift: " + ", ".join(drift))
        print("Run: python scripts/build-client-adapters.py")
    else:
        action = "Validated" if args.check else "Generated"
        print(f"{action} three client adapters; changed={len(drift)}, written={stats.files_written}")
    return 1 if args.check and drift else 0


if __name__ == "__main__":
    raise SystemExit(main())
