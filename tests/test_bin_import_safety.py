"""Import-path safety for everything in bin/ (TASK-62).

The finding: an executable that puts its own directory on sys.path makes that
directory shadow the standard library and site-packages for every import it
performs. Wherever bin/ is attacker-writable -- a self-hosted checkout, a
vendored bin/, or CI running a tool from a pull-request checkout, which
.github/actions/adr-judge does -- a committed bin/<name>.py executes as code.
The explicit insert also defeated CPython's own -P / PYTHONSAFEPATH mitigation
by re-adding the directory that flag removes.

The fix is to load sibling adr_*.py modules by explicit file location and
register them in sys.modules, so the directory never has to be importable.
These tests pin that down two ways:

  * statically, over the source of every file in bin/, so a reintroduced
    `sys.path.insert` fails immediately and by name;
  * behaviourally, by running each executable under -P (where an implicit
    path entry does not exist) and by dropping a hostile module next to a
    mirrored copy, the shape used by
    tests/test_adr_judge_security.py::test_sibling_directory_is_not_importable_by_the_judge.

Static analysis is the load-bearing half here. The dynamic checks only prove
the executables that happen to import a shadowable name today; the static
check is what stops the pattern coming back in a file that does not yet.

Known limit of the static half: the AST walker sees `sys.path.<method>(...)`
calls, not assignments (`sys.path[:] = ...`, `sys.path = ...`). That is the
form bin/adr-lint and bin/adr-doctor deliberately use to MASK their own
directory, and a detector cannot tell a mask from a re-pollution without
evaluating the expression. Left as a call-only check on purpose; the -P and
hostile-module tests below are what cover the assignment form behaviourally.
"""

import ast
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from generated_tree_imports import unresolved_first_party

REPO_ROOT = Path(__file__).resolve().parent.parent
BIN = REPO_ROOT / "bin"


def _bin_files() -> list[Path]:
    return sorted(p for p in BIN.iterdir() if p.is_file() and p.suffix in ("", ".py"))


def _executables() -> list[Path]:
    """Extensionless entry points -- the files run as `python bin/<name>`."""
    return sorted(p for p in BIN.iterdir() if p.is_file() and p.suffix == "")


def _ids(paths) -> list[str]:
    return [p.name for p in paths]


def _tree(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def _sys_path_mutations(tree: ast.Module) -> list[tuple[str, int]]:
    """Every `sys.path.<method>(...)` call in the file, as (method, lineno)."""
    found = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if not isinstance(func, ast.Attribute):
            continue
        owner = func.value
        if (
            isinstance(owner, ast.Attribute)
            and owner.attr == "path"
            and isinstance(owner.value, ast.Name)
            and owner.value.id == "sys"
        ):
            found.append((func.attr, node.lineno))
    return found


# bin/adr-doctor is the one documented exception. Its sibling modules reach into
# scripts/ and clients/ for packages that are not flat siblings, so those two
# roots must be importable -- but they are APPENDED (stdlib and site-packages
# win) and never include bin/ itself.
ALLOWED_SYS_PATH_MUTATORS = {"adr-doctor": {"append"}}


@pytest.mark.parametrize("path", _bin_files(), ids=_ids(_bin_files()))
def test_no_bin_file_puts_a_directory_at_the_front_of_sys_path(path: Path):
    """`sys.path.insert` is banned outright in bin/ -- it IS the finding.

    Position 0 puts the inserted directory ahead of the standard library, which
    is what turns a committed file into executed code. Nothing in bin/ needs it:
    siblings load by explicit file location.
    """
    inserts = [ln for method, ln in _sys_path_mutations(_tree(path)) if method == "insert"]
    assert not inserts, (
        f"{path.name} calls sys.path.insert at line(s) {inserts}. "
        "Load sibling adr_*.py modules with a _load_sibling() SourceFileLoader "
        "helper instead -- see bin/adr-judge."
    )


@pytest.mark.parametrize("path", _bin_files(), ids=_ids(_bin_files()))
def test_other_sys_path_mutations_stay_allowlisted(path: Path):
    """Anything else touching sys.path must be a deliberate, reviewed exception."""
    allowed = ALLOWED_SYS_PATH_MUTATORS.get(path.name, set())
    offenders = sorted(
        {method for method, _ in _sys_path_mutations(_tree(path))} - allowed - {"insert"}
    )
    assert not offenders, (
        f"{path.name} mutates sys.path via {offenders}; add it to "
        "ALLOWED_SYS_PATH_MUTATORS with a comment explaining why, or drop it."
    )


def _sibling_imports(tree: ast.Module) -> set[str]:
    """Sibling module names this file imports, including inside functions."""
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            root = node.module.split(".")[0]
            if root.startswith("adr_"):
                names.add(root)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                root = alias.name.split(".")[0]
                if root.startswith("adr_"):
                    names.add(root)
    return names


def _explicitly_loaded(tree: ast.Module) -> set[str]:
    """Names passed to _load_sibling(), whether called directly or in a loop."""
    loaded = set()
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "_load_sibling"
        ):
            for arg in node.args:
                if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                    loaded.add(arg.value)
        # `for _sibling in ("a", "b"): _load_sibling(_sibling)` -- bin/adr-doctor.
        elif isinstance(node, ast.For) and isinstance(node.iter, (ast.Tuple, ast.List)):
            calls_loader = any(
                isinstance(inner, ast.Call)
                and isinstance(inner.func, ast.Name)
                and inner.func.id == "_load_sibling"
                for inner in ast.walk(node)
            )
            if calls_loader:
                for element in node.iter.elts:
                    if isinstance(element, ast.Constant) and isinstance(element.value, str):
                        loaded.add(element.value)
    return loaded


