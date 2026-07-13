"""G1 check: function length ceiling (TICKET-0027 R1, BRIEF-0027-a).

AST-based: every function/method in `src/`, including nested ones, must be
<= 80 physical lines (`end_lineno - lineno + 1`; Python's ast already
excludes decorator lines from a FunctionDef's own lineno). Existing
violations are frozen in `tooling/verify/baselines/function_length.json`
(transition artifact, deleted at TICKET-0027 stage g — see
code_standards.md section 4, R1). Fails if:
  a. a function over 80 lines is absent from the baseline, or
  b. a baselined function now exceeds its recorded length.
Baseline entries may only shrink or disappear; this check never rewrites
the baseline. Missing/unparsable baseline file, or zero functions found
under `src/`, is a FAILURE (fail-closed / vacuous-pass guard).

No DB, stdlib `ast` only.
"""
from __future__ import annotations

import ast
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
SRC = ROOT / "src"
BASELINE_FILE = ROOT / "tooling" / "verify" / "baselines" / "function_length.json"
MAX_LINES = 80

FAILURES: list[str] = []


def fail(msg: str) -> None:
    FAILURES.append(msg)


def _report_and_exit() -> None:
    if FAILURES:
        for msg in FAILURES:
            print(f"FAIL: {msg}")
        sys.exit(1)
    print(
        "PASS: function_length — every function over 80 lines is baselined "
        "at or below its recorded length"
    )
    sys.exit(0)


def _qualname_functions(tree: ast.Module):
    """Yield (qualname, node) for every function/method, including nested
    ones, using Python __qualname__-style dotted naming (Outer.inner,
    ClassName.method)."""
    out: list[tuple[str, ast.AST]] = []

    def visit(node: ast.AST, prefix: str) -> None:
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                qualname = f"{prefix}.{child.name}" if prefix else child.name
                out.append((qualname, child))
                visit(child, qualname)
            elif isinstance(child, ast.ClassDef):
                qualname = f"{prefix}.{child.name}" if prefix else child.name
                visit(child, qualname)
            else:
                visit(child, prefix)

    visit(tree, "")
    return out


def _scan_file(path: pathlib.Path) -> list[dict]:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except SyntaxError as exc:
        fail(f"{path}: SyntaxError: {exc}")
        return []
    rel = path.relative_to(ROOT).as_posix()
    return [
        {"file": rel, "qualname": qualname, "lines": node.end_lineno - node.lineno + 1}
        for qualname, node in _qualname_functions(tree)
    ]


def _strip_json_comments(text: str) -> str:
    return "\n".join(line for line in text.splitlines() if not line.strip().startswith("//"))


def _load_baseline() -> "dict[tuple[str, str], int] | None":
    if not BASELINE_FILE.exists():
        fail(f"{BASELINE_FILE} not found")
        return None
    try:
        data = json.loads(_strip_json_comments(BASELINE_FILE.read_text(encoding="utf-8")))
    except json.JSONDecodeError as exc:
        fail(f"{BASELINE_FILE}: unparsable JSON: {exc}")
        return None
    if not isinstance(data, list):
        fail(f"{BASELINE_FILE}: expected a JSON array at the top level")
        return None
    baseline: dict[tuple[str, str], int] = {}
    for entry in data:
        if not (isinstance(entry, dict) and {"file", "qualname", "lines"} <= entry.keys()):
            fail(f"{BASELINE_FILE}: malformed entry {entry!r}")
            continue
        baseline[(entry["file"], entry["qualname"])] = entry["lines"]
    return baseline


def main() -> None:
    baseline = _load_baseline()
    if baseline is None:
        _report_and_exit()
        return

    py_files = sorted(SRC.rglob("*.py"))
    if not py_files:
        fail("zero .py files found under src/ — parse is broken, not the repo clean")
        _report_and_exit()
        return

    all_functions: list[dict] = []
    for path in py_files:
        all_functions.extend(_scan_file(path))

    if not all_functions:
        fail("zero functions found under src/ — parse is broken, not the repo clean")
        _report_and_exit()
        return

    for entry in all_functions:
        if entry["lines"] <= MAX_LINES:
            continue
        key = (entry["file"], entry["qualname"])
        baselined_lines = baseline.get(key)
        if baselined_lines is None:
            fail(
                f"{entry['file']}::{entry['qualname']} is {entry['lines']} lines "
                f"(> {MAX_LINES}) and not present in {BASELINE_FILE.name}"
            )
        elif entry["lines"] > baselined_lines:
            fail(
                f"{entry['file']}::{entry['qualname']} grew to {entry['lines']} lines, "
                f"past its baselined {baselined_lines}"
            )

    _report_and_exit()


if __name__ == "__main__":
    main()
