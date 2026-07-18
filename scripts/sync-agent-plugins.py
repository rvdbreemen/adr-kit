#!/usr/bin/env python3
"""Build self-contained Codex and Copilot plugin payloads from canonical files."""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CODEX = ROOT / "codex"
COPILOT = ROOT / "copilot"
TARGETS = (CODEX, COPILOT)
DIRECTORIES = ("bin", "schemas", "templates", "instructions")
EXCLUDED_BIN_FILES = {"bump-version"}
COPILOT_REPLACEMENTS = {
    "for Codex": "for GitHub Copilot CLI",
    "from Codex": "from GitHub Copilot CLI",
    "Codex's skill catalog": "Copilot CLI's skill catalog",
    "Codex project": "Copilot CLI project",
    "In Codex,": "In Copilot CLI,",
    "active Codex session": "active Copilot CLI session",
    "Codex config": "Copilot settings",
    "Codex global config": "Copilot global settings",
    "$adr-kit:context": "the ADR Kit context skill",
    "$adr-kit:adr": "the ADR Kit adr skill",
    "$adr-kit:judge": "the ADR Kit judge skill",
    "$adr-kit:setup": "the ADR Kit setup skill",
    "$adr-kit:install-hooks": "the ADR Kit install-hooks skill",
    "$adr-kit:related": "the ADR Kit related skill",
    "$adr-kit:supersede": "the ADR Kit supersede skill",
    "$adr-kit:lint": "the ADR Kit lint skill",
}


def comparison_bytes(path: Path) -> bytes:
    """Normalize checkout EOLs for deterministic cross-platform drift checks."""
    return path.read_bytes().replace(b"\r\n", b"\n")


def sync_directory(source: Path, destination: Path, excluded: set[str] | None = None) -> None:
    excluded = excluded or set()
    if destination.exists():
        shutil.rmtree(destination)
    destination.mkdir(parents=True)
    for path in sorted(source.rglob("*")):
        relative = path.relative_to(source)
        if any(part == "__pycache__" for part in relative.parts):
            continue
        if path.name in excluded:
            continue
        target = destination / relative
        if path.is_dir():
            target.mkdir(parents=True, exist_ok=True)
        elif path.is_file():
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, target)


def expected_copilot_skills() -> dict[Path, bytes]:
    expected: dict[Path, bytes] = {}
    for path in (CODEX / "skills").rglob("*"):
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        for old, new in COPILOT_REPLACEMENTS.items():
            text = text.replace(old, new)
        expected[path.relative_to(CODEX / "skills")] = text.encode("utf-8")
    return expected


def sync_copilot_skills(expected: dict[Path, bytes]) -> None:
    destination = COPILOT / "skills"
    if destination.exists():
        shutil.rmtree(destination)
    for relative, content in expected.items():
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--check",
        action="store_true",
        help="Exit non-zero when the generated payload differs from canonical files.",
    )
    args = parser.parse_args()

    drift: list[str] = []
    for target in TARGETS:
        for name in DIRECTORIES:
            source = ROOT / name
            destination = target / name
            excluded = EXCLUDED_BIN_FILES if name == "bin" else set()
            expected = {
                p.relative_to(source): comparison_bytes(p)
                for p in source.rglob("*")
                if p.is_file()
                and "__pycache__" not in p.parts
                and p.name not in excluded
            }
            actual = (
                {
                    p.relative_to(destination): comparison_bytes(p)
                    for p in destination.rglob("*")
                    if p.is_file() and "__pycache__" not in p.parts
                }
                if destination.is_dir()
                else {}
            )
            if expected != actual:
                drift.append(f"{target.name}/{name}")
                if not args.check:
                    sync_directory(source, destination, excluded)

    expected_skills = expected_copilot_skills()
    actual_skills = (
        {
            p.relative_to(COPILOT / "skills"): comparison_bytes(p)
            for p in (COPILOT / "skills").rglob("*")
            if p.is_file()
        }
        if (COPILOT / "skills").is_dir()
        else {}
    )
    if expected_skills != actual_skills:
        drift.append("copilot/skills")
        if not args.check:
            sync_copilot_skills(expected_skills)

    if args.check and drift:
        print("Codex payload drift: " + ", ".join(drift))
        print("Run: python scripts/sync-agent-plugins.py")
        return 1
    if not args.check:
        print("Synced agent plugin payloads: " + ", ".join(DIRECTORIES))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
