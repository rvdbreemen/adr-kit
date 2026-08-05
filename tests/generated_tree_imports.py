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


def _module_names(node: ast.stmt, source: Path) -> list[list[str]]:
    """Per import, the dotted names it could refer to, relative ones resolved.

    One entry per module the statement imports; each entry is the list of
    spellings that could name it, tried in order. An absolute import has
    exactly one spelling. A relative one has two, because how it resolves
    depends on which directory ends up on sys.path.

    `from .contracts import ...` in clients/installer/detection.py is
    `clients.installer.contracts` when the plugin root is the path root, and
    `installer.contracts` when clients/ is. Only the second was produced
    before, so the first silently failed to resolve and the walk classified a
    first-party module as third-party -- skipping it, and every module it
    reaches, from the closure this helper exists to enforce.
    """
    if isinstance(node, ast.Import):
        return [[alias.name] for alias in node.names]
    if not isinstance(node, ast.ImportFrom):
        return []
    if node.level == 0:
        return [[node.module]] if node.module else []

    package = source.parent
    for _ in range(node.level - 1):
        package = package.parent

    # Walk up while the parent is still a regular package, longest first.
    parts = [package.name]
    cursor = package
    while (cursor.parent / "__init__.py").is_file():
        cursor = cursor.parent
        parts.insert(0, cursor.name)

    prefixes = [".".join(parts)]
    if parts[-1] != prefixes[0]:
        prefixes.append(parts[-1])
    return [[f"{p}.{node.module}" if node.module else p for p in prefixes]]


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
            for spellings in _module_names(node, current):
                # A relative import has more than one valid spelling; the module
                # is present if any of them lands. Only when none do is it worth
                # asking whether the source tree has it.
                resolved = next(
                    (found for s in spellings if (found := _resolve(s, local_roots))), None
                )
                if resolved is not None:
                    if resolved.is_file():
                        queue.append(resolved)
                    continue
                if not any(_resolve(s, source_roots) for s in spellings):
                    continue  # third-party or stdlib, not our problem
                try:
                    where = current.relative_to(tree).as_posix()
                except ValueError:
                    where = current.name
                missing.append((where, spellings[0], lazy))

    return sorted(set(missing))
