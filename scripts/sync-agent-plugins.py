#!/usr/bin/env python3
"""Compatibility entrypoint for the bounded client artifact generator."""

from __future__ import annotations

import runpy
from pathlib import Path


def comparison_bytes(path: Path) -> bytes:
    """Normalize checkout EOLs for compatibility with existing callers."""
    return path.read_bytes().replace(b"\r\n", b"\n")


if __name__ == "__main__":
    target = Path(__file__).with_name("build-client-adapters.py")
    runpy.run_path(str(target), run_name="__main__")
