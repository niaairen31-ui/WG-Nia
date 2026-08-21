"""G1 check for TICKET-0054 (BRIEF-0054-c): faction sheet grouped roster
panel + member authoring. Text scan, no DB -- stdlib only, same idiom as
`import_cycle.py` (`FAILURES`, `_report_and_exit`, `ROOT` via `parents[3]`).

Collects by function name via a brace-balanced slice (`page_contract.py`'s
`_braced_block` idiom), never by comment-anchored section slice -- a
comment-anchored slice goes stale as the file is edited (TICKET-0043 lesson).

Retargeted (TICKET-0058, BRIEF-0058-g family b): the roster panel and its
loaders moved off index.html onto frontend/src/creation/factionPanel.svelte.js
(state + API calls) and FactionRoster.svelte (the grouped render + add-member
form) -- same class of anchor move `page_contract.py`'s precedent already
covers for a relocated function: assertions preserved verbatim, only the
file each one scans moves to where the real implementation now lives.

Vacuous-proof guard, mandatory: a missing file, or zero assertions actually
evaluated because a named function could not be located, is a FAILURE -- this
check must never report PASS having silently skipped its own assertions.
"""
from __future__ import annotations

import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
INDEX_HTML = ROOT / "src" / "world_engine" / "cockpit" / "legacy.html"
SHEET_SVELTE = ROOT / "frontend" / "src" / "creation" / "Sheet.svelte"
FACTION_PANEL_JS = ROOT / "frontend" / "src" / "creation" / "factionPanel.svelte.js"
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
    print("PASS: faction_roster_panel — grouped roster panel + member authoring wired correctly")
    sys.exit(0)


def _braced_block(text: str, start_pattern: str) -> str:
    """Return the full `{ ... }` block whose opening brace follows the first
    match of start_pattern, matching braces to find the end. Empty string if
    the pattern or a balanced close isn't found."""
    m = re.search(start_pattern, text)
    if not m:
        return ""
    brace_start = text.find("{", m.end() - 1)
    if brace_start == -1:
        return ""
    depth = 0
    for i in range(brace_start, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return text[brace_start : i + 1]
    return ""


def _function_body(text: str, name: str) -> str:
    """Full `{ ... }` body of a top-level `function <name>(...)`,
    `async function <name>(...)`, or `export (async )function <name>(...)`
    declaration, brace-balanced."""
    return _braced_block(text, rf"(?:export\s+)?(?:async\s+)?function\s+{re.escape(name)}\s*\([^)]*\)\s*")


def main() -> None:
    global _ASSERTIONS_EVALUATED

    missing = [p for p in (SHEET_SVELTE, FACTION_PANEL_JS, FACTION_ROSTER_SVELTE, INDEX_HTML) if not p.exists()]
    if missing:
        for p in missing:
            fail(f"{p} does not exist — scan is broken, not the repo clean")
        _report_and_exit()
        return

    sheet_svelte_src = SHEET_SVELTE.read_text(encoding="utf-8")
    faction_panel_src = FACTION_PANEL_JS.read_text(encoding="utf-8")
    faction_roster_src = FACTION_ROSTER_SVELTE.read_text(encoding="utf-8")
    html = INDEX_HTML.read_text(encoding="utf-8")

    # loadFactionMembersPanel (was authorLoadFactionMembersPanel) is defined
    # in factionPanel.svelte.js, and Sheet.svelte's faction branch calls it
    # directly (no legacyCall any more -- BRIEF-0058-g family b moved the
    # caller off the cross-realm bridge, same as BRIEF-0058-f did for the
    # panel's own predecessor).
    panel_loader_body = _function_body(faction_panel_src, "loadFactionMembersPanel")
    if not panel_loader_body:
        fail(f"loadFactionMembersPanel(...) function body not found in {FACTION_PANEL_JS}")
    else:
        _ASSERTIONS_EVALUATED += 1
        if not re.search(
            r"if\s*\(\s*type\s*===\s*'faction'\s*\)\s*\{[^}]*loadFactionMembersPanel\(",
            sheet_svelte_src,
        ):
            fail(
                f"{SHEET_SVELTE}: no \"type === 'faction'\" block calls "
                "loadFactionMembersPanel(...)"
            )

        # loadFactionMembersPanel awaits loadFactionRoles BEFORE
        # loadFactionRoster — ordering IS the mechanism (sequencing wrapper).
        _ASSERTIONS_EVALUATED += 1
        roles_idx = panel_loader_body.find("loadFactionRoles(")
        roster_idx = panel_loader_body.find("loadFactionRoster(")
        if roles_idx == -1 or roster_idx == -1:
            fail(
                f"{FACTION_PANEL_JS}: loadFactionMembersPanel does not call both "
                "loadFactionRoles(...) and loadFactionRoster(...)"
            )
        elif not roles_idx < roster_idx:
            fail(
                f"{FACTION_PANEL_JS}: loadFactionMembersPanel calls loadFactionRoster before "
                "loadFactionRoles — the grouped render needs declared roles in "
                "memory first"
            )

    # FactionRoster.svelte's grouped render references role_declared,
    # role_position, and the shared rolesLive store field (was
    # authorFactionRolesLive); contains no .sort( call (server owns order).
    for token in ("role_declared", "role_position", "factionPanelState.rolesLive"):
        _ASSERTIONS_EVALUATED += 1
        if token not in faction_roster_src:
            fail(f"{FACTION_ROSTER_SVELTE} does not reference {token!r}")
    _ASSERTIONS_EVALUATED += 1
    if ".sort(" in faction_roster_src:
        fail(
            f"{FACTION_ROSTER_SVELTE} contains a .sort( call — the server owns "
            "member order (decision A1); the client must only group"
        )

    # addFactionMember (was authorAddFactionMember) posts to /memberships
    # and sends faction_id.
    add_member_body = _function_body(faction_panel_src, "addFactionMember")
    if not add_member_body:
        fail(f"addFactionMember(...) function body not found in {FACTION_PANEL_JS}")
    else:
        _ASSERTIONS_EVALUATED += 1
        if "/memberships" not in add_member_body:
            fail(f"{FACTION_PANEL_JS}: addFactionMember does not post to a '/memberships' path")
        _ASSERTIONS_EVALUATED += 1
        if "faction_id" not in add_member_body:
            fail(f"{FACTION_PANEL_JS}: addFactionMember does not send faction_id in its request body")

    # memberRoleEditSubmit (was authorMemberRoleEditSubmit) posts to a
    # /role path.
    role_edit_submit_body = _function_body(faction_panel_src, "memberRoleEditSubmit")
    if not role_edit_submit_body:
        fail(f"memberRoleEditSubmit(...) function body not found in {FACTION_PANEL_JS}")
    else:
        _ASSERTIONS_EVALUATED += 1
        if "/role" not in role_edit_submit_body:
            fail(f"{FACTION_PANEL_JS}: memberRoleEditSubmit does not post to a '/role' path")

    # The literal 'Membres (lecture seule)' no longer appears anywhere.
    _ASSERTIONS_EVALUATED += 1
    if "Membres (lecture seule)" in html:
        fail("literal 'Membres (lecture seule)' still present — the section is no longer read-only")

    _report_and_exit()


if __name__ == "__main__":
    main()
