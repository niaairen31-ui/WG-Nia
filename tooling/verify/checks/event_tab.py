"""G1 check for TICKET-0022/BRIEF-0022-a — Événements creator tab.

Re-homed by TICKET-0058/BRIEF-0058-j: evenements' /api/events calls moved
off index.html onto frontend/src/creation/Sheet.svelte (saveEventSheet) and
Evenements.svelte (the AI draft-generate call) -- this check follows them
there, same "assertion preserved, only the scanned file moves" idiom
page_contract.py/faction_roster_panel.py already established.

Asserts:
1. No `event` delete surface exists anywhere: no `DELETE /api/events` (or
   `/api/events/{id}`) route in the cockpit app, and no client-side call to
   an `/api/events` path anywhere under frontend/src/creation uses DELETE
   (C3 — `event` is history; retraction is `knowledge_status = 'secret'`,
   never a delete). Vacuous-proof: at least one non-DELETE `/api/events`
   call must be found under frontend/src/creation, or the check fails --
   an empty scan proves nothing.
2. `Event.occurred_at` appears in no `order_by(...)` anywhere in `src/`
   (RECON finding 7 — the column is never written, so ordering by it was
   arbitrary; `context.py` now orders by `recorded_at`).

No DB, plain text/regex only. Exit 0 on pass, 1 on failure.
"""
from __future__ import annotations

import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
SRC = ROOT / "src"
COCKPIT_DIR = SRC / "world_engine" / "cockpit"
FRONTEND_CREATION_DIR = ROOT / "frontend" / "src" / "creation"

DELETE_ROUTE_RE = re.compile(r"""@(?:router|app)\.delete\(\s*["']/api/events""")
API_EVENTS_CALL_RE = re.compile(r"api\(\s*`?/api/events[^)]*\)")
ORDER_BY_OCCURRED_AT_RE = re.compile(r"order_by\(\s*Event\.occurred_at")


def main() -> int:
    failures: list[str] = []

    for path in sorted(COCKPIT_DIR.rglob("*.py")):
        if DELETE_ROUTE_RE.search(path.read_text(encoding="utf-8")):
            failures.append(
                f"{path.relative_to(ROOT).as_posix()}: a DELETE /api/events route is "
                "registered — event deletion is Scope OUT (C3)"
            )

    if not FRONTEND_CREATION_DIR.is_dir():
        failures.append(f"{FRONTEND_CREATION_DIR} is not a directory")
    else:
        calls_found = 0
        for path in sorted(FRONTEND_CREATION_DIR.rglob("*")):
            if not path.is_file():
                continue
            text = path.read_text(encoding="utf-8")
            for m in API_EVENTS_CALL_RE.finditer(text):
                calls_found += 1
                window = text[m.start():m.start() + 200]
                if "DELETE" in window:
                    failures.append(
                        f"{path.relative_to(ROOT).as_posix()} calls DELETE against "
                        f"/api/events near {window[:60]!r}"
                    )
        if calls_found == 0:
            failures.append(
                f"zero /api/events call(s) found under {FRONTEND_CREATION_DIR} — "
                "a rule that passes on nothing is the flaw this fixes"
            )

    for path in sorted(SRC.rglob("*.py")):
        text = path.read_text(encoding="utf-8")
        if ORDER_BY_OCCURRED_AT_RE.search(text):
            failures.append(
                f"{path.relative_to(ROOT).as_posix()}: order_by(Event.occurred_at...) found — "
                "Event.occurred_at must govern no ordering (RECON finding 7, order by recorded_at instead)"
            )

    if failures:
        for f in failures:
            print(f"FAIL: {f}")
        return 1

    print(
        "PASS: event_tab — no event-delete surface exists, "
        "Event.occurred_at governs no order_by"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
