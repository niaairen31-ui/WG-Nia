"""G1 check for TICKET-0022/BRIEF-0022-a — Événements creator tab.

Asserts:
1. No `event` delete surface exists anywhere: no `DELETE /api/events` (or
   `/api/events/{id}`) route in the cockpit app, and no client-side function
   or route call in index.html deletes an event (C3 — `event` is history;
   retraction is `knowledge_status = 'secret'`, never a delete).
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
INDEX_HTML = COCKPIT_DIR / "index.html"

DELETE_ROUTE_RE = re.compile(r"""@(?:router|app)\.delete\(\s*["']/api/events""")
JS_DELETE_RE = re.compile(r"""method:\s*['"]DELETE['"]\s*,?\s*\}\)?[^`]{0,80}""")
ORDER_BY_OCCURRED_AT_RE = re.compile(r"order_by\(\s*Event\.occurred_at")


def main() -> int:
    failures: list[str] = []

    for path in sorted(COCKPIT_DIR.rglob("*.py")):
        if DELETE_ROUTE_RE.search(path.read_text(encoding="utf-8")):
            failures.append(
                f"{path.relative_to(ROOT).as_posix()}: a DELETE /api/events route is "
                "registered — event deletion is Scope OUT (C3)"
            )

    html_src = INDEX_HTML.read_text(encoding="utf-8")
    for m in re.finditer(r"api\(`?/api/events[^)]*\)", html_src):
        window = html_src[m.start():m.start() + 200]
        if "DELETE" in window:
            failures.append(f"index.html calls DELETE against /api/events near {window[:60]!r}")

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
