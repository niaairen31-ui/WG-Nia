"""G1 check: door terminality + orchestration-only guards (TICKET-0034,
BRIEF-0034-b). AST-based, no DB, on the module_budget.py /
llm_parse_chokepoint.py idiom. Two assertions, both fail-closed (zero
parsed criteria found is a FAILURE, never a vacuous pass):

  a. A1 escalation guard — no table under src/ may take a foreign key on
     `door.id`. `door` stays terminal (TICKET-0034 A1): the day a canon
     row references a door by id, the A1 -> A2 escalation (one `passage`
     row carrying both endpoints) stops being mechanical.
  b. K1 orchestration guard — `src/world_engine/cockpit/spatial_doors.py`
     implements no math: distances, thresholds and spawn offsets belong
     to `placement.py`, the sole placement/distance authority.
"""
from __future__ import annotations

import ast
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
SRC = ROOT / "src"
MODELS_DIR = SRC / "world_engine" / "models"
SPATIAL_DOORS_FILE = SRC / "world_engine" / "cockpit" / "spatial_doors.py"

FAILURES: list[str] = []


def fail(msg: str) -> None:
    FAILURES.append(msg)


def _report_and_exit() -> None:
    if FAILURES:
        for msg in FAILURES:
            print(f"FAIL: {msg}")
        sys.exit(1)
    print("PASS: door_terminal — door.id carries no FK, spatial_doors.py implements no math")
    sys.exit(0)


def _foreign_key_calls(path: pathlib.Path) -> list[ast.Call]:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except SyntaxError as exc:
        fail(f"{path}: SyntaxError: {exc}")
        return []
    calls = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "Field":
            for kw in node.keywords:
                if kw.arg == "foreign_key":
                    calls.append(node)
    return calls


def check_a1_escalation_guard() -> None:
    if not MODELS_DIR.exists():
        fail(f"{MODELS_DIR} does not exist — scan is broken, not the repo clean")
        return

    model_files = sorted(MODELS_DIR.rglob("*.py"))
    if not model_files:
        fail(f"zero .py files found under {MODELS_DIR} — parse is broken, not the repo clean")
        return

    total_foreign_keys = 0
    for path in model_files:
        for call in _foreign_key_calls(path):
            for kw in call.keywords:
                if kw.arg != "foreign_key":
                    continue
                total_foreign_keys += 1
                if isinstance(kw.value, ast.Constant) and kw.value.value == "door.id":
                    rel = path.relative_to(ROOT).as_posix()
                    fail(
                        f"{rel}:{call.lineno} — Field(foreign_key=\"door.id\") found; "
                        "door is terminal (A1) until a deliberate A1 -> A2 escalation"
                    )

    if total_foreign_keys == 0:
        fail(f"zero foreign_key= sites found under {MODELS_DIR} — scan is broken, not the repo clean")


def check_k1_orchestration_guard() -> None:
    if not SPATIAL_DOORS_FILE.exists():
        fail(f"{SPATIAL_DOORS_FILE} does not exist")
        return

    try:
        tree = ast.parse(SPATIAL_DOORS_FILE.read_text(encoding="utf-8"), filename=str(SPATIAL_DOORS_FILE))
    except SyntaxError as exc:
        fail(f"{SPATIAL_DOORS_FILE}: SyntaxError: {exc}")
        return

    reason = "spatial_doors.py orchestrates; distance and offsets belong to placement.py (K1)."

    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            names = [alias.name for alias in node.names]
            module = getattr(node, "module", None)
            forbidden = {"math", "numpy"}
            if (module in forbidden) or any(n in forbidden for n in names):
                fail(f"{SPATIAL_DOORS_FILE}:{node.lineno} — imports a math module. {reason}")

        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Attribute) and node.func.attr in ("hypot", "sqrt"):
                if isinstance(node.func.value, ast.Name) and node.func.value.id == "math":
                    fail(f"{SPATIAL_DOORS_FILE}:{node.lineno} — calls math.{node.func.attr}. {reason}")

        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Pow):
            if isinstance(node.right, ast.Constant) and node.right.value == 0.5:
                fail(f"{SPATIAL_DOORS_FILE}:{node.lineno} — uses **0.5 in place of a placement call. {reason}")


CASES = [
    check_a1_escalation_guard,
    check_k1_orchestration_guard,
]


def main() -> None:
    for case in CASES:
        case()
    _report_and_exit()


if __name__ == "__main__":
    main()
