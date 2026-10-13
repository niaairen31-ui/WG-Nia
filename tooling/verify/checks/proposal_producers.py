"""G1 check for TICKET-0115 -- every proposal names its producer from one closed list, and code-made proposals are reviewed like a model's (INV-14).

BRIEF-0115-C's rules (B2 of the conditions series' dashboard).

PP1 -- every producer is named (AST of `src/world_engine/**/*.py`). Every
   `ProposedMutation(...)` call passes `proposed_by=`, and every
   `<x>.proposed_by = ...` assignment sets one; each value is a string
   literal or a name bound at module level to one (in any module of the
   package). The values found equal `proposal_producers.PRODUCERS`' keys
   exactly: a producer missing from the list, or a listed producer nobody
   writes, fails. Zero sites is a FAILURE.
PP2 -- the list (import). Each producer's kind is one of `PRODUCER_KINDS`
   and its label is not empty; no value is both live and legacy;
   `producer_label` names a legacy value and an unknown one.
PP3 -- never auto-applied (AST). Every `ProposedMutation(...)` whose
   producer is of kind `engine` or `model` passes no `status=` other than
   `"proposed"`; outside `cockpit/routes/mutations.py`, only the modules
   writing an `auto` producer call `_approve_apply_and_commit` or
   `_apply_mutation`.
PP4 -- Journée's objective event (AST). `day_events.py`'s one
   `ProposedMutation(` passes `proposed_by="engine"`: no model is asked
   (Bt1 of 0119).

Stdlib plus the package's own `proposal_producers`; no DB.
"""
from __future__ import annotations

import ast
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
PKG = ROOT / "src" / "world_engine"
ROUTES = PKG / "cockpit" / "routes" / "mutations.py"
DAY_EVENTS = PKG / "day_events.py"

FAILURES: list[str] = []


def fail(msg: str) -> None:
    FAILURES.append(msg)


def _modules() -> dict[pathlib.Path, ast.Module]:
    return {p: ast.parse(p.read_text(encoding="utf-8")) for p in sorted(PKG.rglob("*.py"))}


def _constants(trees: dict[pathlib.Path, ast.Module]) -> dict[str, set[str]]:
    """Every module-level `NAME = "literal"` of the package, by name."""
    out: dict[str, set[str]] = {}
    for tree in trees.values():
        for node in tree.body:
            targets = node.targets if isinstance(node, ast.Assign) else \
                [node.target] if isinstance(node, ast.AnnAssign) and node.value is not None else []
            value = node.value if isinstance(node, (ast.Assign, ast.AnnAssign)) else None
            if isinstance(value, ast.Constant) and isinstance(value.value, str):
                for t in targets:
                    if isinstance(t, ast.Name):
                        out.setdefault(t.id, set()).add(value.value)
    return out


def _value(node: ast.AST, constants: dict[str, set[str]]) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.Name) and len(constants.get(node.id, ())) == 1:
        return next(iter(constants[node.id]))
    return None


def _is_ctor(node: ast.AST) -> bool:
    return isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "ProposedMutation"


def _sites(trees, constants) -> list[tuple[pathlib.Path, int, str | None, ast.Call | None]]:
    sites = []
    for path, tree in trees.items():
        for node in ast.walk(tree):
            if _is_ctor(node):
                kw = next((k for k in node.keywords if k.arg == "proposed_by"), None)
                sites.append((path, node.lineno, _value(kw.value, constants) if kw else None, node))
                if kw is None:
                    fail(f"PP1: {path.relative_to(ROOT)}:{node.lineno} builds a ProposedMutation with no proposed_by")
            elif isinstance(node, ast.Assign) and any(
                    isinstance(t, ast.Attribute) and t.attr == "proposed_by" for t in node.targets):
                sites.append((path, node.lineno, _value(node.value, constants), None))
    return sites


def check_pp1(sites) -> None:
    from world_engine.proposal_producers import PRODUCERS

    if not sites:
        fail("PP1: no ProposedMutation construction found")
        return
    found = set()
    for path, line, value, _call in sites:
        if value is None:
            fail(f"PP1: {path.relative_to(ROOT)}:{line} sets proposed_by to no literal or module constant")
        else:
            found.add(value)
    if found != set(PRODUCERS):
        fail(f"PP1: written {sorted(found)}, listed {sorted(PRODUCERS)}")


def check_pp2() -> None:
    from world_engine.proposal_producers import (
        LEGACY_PRODUCERS, PRODUCER_KINDS, PRODUCERS, UNKNOWN_PRODUCER_FR, producer_label,
    )

    if not PRODUCERS or not LEGACY_PRODUCERS:
        fail("PP2: an empty producer list")
    for value, (kind, label) in PRODUCERS.items():
        if kind not in PRODUCER_KINDS or not label.strip():
            fail(f"PP2: {value!r} is ({kind!r}, {label!r})")
    if set(PRODUCERS) & set(LEGACY_PRODUCERS):
        fail(f"PP2: live and legacy {sorted(set(PRODUCERS) & set(LEGACY_PRODUCERS))}")
    legacy = next(iter(LEGACY_PRODUCERS))
    if producer_label(legacy) != LEGACY_PRODUCERS[legacy] or producer_label("nobody") != UNKNOWN_PRODUCER_FR:
        fail("PP2: producer_label does not name a legacy or an unknown producer")


def _calls(tree: ast.AST, names: set[str]) -> bool:
    return any(isinstance(n, ast.Call) and ((isinstance(n.func, ast.Name) and n.func.id in names)
                                            or (isinstance(n.func, ast.Attribute) and n.func.attr in names))
               for n in ast.walk(tree))


def check_pp3(trees, sites) -> None:
    from world_engine.proposal_producers import PRODUCERS

    auto_modules = set()
    checked = 0
    for path, line, value, call in sites:
        kind = PRODUCERS.get(value or "", ("", ""))[0]
        if kind == "auto":
            auto_modules.add(path)
        if call is None or kind not in ("engine", "model"):
            continue
        checked += 1
        status = next((k.value for k in call.keywords if k.arg == "status"), None)
        if status is not None and not (isinstance(status, ast.Constant) and status.value == "proposed"):
            fail(f"PP3: {path.relative_to(ROOT)}:{line} builds a {kind} proposal not 'proposed'")
    if not checked or not auto_modules:
        fail(f"PP3: {checked} reviewed producer site(s), {len(auto_modules)} auto module(s)")
    for path, tree in trees.items():
        if path == ROUTES or path in auto_modules:
            continue
        if _calls(tree, {"_approve_apply_and_commit", "_apply_mutation"}):
            fail(f"PP3: {path.relative_to(ROOT)} applies a proposal itself")


def check_pp4(sites) -> None:
    mine = [value for path, _line, value, call in sites if path == DAY_EVENTS and call is not None]
    if mine != ["engine"]:
        fail(f"PP4: day_events.py proposes as {mine}")


def main() -> None:
    sys.path.insert(0, str(ROOT / "src"))
    trees = _modules()
    sites = _sites(trees, _constants(trees))
    check_pp1(sites)
    check_pp2()
    check_pp3(trees, sites)
    check_pp4(sites)
    if FAILURES:
        for msg in FAILURES:
            print(f"FAIL: {msg}")
        sys.exit(1)
    print(f"PASS: proposal_producers -- {len(sites)} producer site(s), each naming a listed producer; "
          "code-made proposals are reviewed")


if __name__ == "__main__":
    main()
