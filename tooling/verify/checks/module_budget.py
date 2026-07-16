"""G1 check: module budget (TICKET-0027 R5, BRIEF-0027-a).

AST-based: every module under `src/` stays within 40 top-level functions
+ methods (module-level function defs and methods on module-level classes;
nested closures don't count) AND 1000 physical lines. Exceeding either cap
fails unless the module is baselined in
`tooling/verify/baselines/module_budget.json`, a transition artifact
retired at TICKET-0028's close (code_standards.md section 4, R5) at
values it has not exceeded on either dimension. Baseline entries may only
shrink or disappear; this check never rewrites the baseline. A missing
baseline file is treated as an empty exemption set — the cap is enforced
on every module, fail-closed, not a vacuous pass. An unparsable baseline
file, or zero .py files found under `src/`, is a FAILURE.

No permanent exemptions: a doctrinal registry module legitimately growing
past the cap is the intended tripwire forcing a split — the failing check
IS the mechanism, not a bug to route around.

No DB, stdlib `ast` only.
"""
from __future__ import annotations

import ast
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
SRC = ROOT / "src"
BASELINE_FILE = ROOT / "tooling" / "verify" / "baselines" / "module_budget.json"
MAX_FUNCTIONS = 40
MAX_LINES = 1000

FAILURES: list[str] = []


def fail(msg: str) -> None:
    FAILURES.append(msg)


def _report_and_exit() -> None:
    if FAILURES:
        for msg in FAILURES:
            print(f"FAIL: {msg}")
        sys.exit(1)
    print(
        "PASS: module_budget — every module over 40 functions or 1000 lines "
        "is baselined at or below its recorded values"
    )
    sys.exit(0)


def _top_level_function_count(tree: ast.Module) -> int:
    """Module-level function defs plus methods on module-level classes.
    Nested closures (a function defined inside another function) are not
    counted — they aren't independent surface area."""
    count = 0
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            count += 1
        elif isinstance(node, ast.ClassDef):
            for sub in node.body:
                if isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    count += 1
    return count


def _strip_json_comments(text: str) -> str:
    return "\n".join(line for line in text.splitlines() if not line.strip().startswith("//"))


def _load_baseline() -> "dict[str, tuple[int, int]] | None":
    if not BASELINE_FILE.exists():
        return {}
    try:
        data = json.loads(_strip_json_comments(BASELINE_FILE.read_text(encoding="utf-8")))
    except json.JSONDecodeError as exc:
        fail(f"{BASELINE_FILE}: unparsable JSON: {exc}")
        return None
    if not isinstance(data, list):
        fail(f"{BASELINE_FILE}: expected a JSON array at the top level")
        return None
    baseline: dict[str, tuple[int, int]] = {}
    for entry in data:
        if not (isinstance(entry, dict) and {"file", "functions", "lines"} <= entry.keys()):
            fail(f"{BASELINE_FILE}: malformed entry {entry!r}")
            continue
        baseline[entry["file"]] = (entry["functions"], entry["lines"])
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

    for path in py_files:
        text = path.read_text(encoding="utf-8")
        try:
            tree = ast.parse(text, filename=str(path))
        except SyntaxError as exc:
            fail(f"{path}: SyntaxError: {exc}")
            continue

        rel = path.relative_to(ROOT).as_posix()
        functions = _top_level_function_count(tree)
        lines = len(text.splitlines())

        if functions <= MAX_FUNCTIONS and lines <= MAX_LINES:
            continue

        entry = baseline.get(rel)
        if entry is None:
            fail(
                f"{rel} is {functions} functions / {lines} lines "
                f"(cap {MAX_FUNCTIONS}/{MAX_LINES}) and not present in {BASELINE_FILE.name}"
            )
            continue
        base_functions, base_lines = entry
        if functions > base_functions:
            fail(f"{rel} grew to {functions} functions, past its baselined {base_functions}")
        if lines > base_lines:
            fail(f"{rel} grew to {lines} lines, past its baselined {base_lines}")

    _report_and_exit()


if __name__ == "__main__":
    main()