@pytest.mark.parametrize("path", _executables(), ids=_ids(_executables()))
def test_every_sibling_import_is_backed_by_an_explicit_load(path: Path):
    """A bare `from adr_x import ...` must be preceded by _load_sibling("adr_x").

    Without the sys.modules pre-registration the statement falls through to the
    path finders, which is exactly the dependency on an importable bin/ that
    this change removes -- and it fails outright under -P. Registering the
    module first makes the same statement resolve from the cache.
    """
    tree = _tree(path)
    imported = _sibling_imports(tree)
    if not imported:
        pytest.skip(f"{path.name} imports no sibling modules")
    missing = sorted(imported - _explicitly_loaded(tree))
    assert not missing, (
        f"{path.name} imports {missing} without a matching _load_sibling() call. "
        "Add one, in dependency order, before the import statement."
    )


@pytest.mark.parametrize("path", _executables(), ids=_ids(_executables()))
def test_every_executable_starts_under_python_safe_path(path: Path):
    """No executable may fail to import under -P.

    -P removes the script's own directory from sys.path entirely, so getting
    past the import block there is direct evidence that no module is resolved
    through the path. That is strictly stronger than a plain run, which the
    implicit sys.path[0] would carry even for an unconverted file -- before this
    change bin/adr-readiness, bin/adr-readiness-ci and bin/adr-grill-signal all
    died here with ModuleNotFoundError.

    The exit code is deliberately not asserted: --help is not universal (bin/
    bump-version reads its first argument as a version), and a domain-level
    complaint already proves the imports completed.
    """
    result = subprocess.run(
        [sys.executable, "-P", str(path), "--help"],
        capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60,
    )
    for failure in ("ModuleNotFoundError", "ImportError"):
        assert failure not in result.stderr, (
            f"{path.name} could not import under -P; it still depends on its own "
            f"directory being on sys.path:\n{result.stderr[-800:]}"
        )


# (executable, argv, shadowed module name). One case per distinct exposure:
# adr-lint resolves the optional third-party jsonschema through the path -- the
# exact name the original finding used as its payload -- and adr-doctor resolves
# scripts/adr_settings.py the same way via its doctor modules.
SHADOW_CASES = [
    ("adr-lint", ["--strict", "docs/adr"], "jsonschema"),
    ("adr-doctor", ["docs/adr", "--check", "--format", "json"], "adr_settings"),
]


