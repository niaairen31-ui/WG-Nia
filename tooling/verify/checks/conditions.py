"""G1 check for TICKET-0111 -- the condition language.

The lot adds its pieces brief by brief; this check grows with it (the
`quests.py` and `debts.py` precedent). Each brief adds its rules here in
the same commit.

CA1 -- the forms have one home (BRIEF-0111-A, static, AST). Each of
   `REQUIREMENT_TYPES`, `MODEL_REQUIREMENT_TYPES`, `ENTITY_TARGET_TYPES`,
   `KEY_TARGET_TYPES`, `THRESHOLD_TYPES`, `_EVALUATORS`, `RequirementSpec`,
   `Verdict`, `evaluate_specs` and `_day_reachable_ids` is defined at module
   level in `condition_forms.py`, and each but `Verdict` in no other module
   under `src/` (`resolution.py` and `skill_lexicon.py` declare verdicts of
   their own); no other module defines a function of the same name as one
   of its `_eval_*` evaluators.

A rule that collects nothing fails.
"""
from __future__ import annotations

import ast
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
SRC = ROOT / "src" / "world_engine"
FORMS_FILE = SRC / "condition_forms.py"

FAILURES: list[str] = []

FORM_NAMES = (
    "REQUIREMENT_TYPES", "MODEL_REQUIREMENT_TYPES", "ENTITY_TARGET_TYPES", "KEY_TARGET_TYPES",
    "THRESHOLD_TYPES", "_EVALUATORS", "RequirementSpec", "Verdict", "evaluate_specs", "_day_reachable_ids",
)

# `Verdict` is a common name: `resolution.Verdict` and `skill_lexicon.Verdict`
# are other things. Every other name is the forms' alone.
UNIQUE_NAMES = tuple(n for n in FORM_NAMES if n != "Verdict")


def fail(msg: str) -> None:
    FAILURES.append(msg)


def _top_level_names(tree: ast.Module) -> set[str]:
    names: set[str] = set()
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
            names.add(node.name)
        elif isinstance(node, ast.Assign):
            names.update(t.id for t in node.targets if isinstance(t, ast.Name))
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            names.add(node.target.id)
    return names


def _modules() -> dict[pathlib.Path, set[str]]:
    found: dict[pathlib.Path, set[str]] = {}
    for path in sorted(SRC.rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        found[path] = _top_level_names(ast.parse(path.read_text(encoding="utf-8"), filename=str(path)))
    return found


# --- CA1 -----------------------------------------------------------------------

def check_ca1() -> None:
    modules = _modules()
    if FORMS_FILE not in modules:
        fail("CA1: condition_forms.py is missing")
        return
    home = modules[FORMS_FILE]
    for name in FORM_NAMES:
        if name not in home:
            fail(f"CA1: condition_forms.py does not define {name}")
    evaluators = sorted(n for n in home if n.startswith("_eval_"))
    if not evaluators:
        fail("CA1: condition_forms.py defines zero _eval_* functions")
    for path, names in modules.items():
        if path == FORMS_FILE:
            continue
        rel = path.relative_to(SRC.parent).as_posix()
        for name in UNIQUE_NAMES:
            if name in names:
                fail(f"CA1: {rel} defines {name}, which lives in condition_forms.py")
        for name in sorted(n for n in names if n.startswith("_eval_") and n in evaluators):
            fail(f"CA1: {rel} defines the evaluator {name}, which lives in condition_forms.py")


def main() -> int:
    check_ca1()
    if FAILURES:
        for msg in FAILURES:
            print(f"FAIL: {msg}")
        return 1
    print("PASS: conditions -- the requirement forms, their evaluators and their BFS live in "
          "condition_forms.py alone")
    return 0


if __name__ == "__main__":
    sys.exit(main())
