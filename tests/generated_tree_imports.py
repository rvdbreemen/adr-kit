"""Resolve an entrypoint's first-party import closure inside a generated tree.

Not a test module. Shared by the two invariant tests that ask the same question
of different entrypoints: does every first-party module this file reaches also
exist in the client tree it was mirrored into?

Three properties matter, and a naive version gets each of them wrong.

**Transitive.** The v0.44.1 test scanned one file and resolved one hop. TASK-125's
defect lived two hops down -- `bin/adr-doctor` imports `adr_doctor_checks`, which
exists in the mirror, and `adr_doctor_checks` imports `adr_settings`, which did
not. A per-file scan passes on a live outage.

**Parsed, not grepped.** bin/ uses deliberate function-level imports, so a
`line.startswith("from ")` scan misses them -- including the lazy
`client_generation` import that this whole fix rests on.

**First-party only.** A module is a finding only when it resolves inside the
source tree's search roots and NOT inside the mirror. That is exactly the defect
class, and it keeps bin/adr-lint's optional third-party `jsonschema` from being
reported.
"""

from __future__ import annotations

import ast
from pathlib import Path


def _imports_with_scope(tree: ast.AST) -> list[tuple[ast.stmt, bool]]:
    """Every import node paired with whether it is reachable only via a call.

    An import at module scope is eager: it runs on import and can kill the
    process. One inside a function body is lazy: it runs only if that path is
    taken, which is what makes a deliberately-absent module survivable.
    Recursion per scope rather than a flat ast.walk, because walk() loses the
    enclosing-scope information the distinction depends on.
    """
    found: list[tuple[ast.stmt, bool]] = []

    def visit(node: ast.AST, lazy: bool) -> None:
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.Import, ast.ImportFrom)):
                found.append((child, lazy))
            child_lazy = lazy or isinstance(
                child, (ast.FunctionDef, ast.AsyncFunctionDef)
            )
            visit(child, child_lazy)

    visit(tree, False)
    return found


def _module_names(node: ast.stmt, source: Path) -> list[str]:
    """Dotted module names one import node refers to, relative ones resolved."""
    if isinstance(node, ast.Import):
        return [alias.name for alias in node.names]
    if not isinstance(node, ast.ImportFrom):
        return []
    if node.level == 0:
        return [node.module] if node.module else []
    # `from .contracts import ...` in clients/installer/detection.py: walk up
    # level-1 directories from the importing file to find the package root.
    package = source.parent
    for _ in range(node.level - 1):
        package = package.parent
    prefix = package.name
    return [f"{prefix}.{node.module}" if node.module else prefix]


def _resolve(module: str, roots: list[Path]) -> Path | None:
    """Where a dotted module lives under any of these roots, if anywhere."""
    parts = module.split(".")
    for root in roots:
        base = root.joinpath(*parts)
        for candidate in (base.with_suffix(".py"), base / "__init__.py"):
            if candidate.is_file():
                return candidate
        # A bare directory is an implicit namespace package: accept it so the
        # static walk and the runtime importer agree.
        if base.is_dir():
            return base
    return None


def unresolved_first_party(
    entrypoint: Path,
    tree: Path,
    search_roots: list[Path],
    source_root: Path,
) -> list[tuple[str, str, bool]]:
    """First-party modules the entrypoint reaches that are missing from `tree`.

    Returns (importing file relative to `tree`, module name, is_lazy).

    `search_roots` are the directories the entrypoint itself puts on sys.path,
    in the tree being checked. `source_root` is the canonical checkout, used to
    decide whether a missing module is first-party at all.
    """
    def mirror_of(path: Path) -> Path:
        """The canonical directory corresponding to one of the tree's roots.

        A search root is usually inside the tree, but not always: the hook
        entrypoint lists its own parent, which sits one level above. Walking the
        same number of levels in either direction keeps the two sides aligned
        instead of raising on the upward case.
        """
        if path == tree:
            return source_root
        try:
            return source_root / path.relative_to(tree)
        except ValueError:
            levels = len(tree.parts) - len(path.parts)
            result = source_root
            for _ in range(max(levels, 0)):
                result = result.parent
            return result

    source_roots = [mirror_of(path) for path in search_roots]

    missing: list[tuple[str, str, bool]] = []
    seen: set[Path] = set()
    queue = [entrypoint]

    while queue:
        current = queue.pop()
        if current in seen or not current.is_file():
            continue
        seen.add(current)
        try:
            parsed = ast.parse(current.read_text(encoding="utf-8"), filename=str(current))
        except (SyntaxError, UnicodeDecodeError):
            continue
        # A file's own directory is always importable by it.
        local_roots = [current.parent, *search_roots]
        for node, lazy in _imports_with_scope(parsed):
            for module in _module_names(node, current):
                resolved = _resolve(module, local_roots)
                if resolved is not None:
                    if resolved.is_file():
                        queue.append(resolved)
                    continue
                if _resolve(module, source_roots) is None:
                    continue  # third-party or stdlib, not our problem
                try:
                    where = current.relative_to(tree).as_posix()
                except ValueError:
                    where = current.name
                missing.append((where, module, lazy))

    return sorted(set(missing))