@pytest.mark.parametrize(
    "executable,argv,shadowed", SHADOW_CASES, ids=[c[0] for c in SHADOW_CASES]
)
def test_module_committed_next_to_an_executable_is_never_imported(
    tmp_path, executable, argv, shadowed
):
    """The end-to-end shape: mirror bin/, commit a payload into it, run.

    Mirrors tests/test_adr_judge_security.py's approach. Both invocation modes
    are checked, and the plain one is the one that matters: -P alone would pass
    even on the unfixed code path, because the implicit sys.path[0] is what
    carries the shadowing during a normal `python bin/<name>` run.
    """
    mirror = tmp_path / "mirror"
    mirror_bin = mirror / "bin"
    mirror_bin.mkdir(parents=True)
    for source in BIN.iterdir():
        if source.is_file():
            shutil.copy2(source, mirror_bin / source.name)
    for tree_name in ("schemas", "templates", "clients", "scripts", "hooks"):
        if (REPO_ROOT / tree_name).exists():
            shutil.copytree(
                REPO_ROOT / tree_name,
                mirror / tree_name,
                ignore=shutil.ignore_patterns("__pycache__"),
            )
    shutil.copytree(REPO_ROOT / "docs" / "adr", mirror / "docs" / "adr")

    marker = tmp_path / "payload-executed.txt"
    (mirror_bin / f"{shadowed}.py").write_text(
        "import pathlib\n"
        f"pathlib.Path({str(marker)!r}).write_text('executed', encoding='utf-8')\n",
        encoding="utf-8",
    )

    # -P (PYTHONSAFEPATH) landed in CPython 3.11. On 3.10 it is not a flag at
    # all: the interpreter exits 2 with "Unknown option", which this loop would
    # read as the tool being broken. The project supports 3.10 (validate.yml
    # runs 3.10 and 3.12), so the variant is skipped rather than the whole test
    # — the "plain" run still proves the shadowing defence on every version,
    # and -P only adds the belt-and-braces case where CPython's own mitigation
    # is active too.
    variants = [([], "plain")]
    if sys.version_info >= (3, 11):
        variants.append((["-P"], "-P"))

    for flags, label in variants:
        if marker.exists():
            marker.unlink()
        result = subprocess.run(
            [sys.executable, *flags, str(mirror_bin / executable), *argv],
            cwd=str(mirror),
            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120,
        )
        assert not marker.exists(), (
            f"bin/{shadowed}.py was imported and executed by {executable} ({label})"
        )
        # Still a working tool from the mirrored location: 0 or 1 are verdicts,
        # 2 is a config or input error and would mean the conversion broke it.
        assert result.returncode in (0, 1), (
            f"{executable} ({label}) rc={result.returncode}:\n{result.stderr[-800:]}"
        )


# ---------------------------------------------------------------------------
# Generated client trees (TASK-125, ADR-032)
#
# bin/adr-doctor died at import in both mirrors: adr_doctor_checks reaches
# scripts/adr_settings.py, which COPY_ROOTS never carried. The hook-side
# invariant added in v0.44.1 would have PASSED on it, because it scanned one
# file one hop deep and the missing module was two hops down. These checks are
# transitive and cover every bin/ entrypoint in both trees.
#
# Gate anchor for ADR-032: adr-doctor-generated-tree-v1
# ---------------------------------------------------------------------------

TREES = {"codex": REPO_ROOT / "codex", "copilot": REPO_ROOT / "copilot"}

# A first-party module a mirror is allowed to lack, with the reason. The
# exclusion is valid ONLY for a lazy import -- see the test below.
DELIBERATELY_ABSENT = {
    "client_generation": (
        "the generator's own source is not mirrored; a mirror has no canonical "
        "inputs to diff. adr_doctor_checks._generated_check returns unsupported "
        "before importing it -- see adr_doctor_models.generated_tree_owner()."
    ),
}


def _tree_cases() -> list[tuple[str, Path]]:
    return [
        (client, entry)
        for client, tree in TREES.items()
        for entry in sorted((tree / "bin").iterdir())
        if entry.is_file() and entry.suffix == ""
    ]


def _tree_ids() -> list[str]:
    return [f"{client}-{entry.name}" for client, entry in _tree_cases()]


@pytest.mark.parametrize("client,executable", _tree_cases(), ids=_tree_ids())
def test_every_bin_entrypoint_resolves_its_import_closure_in_each_client_tree(
    client: str, executable: Path
):
    """Every first-party module an entrypoint reaches must exist in its tree."""
    tree = TREES[client]
    missing = [
        (where, module, lazy)
        for where, module, lazy in unresolved_first_party(
            executable, tree, [tree, tree / "bin", tree / "scripts"], REPO_ROOT
        )
        if module not in DELIBERATELY_ABSENT
    ]
    assert not missing, (
        f"{client}/bin/{executable.name} reaches modules absent from {tree}:\n  "
        + "\n  ".join(
            f"{module} (imported by {where}, lazy={lazy})"
            for where, module, lazy in missing
        )
        + "\n\nDeclare each in client_generation_model.RUNTIME_SUPPORT_FILES."
    )


