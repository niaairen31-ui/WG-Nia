"""G1 gate: completion-effects vocabulary is closed to exactly
{relation_delta, ledger_transfer, role_change} (B1, TICKET-0024,
BRIEF-0024-c) — an unknown effect type whole-rejects the mutation.

Retargeted (TICKET-0027, BRIEF-0027-c amendment, "check-anchor
relocation"): `_apply_completion_effects` (and its `_EFFECT_TYPES`
constant) moved as-is from `app.py` to `cockpit/mutations.py`. Same class
of anchor as the four checks the amendment named explicitly
(h1_strip_bounded, prereq_judge, effects_ledger_source,
world_tick:check_apply_mutation_location_write) — this one tests the same
relocated function's vocabulary, so the amendment's rules apply here too:
assertions preserved verbatim, only the file anchor moves.

No DB, stdlib `ast` only.
"""
import ast
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
TARGET = ROOT / "src" / "world_engine" / "cockpit" / "mutations.py"

EXPECTED = {"relation_delta", "ledger_transfer", "role_change"}


def fail(msg):
    print(f"FAIL: {msg}")
    sys.exit(1)


def main():
    if not TARGET.exists():
        fail(f"{TARGET} not found")
    src = TARGET.read_text(encoding="utf-8")
    tree = ast.parse(src, filename=str(TARGET))

    assign = None
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and any(
            isinstance(t, ast.Name) and t.id == "_EFFECT_TYPES" for t in node.targets
        ):
            assign = node
            break
    if assign is None:
        fail("_EFFECT_TYPES not found in mutations.py")

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
