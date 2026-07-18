"""Static syntax guard for the documented Python 3.10 runtime floor."""

from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


def python_sources() -> list[Path]:
    sources = sorted((ROOT / "scripts").glob("*.py"))
    for path in sorted((ROOT / "bin").iterdir()):
        if not path.is_file():
            continue
        first_line = path.read_bytes().splitlines()[:1]
        if first_line and b"python" in first_line[0].lower():
            sources.append(path)
    return sources


def test_runtime_sources_parse_with_python_310_grammar():
    sources = python_sources()
    assert sources
    failures = []
    for path in sources:
        try:
            ast.parse(
                path.read_text(encoding="utf-8"),
                filename=str(path),
                feature_version=10,
            )
        except SyntaxError as exc:
            failures.append(f"{path.relative_to(ROOT)}:{exc.lineno}: {exc.msg}")
    assert failures == []
