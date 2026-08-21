"""G1 check: module budget (TICKET-0027 R5, BRIEF-0027-a; frontend rule
added TICKET-0059, BRIEF-0059-b, Amendment 6).

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

A second, separate rule (frontend_line_budget) covers `frontend/src/**/
*.svelte` and `frontend/src/**/*.js`: the same 1000-line ceiling (R5),
line-count only (no AST, no function-count dimension — Svelte files
aren't Python). No exemption mechanism for this rule: every file is under
the cap as of TICKET-0059, so there is nothing to grandfather. A glob
collecting zero frontend files is a FAILURE, not a pass — the same
vacuous-proof guard as the Python rule's zero-.py-files case.

A third rule (legacy_document_ratchet, TICKET-0061, BRIEF-0061-b, A3)
covers the one file the other two rules structurally cannot reach: the
legacy document (`src/world_engine/cockpit/legacy.html`) is neither
`src/**/*.py` nor `frontend/src/**/*.{svelte,js}`, and under decision A3
its exemption from every other budget lives a year or more. This is a
RATCHET, not the 1000-line cap (which would be red on arrival and prove
nothing): `LEGACY_DOCUMENT_LINE_CEILING` is a named constant recording
the document's committed line count, and it may only ever decrease.
Exceeding it is a FAILURE naming both numbers; coming in UNDER it is
also a FAILURE, instructing that the constant be lowered to the new
count in the same commit — the document stays on the same
monotonically-shrinking discipline as `LEGACY_MOUNTS`, and the constant
can never silently drift above the truth. The file's absence is a
FAILURE, not a vacuous pass.

No DB, stdlib `ast` only (the frontend and legacy-document rules add no
dependency — both are line counts).
"""
from __future__ import annotations

import ast
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
SRC = ROOT / "src"
FRONTEND_SRC = ROOT / "frontend" / "src"
BASELINE_FILE = ROOT / "tooling" / "verify" / "baselines" / "module_budget.json"
MAX_FUNCTIONS = 40
MAX_LINES = 1000
FRONTEND_MAX_LINES = 1000

LEGACY_DOCUMENT = ROOT / "src" / "world_engine" / "cockpit" / "legacy.html"
# Ratchet ceiling, TICKET-0061 BRIEF-0061-b (A3): the legacy document's
# committed line count. May only ever DECREASE -- lower this constant to
# the new count in the same commit that shrinks the file. Never raise it.
LEGACY_DOCUMENT_LINE_CEILING = 2762

FAILURES: list[str] = []


def fail(msg: str) -> None:
    FAILURES.append(msg)


def _report_and_exit(frontend_count: int | None = None, legacy_lines: int | None = None) -> None:
    if FAILURES:
        for msg in FAILURES:
            print(f"FAIL: {msg}")
        sys.exit(1)
    print(
        "PASS: module_budget — every module over 40 functions or 1000 lines "
        "is baselined at or below its recorded values"
        + (f"; {frontend_count} frontend file(s) within the 1000-line cap" if frontend_count is not None else "")
        + (f"; legacy document at its ratcheted {legacy_lines}-line ceiling" if legacy_lines is not None else "")
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


def _check_frontend_line_budget() -> int | None:
    """rule: frontend_line_budget. No AST, no baseline, no exemption —
    line count only, over frontend/src/**/*.svelte and **/*.js."""
    if not FRONTEND_SRC.is_dir():
        fail(f"frontend_line_budget: {FRONTEND_SRC} is not a directory")
        return None
    frontend_files = sorted(
        p for p in FRONTEND_SRC.rglob("*") if p.is_file() and p.suffix in (".svelte", ".js")
    )
    if not frontend_files:
        fail("frontend_line_budget: zero .svelte/.js files found under frontend/src/ — vacuous scan")
        return None

    for path in frontend_files:
        lines = len(path.read_text(encoding="utf-8").splitlines())
        if lines > FRONTEND_MAX_LINES:
            rel = path.relative_to(ROOT).as_posix()
            fail(f"frontend_line_budget: {rel} is {lines} lines, past the {FRONTEND_MAX_LINES}-line cap")

    return len(frontend_files)


def _check_legacy_document_ratchet() -> int | None:
    """rule: legacy_document_ratchet. Not a cap -- a ratchet. Exceeding
    LEGACY_DOCUMENT_LINE_CEILING fails naming both numbers; coming in
    UNDER it also fails, instructing the constant be lowered, so it can
    never silently drift above the truth. Absence is a FAILURE."""
    if not LEGACY_DOCUMENT.is_file():
        fail(f"legacy_document_ratchet: {LEGACY_DOCUMENT} does not exist")
        return None
    lines = len(LEGACY_DOCUMENT.read_text(encoding="utf-8").splitlines())
    if lines > LEGACY_DOCUMENT_LINE_CEILING:
        fail(
            f"legacy_document_ratchet: {LEGACY_DOCUMENT.relative_to(ROOT).as_posix()} "
            f"grew to {lines} lines, past its ratcheted ceiling of {LEGACY_DOCUMENT_LINE_CEILING}"
        )
        return None
    if lines < LEGACY_DOCUMENT_LINE_CEILING:
        fail(
            f"legacy_document_ratchet: {LEGACY_DOCUMENT.relative_to(ROOT).as_posix()} "
            f"shrank to {lines} lines, under its ratcheted ceiling of {LEGACY_DOCUMENT_LINE_CEILING} -- "
            f"lower LEGACY_DOCUMENT_LINE_CEILING to {lines} in this same commit"
        )
        return None
    return lines


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

    frontend_count = _check_frontend_line_budget()
    legacy_lines = _check_legacy_document_ratchet()

    _report_and_exit(frontend_count, legacy_lines)


if __name__ == "__main__":
    main()
