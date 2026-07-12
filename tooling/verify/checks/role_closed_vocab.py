"""G1 gate: the `role_change` effect resolves against `faction_role` rows
case-insensitively; an undeclared role without `declare: true`
whole-rejects (K1); `declare: true` on an undeclared role goes through the
L2 declare-and-occupy path, never a direct write (TICKET-0024,
BRIEF-0024-d — corrective, resolution moved from `faction.role_capacities`
to the relational `faction_role` table).

No DB, plain text scan of `app.py`.
"""
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
APP = ROOT / "src" / "world_engine" / "cockpit" / "app.py"


def fail(msg):
    print(f"FAIL: {msg}")
    sys.exit(1)


def main():
    if not APP.exists():
        fail(f"{APP} not found")
    src = APP.read_text(encoding="utf-8")

    if "r.name.casefold() == role_key.casefold()" not in src:
        fail("role resolution is not case-insensitive against faction_role rows")
    if "select(FactionRole).where(FactionRole.faction_id == faction_id)" not in src:
        fail("role resolution does not read the faction_role table")
    if "faction.role_capacities or {}" in src or "capacities = faction.role_capacities" in src:
        fail("role resolution still reads faction.role_capacities directly")
    if "is not declared for" not in src:
        fail("no K1 reject message for an undeclared role without declare")
    if "elif declare:" not in src:
        fail("no L2 declare-and-occupy branch (elif declare:)")
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
