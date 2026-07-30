"""G1 check: the faction roster route sorts by declared role rank
(TICKET-0054, BRIEF-0054-a, decisions A1/B1).

Plain text scan of `src/world_engine/cockpit/crud/factions.py`, no DB —
same idiom as `import_cycle.py` (`FAILURES` list, `_report_and_exit`, `ROOT`
via `parents[3]`). Asserts the ordering helpers exist, that the route
actually calls the sort key (a roster returned unsorted is the exact
regression this check exists for), that the enrichment stays roster-only,
and that role matching is casefold-based, never ASCII-only SQL `lower()`.
"""
from __future__ import annotations

import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
TARGET = ROOT / "src" / "world_engine" / "cockpit" / "crud" / "factions.py"

FAILURES: list[str] = []


def fail(msg: str) -> None:
    FAILURES.append(msg)


def _report_and_exit() -> None:
    if FAILURES:
        for msg in FAILURES:
            print(f"FAIL: {msg}")
        sys.exit(1)
    print("PASS: faction_roster_order — roster route sorts by declared role rank")
    sys.exit(0)


def main() -> None:
    if not TARGET.exists():
        fail(f"{TARGET} not found")
        _report_and_exit()
        return

    text = TARGET.read_text(encoding="utf-8")

    if "def _roster_rank_index(" not in text:
        fail("_roster_rank_index is not defined")
    if "def _roster_sort_key(" not in text:
        fail("_roster_sort_key is not defined")

    roster_match = re.search(
        r"def get_faction_roster\(.*?\n(?:.*\n)*?(?=\ndef |\Z)", text
    )
    if roster_match is None:
        fail("get_faction_roster could not be located in the source text")
        _report_and_exit()
        return

    roster_body = roster_match.group(0)
    if "_roster_sort_key" not in roster_body:
        fail("get_faction_roster does not call _roster_sort_key — roster is not sorted")

    rank_index_match = re.search(
        r"def _roster_rank_index\(.*?\n(?:.*\n)*?(?=\ndef |\Z)", text
    )
    if rank_index_match is None:
        fail("_roster_rank_index could not be located in the source text")
    else:
        rank_index_body = rank_index_match.group(0)
        if "FactionRole.position" not in rank_index_body:
            fail("_roster_rank_index does not read FactionRole.position")
        if ".casefold()" not in rank_index_body:
            fail("_roster_rank_index does not use .casefold() for role matching")

    roster_dict_match = re.search(
        r"def _roster_dict\(.*?\n(?:.*\n)*?(?=\ndef |\Z)", text
    )
    if roster_dict_match is None:
        fail("_roster_dict could not be located in the source text")
    else:
        roster_dict_body = roster_dict_match.group(0)
        if "role_position" not in roster_dict_body:
            fail("_roster_dict does not carry role_position")
        if "role_declared" not in roster_dict_body:
            fail("_roster_dict does not carry role_declared")

    membership_dict_match = re.search(
        r"def _membership_dict\(.*?\n(?:.*\n)*?(?=\ndef |\Z)", text
    )
    if membership_dict_match is None:
        fail("_membership_dict could not be located in the source text")
    else:
        membership_dict_body = membership_dict_match.group(0)
        if "role_position" in membership_dict_body:
            fail("_membership_dict leaks role_position — roster enrichment must stay roster-only")

    if not FAILURES and roster_match is None:
        fail("zero assertions evaluated — vacuous check")

    _report_and_exit()


if __name__ == "__main__":
    main()
