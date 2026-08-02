"""G1 check for TICKET-0054 (BRIEF-0054-d): Creation surface cross-tab entity
navigation with a single-slot return crumb. Text scan of
`src/world_engine/cockpit/index.html`, no DB — stdlib only, same idiom as
`import_cycle.py` (`FAILURES`, `_report_and_exit`, `ROOT` via `parents[3]`).

Collects by function name via a brace-balanced slice (`page_contract.py`'s
`_braced_block` idiom), never by comment-anchored section slice — a
comment-anchored slice goes stale as the file is edited (TICKET-0043 lesson).

Retargeted (TICKET-0058, BRIEF-0058-g family b): authorRenderFactionRoster/
_factionRosterRowHtml moved off index.html onto
frontend/src/creation/FactionRoster.svelte — same class of anchor move
faction_roster_panel.py's own retargeting already covers; the ondblclick
assertion now scans that file's source text directly instead of a
brace-balanced function body (a .svelte file isn't JS function syntax).

Vacuous-proof guard, mandatory: a missing file, or zero assertions actually
evaluated because a named function could not be located, is a FAILURE — this
check must never report PASS having silently skipped its own assertions.
"""
from __future__ import annotations

import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
INDEX_HTML = ROOT / "src" / "world_engine" / "cockpit" / "index.html"
FACTION_ROSTER_SVELTE = ROOT / "frontend" / "src" / "creation" / "FactionRoster.svelte"

FAILURES: list[str] = []
_ASSERTIONS_EVALUATED = 0


def fail(msg: str) -> None:
    FAILURES.append(msg)


def _report_and_exit() -> None:
    if not FAILURES and _ASSERTIONS_EVALUATED == 0:
        fail("zero assertions evaluated — a named function could not be located; vacuous pass refused")
    if FAILURES:
        for msg in FAILURES:
            print(f"FAIL: {msg}")
        sys.exit(1)
    print("PASS: creation_return_nav — single-slot return crumb wired correctly")
    sys.exit(0)


def _braced_block(html: str, start_pattern: str) -> str:
    """Return the full `{ ... }` block whose opening brace follows the first
    match of start_pattern, matching braces to find the end. Empty string if
    the pattern or a balanced close isn't found."""
    m = re.search(start_pattern, html)
    if not m:
        return ""
    brace_start = html.find("{", m.end() - 1)
    if brace_start == -1:
        return ""
    depth = 0
    for i in range(brace_start, len(html)):
        if html[i] == "{":
            depth += 1
        elif html[i] == "}":
            depth -= 1
            if depth == 0:
                return html[brace_start : i + 1]
    return ""


def _function_body(html: str, name: str) -> str:
    """Full `{ ... }` body of a top-level `function <name>(...)` or
    `async function <name>(...)` declaration, brace-balanced."""
    return _braced_block(html, rf"(?:async\s+)?function\s+{re.escape(name)}\s*\([^)]*\)\s*")


def main() -> None:
    global _ASSERTIONS_EVALUATED

    if not INDEX_HTML.exists():
        fail(f"{INDEX_HTML} does not exist — scan is broken, not the repo clean")
        _report_and_exit()
        return

    html = INDEX_HTML.read_text(encoding="utf-8")

    # creationReturnTo is declared exactly once at module level.
    _ASSERTIONS_EVALUATED += 1
    declare_count = len(re.findall(r"\blet\s+creationReturnTo\s*=", html))
    if declare_count != 1:
        fail(f"creationReturnTo is declared {declare_count} time(s) at module level — expected exactly 1")

    # showCreationSubTab assigns creationReturnTo = null.
    subtab_body = _function_body(html, "showCreationSubTab")
    if not subtab_body:
        fail("showCreationSubTab(...) function body not found in index.html")
    else:
        _ASSERTIONS_EVALUATED += 1
        if not re.search(r"creationReturnTo\s*=\s*null", subtab_body):
            fail("showCreationSubTab does not assign creationReturnTo = null")

    # Inside creationOpenEntityFrom: the assignment creationReturnTo = origin
    # appears AFTER the showCreationSubTab( call — ordering IS the mechanism.
    open_body = _function_body(html, "creationOpenEntityFrom")
    if not open_body:
        fail("creationOpenEntityFrom(...) function body not found in index.html")
    else:
        _ASSERTIONS_EVALUATED += 1
        call_idx = open_body.find("showCreationSubTab(")
        assign_idx = open_body.find("creationReturnTo = origin")
        if call_idx == -1 or assign_idx == -1:
            fail(
                "creationOpenEntityFrom does not contain both a showCreationSubTab( "
                "call and a 'creationReturnTo = origin' assignment"
            )
        elif not call_idx < assign_idx:
            fail(
                "creationOpenEntityFrom assigns creationReturnTo = origin BEFORE "
                "calling showCreationSubTab( — the ordering is the mechanism that "
                "keeps a manual tab click and a programmatic navigation distinct; "
                "reversing it silently breaks the whole feature"
            )

        # creationOpenEntityFrom contains the currentCreationSubTab !== guard.
        _ASSERTIONS_EVALUATED += 1
        if "currentCreationSubTab !== " not in open_body:
            fail("creationOpenEntityFrom does not contain a 'currentCreationSubTab !== ' guard")

    # creationResolveEntityTab references playerCharIds.
    resolve_body = _function_body(html, "creationResolveEntityTab")
    if not resolve_body:
        fail("creationResolveEntityTab(...) function body not found in index.html")
    else:
        _ASSERTIONS_EVALUATED += 1
        if "playerCharIds" not in resolve_body:
            fail("creationResolveEntityTab does not reference playerCharIds")

    # _creationRunWorldSwitchResets assigns creationReturnTo = null.
    worldswitch_body = _function_body(html, "_creationRunWorldSwitchResets")
    if not worldswitch_body:
        fail("_creationRunWorldSwitchResets(...) function body not found in index.html")
    else:
        _ASSERTIONS_EVALUATED += 1
        if not re.search(r"creationReturnTo\s*=\s*null", worldswitch_body):
            fail("_creationRunWorldSwitchResets does not assign creationReturnTo = null")

    # creationReturnTo is never .push(ed onto — it is a slot, not a stack.
    _ASSERTIONS_EVALUATED += 1
    if re.search(r"creationReturnTo\.push\(", html):
        fail("creationReturnTo is .push(ed onto somewhere — it must stay a single slot, never a stack")

    # FactionRoster.svelte (was authorRenderFactionRoster/_factionRosterRowHtml)
    # contains ondblclick.
    if not FACTION_ROSTER_SVELTE.exists():
        fail(f"{FACTION_ROSTER_SVELTE} does not exist — scan is broken, not the repo clean")
    else:
        _ASSERTIONS_EVALUATED += 1
        roster_svelte_src = FACTION_ROSTER_SVELTE.read_text(encoding="utf-8")
        if "ondblclick" not in roster_svelte_src:
            fail(f"{FACTION_ROSTER_SVELTE} does not contain 'ondblclick'")

    _report_and_exit()


if __name__ == "__main__":
    main()
