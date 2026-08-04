"""Test helpers are imported by bare name, never as `tests.<module>`.

`tests/` has no `__init__.py`, so it is a namespace package. `pytest.ini` sets
`pythonpath = .`, which puts the repository root on `sys.path`, and that is
enough for `tests.adr_fixtures` to resolve -- until something shadows it. Any
installed distribution that ships a real top-level `tests` package wins, because
a regular package always beats a namespace portion.

That is why the dotted form is banned rather than merely discouraged: whether it
works is a property of the machine, not of this repository. It resolved in CI and
raised ModuleNotFoundError on a developer box that happened to have such a
distribution installed, and the version that reached `dev` (TASK-132) was the one
CI could import and a developer could not.

This gate is pure text analysis, so its verdict does not depend on what is
installed where it runs.
"""

from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TESTS = ROOT / "tests"


def _dotted_imports(path: Path) -> list[str]:
    """Return every `tests.*` import in one module, by source text.

    Parsed rather than grepped so a mention inside a string or a comment -- this
    module is full of them -- is not mistaken for an import.
    """
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    found: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if module == "tests" or module.startswith("tests."):
                found.append(f"{path.name}:{node.lineno}: from {module} import ...")
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "tests" or alias.name.startswith("tests."):
                    found.append(f"{path.name}:{node.lineno}: import {alias.name}")
    return found


def test_no_test_module_imports_a_helper_through_the_tests_package():
    offenders = sorted(
        entry for path in TESTS.rglob("*.py") for entry in _dotted_imports(path)
    )
    assert not offenders, (
        "test helpers must be imported by bare name:\n  "
        + "\n  ".join(offenders)
        + "\n\nUse `from adr_fixtures import ...`, not `from tests.adr_fixtures import ...`. "
        "tests/ is a namespace package, so the dotted form resolves or fails "
        "depending on what is installed on the machine running the suite."
    )


def test_the_tests_directory_is_still_a_namespace_package():
    """If tests/__init__.py ever appears, this gate's reasoning changes.

    A real package would make the dotted form reliable and the convention
    arbitrary. Whoever adds it should revisit this file rather than delete the
    failing assertion.
    """
    assert not (TESTS / "__init__.py").exists(), (
        "tests/__init__.py now exists, which makes tests/ a regular package and "
        "the dotted import form reliable. Revisit tests/test_import_convention.py "
        "and the comments in test_adr_policy.py, test_adr_lint_clarity.py and "
        "test_adr_audit_command.py, which all explain the ban in terms of "
        "namespace-package shadowing."
    )