@pytest.mark.parametrize("client,executable", _tree_cases(), ids=_tree_ids())
def test_only_lazy_imports_may_be_deliberately_absent(client: str, executable: Path):
    """An eager import of an excluded module is never allowed.

    Without this the exclusion list becomes a hole big enough to reproduce the
    v0.44.1 outage with a green suite: someone writes
    `from client_generation import generate` at module scope, the name is on the
    allowlist, and every mirrored hook dies at import while the tests pass.
    """
    tree = TREES[client]
    eager = [
        (where, module)
        for where, module, lazy in unresolved_first_party(
            executable, tree, [tree, tree / "bin", tree / "scripts"], REPO_ROOT
        )
        if module in DELIBERATELY_ABSENT and not lazy
    ]
    assert not eager, (
        f"{client}/bin/{executable.name} imports a deliberately-absent module at "
        "module scope, which kills the entrypoint at import:\n  "
        + "\n  ".join(f"{module} in {where}" for where, module in eager)
        + "\n\nMove it inside the function that has already established the tree "
        "is not a generated mirror."
    )


@pytest.mark.parametrize("client,executable", _tree_cases(), ids=_tree_ids())
def test_every_generated_bin_entrypoint_starts_under_python_safe_path(
    client: str, executable: Path
):
    """The dynamic half: the defect this reproduces is an import-time crash.

    The exit code is deliberately not asserted -- --help is not universal in
    bin/ -- but a ModuleNotFoundError never is.
    """
    result = subprocess.run(
        [sys.executable, "-P", str(executable), "--help"],
        capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60,
    )
    for failure in ("ModuleNotFoundError", "ImportError"):
        assert failure not in result.stderr, (
            f"{client}/bin/{executable.name} could not import from its own tree:\n"
            f"{result.stderr[-800:]}"
        )


def _throwaway_project(tmp_path: Path) -> Path:
    project = tmp_path / "project"
    (project / "docs").mkdir(parents=True)
    shutil.copytree(REPO_ROOT / "docs" / "adr", project / "docs" / "adr")
    return project


@pytest.mark.parametrize("client", sorted(TREES))
def test_mirrored_doctor_reports_only_its_own_client(client: str, tmp_path: Path):
    """ADR-032's reporting contract, asserted end to end.

    Fixing the imports alone would satisfy "it runs" while leaving the doctor
    reporting six failures against paths that were never meant to exist,
    because codex/ IS the plugin root for Codex.
    """
    tree = TREES[client]
    project = _throwaway_project(tmp_path)
    result = subprocess.run(
        [
            sys.executable, str(tree / "bin" / "adr-doctor"), "docs/adr",
            "--check", "--format", "json", "--repo-root", str(project),
        ],
        cwd=str(project),
        capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=180,
    )
    assert result.stdout.strip(), f"no JSON report:\n{result.stderr[-800:]}"
    report = json.loads(result.stdout)

    assert report["summary"]["required_failures"] == 0, result.stdout[-1200:]

    by_key = {(item.get("client"), item["id"]): item for item in report["checks"]}
    generated = by_key[("common", "generated-adapters")]
    assert generated["status"] == "unsupported", generated
    assert generated["required"] is False, generated

    for probe in ("mcp-launcher", "hook-package"):
        assert by_key[(client, probe)]["status"] == "healthy", by_key[(client, probe)]
        for other in ("claude", *sorted(TREES)):
            if other == client:
                continue
            assert by_key[(other, probe)]["status"] == "unsupported", by_key[(other, probe)]


@pytest.mark.parametrize("client", sorted(TREES))
def test_mirrored_doctor_never_writes_inside_its_own_tree(client: str, tmp_path: Path):
    """Repair is the DEFAULT mode, and the tree is a distribution artefact.

    bin/adr-doctor:126 makes repair the default and the init skill runs
    `adr-doctor --fix-index docs/adr/`, so the no-write property has to hold for
    the invocation people actually use, not only under --check.
    """
    tree = TREES[client]
    project = _throwaway_project(tmp_path)

    def snapshot() -> dict[str, str]:
        return {
            str(path.relative_to(tree)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted(tree.rglob("*"))
            if path.is_file() and "__pycache__" not in path.parts
        }

    before = snapshot()
    for extra in ([], ["--fix"]):
        subprocess.run(
            [
                sys.executable, str(tree / "bin" / "adr-doctor"), "docs/adr",
                "--format", "json", "--repo-root", str(project), *extra,
            ],
            cwd=str(project),
            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=180,
        )
    after = snapshot()

    changed = sorted(
        path for path in set(before) | set(after) if before.get(path) != after.get(path)
    )
    assert not changed, (
        f"adr-doctor modified its own {client} tree: {changed}. A repair-mode run "
        "must leave a distribution artefact byte-identical (ADR-032)."
    )
