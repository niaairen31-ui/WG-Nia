"""G1 check for TICKET-0115 -- the « Suivi » tab shows the dashboard's metrics and deferrals, exports the same scope, and warns that the export holds secrets.

BRIEF-0115-E's rules (H1, F2, I1 and J1 of the conditions series'
dashboard). Static: the tab's registration is held by `page_contract.py`,
`creation_island.py` and `creation_container_sizing.py`; this check holds
what the tab says.

DT1 -- registered. `tabs.js` declares a `suivi` entry labelled « Suivi »
   whose one island is `dashboard` in `creation-suivi`, with no primary
   action; `registry.js` declares `dashboard` origin `new`, created by
   TICKET-0115.
DT2 -- requests. `dashboard.svelte.js` reads `/api/dashboard?` and
   `/api/dashboard/export?` with the same query (`world`, `since`, `until`)
   and writes nothing (no `method:` POST, PUT or DELETE).
DT3 -- what it shows. `Dashboard.svelte` renders each metric's `question`,
   `watches` and `rows` (through `share`), each deferral's `condition` and
   `status`, a world selector with « Tous les mondes », two date inputs,
   the export button, and the warning that the export holds the secrets
   and notes.

Stdlib only, no DB. A missing file or a missing passage is a FAILURE.
"""
from __future__ import annotations

import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
CREATION = ROOT / "frontend" / "src" / "creation"

FAILURES: list[str] = []

PASSAGES: dict[str, tuple[str, ...]] = {
    "DT1 tabs.js": ("suivi: {", "label: 'Suivi'", "islands: [{ key: 'dashboard', containerId: 'creation-suivi' }]"),
    "DT1 registry.js": ("dashboard: Object.freeze({", "containerId: 'creation-suivi'", "createdBy: 'TICKET-0115'"),
    "DT2 dashboard.svelte.js": ("'/api/dashboard?' + query()", "'/api/dashboard/export?' + query()",
                                "new URLSearchParams({ world: dashboardState.world })",
                                "params.set('since'", "params.set('until'"),
    "DT3 Dashboard.svelte": ("{metric.question}", "metric.watches", "metric.rows", "share(row)", "{d.condition}",
                             "d.status", '<option value="all">Tous les mondes</option>', 'type="date"',
                             "onclick={exportDashboard}", "secrets et notes compris"),
}
FILES = {"DT1 tabs.js": "tabs.js", "DT1 registry.js": "registry.js",
         "DT2 dashboard.svelte.js": "dashboard.svelte.js", "DT3 Dashboard.svelte": "Dashboard.svelte"}


def fail(msg: str) -> None:
    FAILURES.append(msg)


def main() -> None:
    texts = {}
    for rule, name in FILES.items():
        path = CREATION / name
        if not path.exists():
            fail(f"{rule}: {path} not found")
            continue
        texts[rule] = path.read_text(encoding="utf-8")
        for passage in PASSAGES[rule]:
            if passage not in texts[rule]:
                fail(f"{rule}: missing {passage!r}")
    tabs = texts.get("DT1 tabs.js", "")
    block = re.search(r"\n  suivi: \{(.*?)\n  \},", tabs, re.DOTALL)
    if block is None or "primaryAction: null" not in block.group(1):
        fail("DT1: the suivi entry has a primary action")
    registry = texts.get("DT1 registry.js", "")
    entry = re.search(r"dashboard: Object\.freeze\(\{(.*?)\}\)", registry, re.DOTALL)
    if entry is None or "origin: 'new'" not in entry.group(1):
        fail("DT1: the dashboard island is not origin 'new'")
    if re.search(r"method:\s*'(POST|PUT|PATCH|DELETE)'", texts.get("DT2 dashboard.svelte.js", "")):
        fail("DT2: dashboard.svelte.js writes")
    if FAILURES:
        for msg in FAILURES:
            print(f"FAIL: {msg}")
        sys.exit(1)
    print("PASS: dashboard_tab -- « Suivi » shows the metrics and the deferrals, exports the same scope, "
          "and warns about secrets")


if __name__ == "__main__":
    main()
