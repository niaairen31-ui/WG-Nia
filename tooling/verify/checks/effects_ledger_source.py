"""G1 gate: ledger rows written by completion effects carry
`source_type='tick'` (M1, TICKET-0024, BRIEF-0024-c) — both legs of a
`ledger_transfer` effect, inside `_apply_completion_effects`.

Retargeted (TICKET-0027, BRIEF-0027-c amendment, "check-anchor
relocation"): `_apply_completion_effects` moved as-is (same name) from
`app.py` to `cockpit/mutations.py`. Assertions unchanged. Only the file
anchor moved.

Retargeted again (TICKET-0028, BRIEF-0028-e, same "check-anchor
relocation" precedent): the `ledger_transfer` effect's two
`write_ledger_entry` calls were decomposed out of `_apply_completion_effects`
into their own `_apply_effect_ledger_transfer` helper (in-place extraction,
no behavior change). Assertions unchanged; only the function anchor moved.

No DB, stdlib `ast` only.
"""
import ast
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
TARGET = ROOT / "src" / "world_engine" / "cockpit" / "mutations.py"


def fail(msg):
    print(f"FAIL: {msg}")
    sys.exit(1)


def main():
    if not TARGET.exists():
        fail(f"{TARGET} not found")
    tree = ast.parse(TARGET.read_text(encoding="utf-8"), filename=str(TARGET))

    func = None
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "_apply_effect_ledger_transfer":
            func = node
            break
    if func is None:
        fail("_apply_effect_ledger_transfer not found in mutations.py")

    ledger_calls = [
        n for n in ast.walk(func)
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == "write_ledger_entry"
    ]
    if len(ledger_calls) != 2:
        fail(f"expected exactly 2 write_ledger_entry calls in _apply_effect_ledger_transfer, found {len(ledger_calls)}")

    for call in ledger_calls:
        source_kw = next((kw for kw in call.keywords if kw.arg == "source_type"), None)
        if source_kw is None or not (
            isinstance(source_kw.value, ast.Constant) and source_kw.value.value == "tick"
        ):
            fail(f"write_ledger_entry call at line {call.lineno} does not pass source_type='tick'")

    if "insufficient balance" not in TARGET.read_text(encoding="utf-8"):
        fail("no balance guard reject message found")

    print("PASS: both ledger_transfer legs carry source_type='tick' (M1)")
    sys.exit(0)


if __name__ == "__main__":
    main()
