"""G1 check: no undefined names under src/ (TICKET-0027 R8, BRIEF-0027-i).

BRIEF-0027-d's module split left 80 undefined-name sites (pyflakes F821):
a shared private helper stayed in one domain module while its callers moved
to siblings without importing it. Python resolves names at call time, so
every import in the split still succeeded and the route table stayed
set-identical — the defect was invisible to every existing check and only
surfaced as a 500 when a handler touching the missing name actually ran.
This check closes that gap: it runs pyflakes over every file under `src/`
and fails on any `UndefinedName` report, so the class can never ship silent
again. Fail-closed: zero files scanned, or pyflakes unavailable/erroring
mid-scan, is a FAILURE — never treated as a vacuous pass.

Uses `pyflakes.checker.Checker` directly (typed message objects), not the
string-based reporter — filtering the report text would be one grep-fragile
step away from missing a rename of the message text.
"""
from __future__ import annotations

import ast
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
SRC = ROOT / "src"

FAILURES: list[str] = []


def fail(msg: str) -> None:
    FAILURES.append(msg)


def _report_and_exit() -> None:
    if FAILURES:
        for msg in FAILURES:
            print(f"FAIL: {msg}")
        sys.exit(1)
    print("PASS: undefined_names — pyflakes reports zero undefined names under src/")
    sys.exit(0)


def main() -> None:
    try:
        from pyflakes.checker import Checker
        from pyflakes.messages import UndefinedName
    except ImportError:
        fail("pyflakes is not installed — cannot scan for undefined names (fail-closed)")
        _report_and_exit()
        return

    py_files = sorted(SRC.rglob("*.py"))
    if not py_files:
        fail("zero .py files found under src/ — parse is broken, not the repo clean")
        _report_and_exit()
        return

    for path in py_files:
        text = path.read_text(encoding="utf-8")
        rel = path.relative_to(ROOT).as_posix()
        try:
            tree = ast.parse(text, filename=str(path))
        except SyntaxError as exc:
            fail(f"{rel}: SyntaxError: {exc}")
            continue

        checker = Checker(tree, filename=str(path))
        for message in checker.messages:
            if isinstance(message, UndefinedName):
                fail(f"{rel}:{message.lineno}: {message.message % message.message_args}")

    _report_and_exit()


if __name__ == "__main__":
    main()
