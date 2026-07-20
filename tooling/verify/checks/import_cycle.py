"""G1 check: no import cycle among `src/world_engine` modules (TICKET-0035).

AST-based, module-level only: only `import` / `from ... import ...`
statements that are direct children of a module's top-level body count as
edges. This codebase's established idiom (BRIEF-0027-b/-d onward) for
breaking a would-be cycle between sibling modules is a *lazy* import
inside a function body (`from . import play_stream as _play_stream`,
etc.) — those never execute at module-load time, so they are correctly
excluded from the graph this check builds. Detecting them would produce
false positives against a deliberate, working pattern.

Builds a directed module -> module dependency graph restricted to modules
under `src/world_engine`, then reports any cycle found via DFS. No DB, no
imports of the modules themselves (AST only, same discipline as
module_budget.py) — this check must never execute application code.
"""
from __future__ import annotations

import ast
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
SRC = ROOT / "src"
PACKAGE_ROOT = "world_engine"

FAILURES: list[str] = []


def fail(msg: str) -> None:
    FAILURES.append(msg)


def _report_and_exit() -> None:
    if FAILURES:
        for msg in FAILURES:
            print(f"FAIL: {msg}")
        sys.exit(1)
    print("PASS: import_cycle — no module-level import cycle under src/world_engine")
    sys.exit(0)


def _module_name_for(path: pathlib.Path) -> tuple[str, bool]:
    """(dotted module name, is_package) for a file under SRC."""
    rel = path.relative_to(SRC)
    parts = list(rel.parts)
    is_pkg = parts[-1] == "__init__.py"
    if is_pkg:
        parts = parts[:-1]
    else:
        parts[-1] = parts[-1][: -len(".py")]
    return ".".join(parts), is_pkg


def _resolve_relative(current_mod: str, is_pkg: bool, level: int, module: str | None) -> str:
    pkg_parts = current_mod.split(".") if is_pkg else current_mod.split(".")[:-1]
    drop = level - 1
    if drop > 0:
        pkg_parts = pkg_parts[:-drop] if drop <= len(pkg_parts) else []
    base = ".".join(pkg_parts)
    if module:
        return f"{base}.{module}" if base else module
    return base


def _edges_for(path: pathlib.Path, tree: ast.Module, current_mod: str, is_pkg: bool) -> set[str]:
    """Module-level (top-of-file only) import targets that resolve inside
    world_engine — never descends into function/class bodies, matching
    the lazy-import idiom this codebase relies on to avoid real cycles."""
    targets: set[str] = set()
    for node in tree.body:
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == PACKAGE_ROOT or alias.name.startswith(PACKAGE_ROOT + "."):
                    targets.add(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.level and node.level > 0:
                base = _resolve_relative(current_mod, is_pkg, node.level, node.module)
                if base == PACKAGE_ROOT or base.startswith(PACKAGE_ROOT + "."):
                    if node.module is None:
                        for alias in node.names:
                            targets.add(f"{base}.{alias.name}")
                    else:
                        targets.add(base)
            elif node.module and (
                node.module == PACKAGE_ROOT or node.module.startswith(PACKAGE_ROOT + ".")
            ):
                targets.add(node.module)
    return targets


def _find_cycle(graph: dict[str, set[str]]) -> list[str] | None:
    WHITE, GRAY, BLACK = 0, 1, 2
    color: dict[str, int] = {m: WHITE for m in graph}
    path: list[str] = []

    def dfs(mod: str) -> list[str] | None:
        color[mod] = GRAY
        path.append(mod)
        for nxt in sorted(graph.get(mod, ())):
            if nxt not in graph:
                continue
            if color[nxt] == GRAY:
                cycle_start = path.index(nxt)
                return path[cycle_start:] + [nxt]
            if color[nxt] == WHITE:
                result = dfs(nxt)
                if result is not None:
                    return result
        path.pop()
        color[mod] = BLACK
        return None

    for mod in sorted(graph):
        if color[mod] == WHITE:
            result = dfs(mod)
            if result is not None:
                return result
    return None


def main() -> None:
    py_files = sorted(SRC.rglob("*.py"))
    if not py_files:
        fail("zero .py files found under src/ — parse is broken, not the repo clean")
        _report_and_exit()
        return

    graph: dict[str, set[str]] = {}
    modules: dict[str, pathlib.Path] = {}
    for path in py_files:
        text = path.read_text(encoding="utf-8")
        try:
            tree = ast.parse(text, filename=str(path))
        except SyntaxError as exc:
            fail(f"{path}: SyntaxError: {exc}")
            continue
        mod_name, is_pkg = _module_name_for(path)
        modules[mod_name] = path
        graph[mod_name] = _edges_for(path, tree, mod_name, is_pkg)

    if FAILURES:
        _report_and_exit()
        return

    cycle = _find_cycle(graph)
    if cycle is not None:
        fail("module-level import cycle: " + " -> ".join(cycle))

    _report_and_exit()


if __name__ == "__main__":
    main()
