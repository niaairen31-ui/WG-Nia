"""G1 check: role capacity is read through one shared accessor, called by
BOTH the AI `role_change` effect and the two creator paths (TICKET-0054,
BRIEF-0054-b, decision E1).

Plain text scan, no DB — same idiom as `import_cycle.py` (`FAILURES` list,
`_report_and_exit`, `ROOT` via `parents[3]`). Also guards the close+reopen
shape of the reassignment route: no in-place `membership.role =` write may
ever appear, since `faction_membership` is INSERT-only / close-only by
construction (BRIEF-27).
"""
from __future__ import annotations

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
WRITES_FACTIONS = ROOT / "src" / "world_engine" / "writes" / "factions.py"
WRITES_INIT = ROOT / "src" / "world_engine" / "writes" / "__init__.py"
MUTATIONS = ROOT / "src" / "world_engine" / "cockpit" / "mutations.py"
CRUD_FACTIONS = ROOT / "src" / "world_engine" / "cockpit" / "crud" / "factions.py"

FAILURES: list[str] = []


def fail(msg: str) -> None:
    FAILURES.append(msg)


def _report_and_exit() -> None:
    if FAILURES:
        for msg in FAILURES:
            print(f"FAIL: {msg}")
        sys.exit(1)
    print("PASS: role_capacity_chokepoint — one shared capacity accessor, called by both AI and creator paths")
    sys.exit(0)


def main() -> None:
    targets = {
        "writes/factions.py": WRITES_FACTIONS,
        "writes/__init__.py": WRITES_INIT,
        "cockpit/mutations.py": MUTATIONS,
        "cockpit/crud/factions.py": CRUD_FACTIONS,
    }
    missing = [name for name, path in targets.items() if not path.exists()]
    if missing:
        for name in missing:
            fail(f"{name} not found")
        _report_and_exit()
        return

    writes_factions_text = WRITES_FACTIONS.read_text(encoding="utf-8")
    writes_init_text = WRITES_INIT.read_text(encoding="utf-8")
    mutations_text = MUTATIONS.read_text(encoding="utf-8")
    crud_factions_text = CRUD_FACTIONS.read_text(encoding="utf-8")

    evaluated = 0

    evaluated += 1
    if "def role_capacity_state(" not in writes_factions_text:
        fail("writes/factions.py does not define role_capacity_state(")
    evaluated += 1
    if "def active_role_counts(" not in writes_factions_text:
        fail("writes/factions.py does not define active_role_counts(")

    evaluated += 1
    if "active_role_counts" not in writes_init_text:
        fail("writes/__init__.py does not export active_role_counts")
    evaluated += 1
    if "role_capacity_state" not in writes_init_text:
        fail("writes/__init__.py does not export role_capacity_state")

    evaluated += 1
    if "role_capacity_state(" not in mutations_text:
        fail("cockpit/mutations.py does not call role_capacity_state(")

    evaluated += 1
    if crud_factions_text.count("role_capacity_state(") < 2:
        fail("cockpit/crud/factions.py calls role_capacity_state( fewer than twice (open path + reassign path)")

    evaluated += 1
    if "_active_role_counts" in crud_factions_text:
        fail("cockpit/crud/factions.py still defines/uses _active_role_counts — should be the shared active_role_counts")

    evaluated += 1
    if 'mode="close"' not in crud_factions_text or 'mode="open"' not in crud_factions_text:
        fail("cockpit/crud/factions.py reassign core does not show the close+reopen shape (mode=\"close\"/mode=\"open\")")

    evaluated += 1
    if "membership.role =" in crud_factions_text:
        fail("cockpit/crud/factions.py contains an in-place membership.role = assignment — breaks append-only history")

    if evaluated == 0:
        fail("zero assertions evaluated — vacuous check")

    _report_and_exit()


if __name__ == "__main__":
    main()
