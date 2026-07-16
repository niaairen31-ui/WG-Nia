"""G1 gate: the `role_change` effect resolves against `faction_role` rows
case-insensitively; an undeclared role without `declare: true`
whole-rejects (K1); `declare: true` on an undeclared role goes through the
L2 declare-and-occupy path, never a direct write (TICKET-0024,
BRIEF-0024-d — corrective, resolution moved from `faction.role_capacities`
to the relational `faction_role` table).

Retargeted (TICKET-0027, BRIEF-0027-c amendment, "check-anchor
relocation"): `_apply_completion_effects` (which holds the `role_change`
effect logic this check scans) moved as-is from `app.py` to
`cockpit/mutations.py`. Same class of anchor as the four checks the
amendment named explicitly — this one tests the same relocated function's
role_change branch, so the amendment's rules apply here too: assertions
preserved verbatim, only the file anchor moves.

Retargeted again (TICKET-0028, BRIEF-0028-e, same precedent): the
role_change branch was decomposed into `_apply_effect_role_change` /
`_resolve_role_change_role`, and the declare-and-occupy branch changed
shape from `elif declare:` to `if declare:` (the resolved/declared branch
above it now returns early, so the elif's condition is unreachable
without it — same L2 semantics, no behavior change). Scanned string
updated to match; assertion (an L2 declare-and-occupy branch exists)
preserved verbatim.

No DB, plain text scan of `mutations.py`.
"""
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
    src = TARGET.read_text(encoding="utf-8")

    if "r.name.casefold() == role_key.casefold()" not in src:
        fail("role resolution is not case-insensitive against faction_role rows")
    if "select(FactionRole).where(FactionRole.faction_id == faction_id)" not in src:
        fail("role resolution does not read the faction_role table")
    if "faction.role_capacities or {}" in src or "capacities = faction.role_capacities" in src:
        fail("role resolution still reads faction.role_capacities directly")
    if "is not declared for" not in src:
        fail("no K1 reject message for an undeclared role without declare")
    if "if declare:" not in src:
        fail("no L2 declare-and-occupy branch (if declare:)")
    if "write_faction_role(" not in src or 'mode="create"' not in src:
        fail("declare branch does not call write_faction_role(mode='create')")
    if "is full (" not in src:
        fail("no capacity-full reject message")
    if "not an active member of" not in src:
        fail("no active-membership reject message (I1)")

    print("PASS: role_change resolves case-insensitively against faction_role; undeclared without declare rejects (K1); declare is L2")
    sys.exit(0)


if __name__ == "__main__":
    main()
