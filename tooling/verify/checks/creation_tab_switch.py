"""G1 check: the tab-switch sheet reset (TICKET-0083, BRIEF-0083-a).

Opening a record on a Creation sub-tab and then switching to another
sub-tab used to leave the editor area frozen on the opened record while
the URL and the sub-tab button both moved. The actual bug was ordering:
`showCreationSubTab` (frontend/src/creation/tabs.js) wrote
`creationState.activeTabKey` BEFORE dispatching the sheet reset, while
Sheet.svelte's record-tab render branches were SELECTED by `activeTabKey`
but FED by `sheetType`/`sheetDetail` -- two facts, two writers, no
ordering contract between them. flushSync(fn) flushes the pending batch
BEFORE running fn, so a reset that ran after the key move forced exactly
one frame where the branch selector and its data disagreed; that frame
rendered a record through the generic entity branch, whose unguarded
`registry.types[type]` lookup threw on a tab id (e.g. 'intrigues'), and
the throw aborted the whole batch -- the sheet's AND the sidebar's queued
DOM updates were both dropped. Rule 2 below locks the fix: the reset
dispatch must sit strictly before the key-move assignment, textually,
inside the dispatcher.

That ordering fix alone does not make a stale mismatch safe -- it only
makes it rarer. Rule 4 (and rule 5's registry.types[type] guard) is what
stops an inconsistent frame from being FATAL: Sheet.svelte's evenements/
intrigues branches are selected by `type` (creationState.sheetType, the
same fact that feeds them), never by `tabKey`, so a transient mismatch
renders a blank/empty frame instead of throwing.

Same idiom as creation_island.py: module-level FAILURES list, fail(),
_report_and_exit(counts), ROOT via parents[3], stdlib only, no DB, no
subprocess, exit 0 on pass / 1 on failure. Each rule is vacuous-proof: a
missing file, a zero-length collection, or a zero-count scan is a
FAILURE, never a trivially satisfied comparison.

  1. `frontend/src/creation/tabs.js` exists and contains
     `export function showCreationSubTab(tab) {`. Not found -> FAIL.
  2. Inside that function's body (sliced from the header offset to the
     first line-initial `}` after it), both `'creation:sheet-reset'` and
     `creationState.activeTabKey = tab` occur. Either missing -> FAIL.
     The reset's offset must be strictly LESS than the assignment's
     offset, or FAIL.
  3. `CustomEvent('creation:sheet-reset'` (the DISPATCH form only --
     Sheet.svelte legitimately holds an addEventListener for the same
     name) occurs exactly once across every file under frontend/src/,
     and that occurrence is in creation/tabs.js. Zero -> FAIL.
  4. `frontend/src/creation/Sheet.svelte` contains BOTH
     `{:else if type === 'evenements'}` and
     `{:else if type === 'intrigues'}`, and contains NEITHER
     `{:else if tabKey === 'evenements'}` NOR
     `{:else if tabKey === 'intrigues'}`. Any of the four conditions
     violated -> FAIL.
  5. `frontend/src/creation/Sheet.svelte` contains
     `{:else if registry.types[type]}`. Not found -> FAIL.
  6. The identifiers `_entityTabEnterReset`, `_intriguesTabEnterReset`
     and `_evenementsTabEnterReset` appear nowhere in tabs.js. Any
     present -> FAIL. Vacuity guard: at least one `onTabEnter:` key must
     still be found in tabs.js (npc and lieux keep theirs), or the scan
     proved nothing -> FAIL.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
FRONTEND_SRC = ROOT / "frontend" / "src"
CREATION_SRC = FRONTEND_SRC / "creation"
TABS_FILE = CREATION_SRC / "tabs.js"
SHEET_FILE = CREATION_SRC / "Sheet.svelte"

DISPATCHER_HEADER_RE = re.compile(r"export function showCreationSubTab\(tab\)\s*\{")
LINE_INITIAL_CLOSE_RE = re.compile(r"^\}", re.MULTILINE)
DISPATCH_RE = re.compile(r"CustomEvent\('creation:sheet-reset'")
RETIRED_IDENTS = ("_entityTabEnterReset", "_intriguesTabEnterReset", "_evenementsTabEnterReset")

FAILURES: list[str] = []


def fail(msg: str) -> None:
    FAILURES.append(msg)


def _report_and_exit(counts: dict | None = None) -> None:
    if FAILURES:
        for msg in FAILURES:
            print(f"FAIL: {msg}")
        sys.exit(1)
    print(
        f"PASS: creation_tab_switch — reset dispatched at offset {counts['reset_offset']} "
        f"before activeTabKey move at offset {counts['assign_offset']}; "
        f"{counts['onTabEnter_count']} onTabEnter key(s) surviving"
    )
    sys.exit(0)


def _dispatcher_body(tabs_src: str) -> tuple[str, int] | None:
    m = DISPATCHER_HEADER_RE.search(tabs_src)
    if not m:
        fail(f"{TABS_FILE}: 'export function showCreationSubTab(tab) {{' not found")
        return None
    brace_start = tabs_src.find("{", m.end() - 1)
    close_m = LINE_INITIAL_CLOSE_RE.search(tabs_src, brace_start)
    if not close_m:
        fail(f"{TABS_FILE}: no line-initial '}}' found after showCreationSubTab's header -- cannot bound its body")
        return None
    return tabs_src[m.start():close_m.end()], m.start()


def _rule2_ordering(tabs_src: str) -> bool:
    result = _dispatcher_body(tabs_src)
    if result is None:
        return False
    body, base_offset = result
    reset_m = re.search(r"'creation:sheet-reset'", body)
    assign_m = re.search(r"creationState\.activeTabKey\s*=\s*tab\b", body)
    if not reset_m:
        fail(f"{TABS_FILE}: showCreationSubTab's body has no 'creation:sheet-reset' dispatch")
        return False
    if not assign_m:
        fail(f"{TABS_FILE}: showCreationSubTab's body has no 'creationState.activeTabKey = tab' assignment")
        return False
    if not (reset_m.start() < assign_m.start()):
        fail(
            f"{TABS_FILE}: 'creation:sheet-reset' dispatch (offset {base_offset + reset_m.start()}) "
            f"does not precede 'creationState.activeTabKey = tab' (offset {base_offset + assign_m.start()}) "
            "-- the reset must run BEFORE the key move"
        )
        return False
    return True


def _rule2_offsets(tabs_src: str) -> tuple[int, int]:
    result = _dispatcher_body(tabs_src)
    if result is None:
        return (-1, -1)
    body, base_offset = result
    reset_m = re.search(r"'creation:sheet-reset'", body)
    assign_m = re.search(r"creationState\.activeTabKey\s*=\s*tab\b", body)
    reset_off = base_offset + reset_m.start() if reset_m else -1
    assign_off = base_offset + assign_m.start() if assign_m else -1
    return (reset_off, assign_off)


def _rule3_single_dispatch_site() -> bool:
    if not FRONTEND_SRC.is_dir():
        fail(f"{FRONTEND_SRC} is not a directory")
        return False
    files = [p for p in FRONTEND_SRC.rglob("*") if p.is_file()]
    if not files:
        fail(f"{FRONTEND_SRC} contains no files -- empty scan is a failure")
        return False
    sites: list[Path] = []
    total = 0
    for path in files:
        text = path.read_text(encoding="utf-8")
        n = len(DISPATCH_RE.findall(text))
        if n:
            total += n
            sites.append(path)
    if total == 0:
        fail("zero \"CustomEvent('creation:sheet-reset'\" dispatch sites found under frontend/src/")
        return False
    if total != 1 or sites != [TABS_FILE]:
        fail(
            f"\"CustomEvent('creation:sheet-reset'\" dispatched {total} time(s) across {[str(p) for p in sites]} "
            f"-- must be exactly 1 occurrence, in {TABS_FILE}"
        )
        return False
    return True


def _rule4_type_gated(sheet_src: str) -> bool:
    ok = True
    if "{:else if type === 'evenements'}" not in sheet_src:
        fail(f"{SHEET_FILE}: missing \"{{:else if type === 'evenements'}}\" branch")
        ok = False
    if "{:else if type === 'intrigues'}" not in sheet_src:
        fail(f"{SHEET_FILE}: missing \"{{:else if type === 'intrigues'}}\" branch")
        ok = False
    if "{:else if tabKey === 'evenements'}" in sheet_src:
        fail(f"{SHEET_FILE}: stale \"{{:else if tabKey === 'evenements'}}\" branch still present")
        ok = False
    if "{:else if tabKey === 'intrigues'}" in sheet_src:
        fail(f"{SHEET_FILE}: stale \"{{:else if tabKey === 'intrigues'}}\" branch still present")
        ok = False
    return ok


def _rule5_generic_guard(sheet_src: str) -> bool:
    if "{:else if registry.types[type]}" not in sheet_src:
        fail(f"{SHEET_FILE}: missing \"{{:else if registry.types[type]}}\" guard on the generic entity branch")
        return False
    return True


def main() -> None:
    if not TABS_FILE.is_file():
        fail(f"{TABS_FILE} does not exist")
        _report_and_exit()
        return
    if not SHEET_FILE.is_file():
        fail(f"{SHEET_FILE} does not exist")
        _report_and_exit()
        return

    tabs_src = TABS_FILE.read_text(encoding="utf-8")
    sheet_src = SHEET_FILE.read_text(encoding="utf-8")
    if not tabs_src.strip() or not sheet_src.strip():
        fail(f"{TABS_FILE} or {SHEET_FILE} is empty")
        _report_and_exit()
        return

    ordering_ok = _rule2_ordering(tabs_src)
    dispatch_ok = _rule3_single_dispatch_site()
    gated_ok = _rule4_type_gated(sheet_src)
    guard_ok = _rule5_generic_guard(sheet_src)

    helpers_ok = True
    for ident in RETIRED_IDENTS:
        if re.search(rf"\b{re.escape(ident)}\b", tabs_src):
            fail(f"{TABS_FILE}: retired identifier {ident!r} still present")
            helpers_ok = False
    onTabEnter_count = len(re.findall(r"\bonTabEnter\s*:", tabs_src))
    if onTabEnter_count == 0:
        fail(f"{TABS_FILE}: zero 'onTabEnter:' keys found -- the scan proved nothing")
        helpers_ok = False

    if FAILURES or not (ordering_ok and dispatch_ok and gated_ok and guard_ok and helpers_ok):
        _report_and_exit()
        return

    reset_off, assign_off = _rule2_offsets(tabs_src)
    _report_and_exit(
        {
            "reset_offset": reset_off,
            "assign_offset": assign_off,
            "onTabEnter_count": onTabEnter_count,
        }
    )


if __name__ == "__main__":
    main()
