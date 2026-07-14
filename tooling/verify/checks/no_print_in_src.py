"""G1 check: no print() in src/ (TICKET-0027 R3, BRIEF-0027-a).

AST call check (not grep): `print(...)` under `src/world_engine/` must be
zero, except up to a per-file transition allowance in TRANSITION_ALLOW
below — existing sites TICKET-0027 stage f replaces with the `logging`
module (see code_standards.md section 4, R3), which empties this list.
`scripts/` is out of scope by design: operator-facing CLI output stays
`print`. Counts may only shrink; this check never rewrites the list.
Zero .py files found under `src/` is a FAILURE (fail-closed).

No DB, stdlib `ast` only.
"""
from __future__ import annotations

import ast
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
SRC = ROOT / "src"

# Transition allowance: existing print() sites TICKET-0027 stage f replaces
# with logging. Counts may only shrink; empty at stage f.
TRANSITION_ALLOW: dict[str, int] = {
    "src/world_engine/analyzer.py": 12,
    "src/world_engine/tick.py": 26,
}

FAILURES: list[str] = []


def fail(msg: str) -> None:
    FAILURES.append(msg)


def _report_and_exit() -> None:
    if FAILURES:
        for msg in FAILURES:
            print(f"FAIL: {msg}")
        sys.exit(1)
    print(
        "PASS: no_print_in_src — every print() site under src/world_engine/ "
        "is within its transition allowance"
    )
    sys.exit(0)


def _print_call_count(path: pathlib.Path) -> int:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except SyntaxError as exc:
        fail(f"{path}: SyntaxError: {exc}")
        return 0
    return sum(
        1
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "print"
    )


def main() -> None:
    py_files = sorted(SRC.rglob("*.py"))
    if not py_files:
        fail("zero .py files found under src/ — parse is broken, not the repo clean")
        _report_and_exit()
        return

    for path in py_files:
        count = _print_call_count(path)
        if count == 0:
            continue
        rel = path.relative_to(ROOT).as_posix()
        allowed = TRANSITION_ALLOW.get(rel, 0)
        if count > allowed:
            fail(f"{rel} has {count} print() call site(s), past its transition allowance of {allowed}")

    _report_and_exit()


if __name__ == "__main__":
    main()
