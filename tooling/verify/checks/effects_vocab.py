"""G1 gate: completion-effects vocabulary is closed to exactly
{relation_delta, ledger_transfer, role_change} (B1, TICKET-0024,
BRIEF-0024-c) — an unknown effect type whole-rejects the mutation.

No DB, stdlib `ast` only.
"""
import ast
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
APP = ROOT / "src" / "world_engine" / "cockpit" / "app.py"

EXPECTED = {"relation_delta", "ledger_transfer", "role_change"}


def fail(msg):
    print(f"FAIL: {msg}")
    sys.exit(1)


def main():
    if not APP.exists():
        fail(f"{APP} not found")
    src = APP.read_text(encoding="utf-8")
    tree = ast.parse(src, filename=str(APP))

    assign = None
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and any(
            isinstance(t, ast.Name) and t.id == "_EFFECT_TYPES" for t in node.targets
        ):
            assign = node
            break
    if assign is None:
        fail("_EFFECT_TYPES not found in app.py")

    values = {
        n.value for n in ast.walk(assign.value)
        if isinstance(n, ast.Constant) and isinstance(n.value, str)
    }
    if values != EXPECTED:
        fail(f"_EFFECT_TYPES = {values!r}, expected {EXPECTED!r}")

    if "eff_type not in _EFFECT_TYPES" not in src:
        fail("no vocabulary-membership guard found (eff_type not in _EFFECT_TYPES)")
    if "unknown effect type" not in src:
        fail("no whole-reject message for an unknown effect type")
    if "too many effects" not in src:
        fail("no N1 cardinality reject (too many effects)")

    print("PASS: effects vocabulary closed to relation_delta/ledger_transfer/role_change")
    sys.exit(0)


if __name__ == "__main__":
    main()
