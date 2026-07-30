"""G1 check for TICKET-0054 (BRIEF-0054-c): faction sheet grouped roster
panel + member authoring. Text scan of `src/world_engine/cockpit/index.html`,
no DB — stdlib only, same idiom as `import_cycle.py` (`FAILURES`,
`_report_and_exit`, `ROOT` via `parents[3]`).

Collects by function name via a brace-balanced slice (`page_contract.py`'s
`_braced_block` idiom), never by comment-anchored section slice — a
comment-anchored slice goes stale as the file is edited (TICKET-0043 lesson).

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

    # authorLoadFactionMembersPanel is defined, and the faction branch of the
    # sheet renderer (authorRenderSheet) calls it.
    panel_loader_body = _function_body(html, "authorLoadFactionMembersPanel")
    if not panel_loader_body:
        fail("authorLoadFactionMembersPanel(...) function body not found in index.html")
    else:
        _ASSERTIONS_EVALUATED += 1
        sheet_body = _function_body(html, "authorRenderSheet")
        if not sheet_body:
            fail("authorRenderSheet(...) function body not found in index.html")
        else:
            _ASSERTIONS_EVALUATED += 1
            if not re.search(
                r"if\s*\(\s*!isNew\s*&&\s*type\s*===\s*'faction'\s*\)\s*\{"
                r"[^}]*authorLoadFactionMembersPanel\(",
                sheet_body,
            ):
                fail(
                    "authorRenderSheet's \"!isNew && type === 'faction'\" branch does not "
                    "call authorLoadFactionMembersPanel(...)"
                )

        # authorLoadFactionMembersPanel awaits authorLoadFactionRoles BEFORE
        # authorLoadFactionRoster — ordering IS the mechanism (sequencing wrapper).
        _ASSERTIONS_EVALUATED += 1
        roles_idx = panel_loader_body.find("authorLoadFactionRoles(")
        roster_idx = panel_loader_body.find("authorLoadFactionRoster(")
        if roles_idx == -1 or roster_idx == -1:
            fail(
                "authorLoadFactionMembersPanel does not call both "
                "authorLoadFactionRoles(...) and authorLoadFactionRoster(...)"
            )
        elif not roles_idx < roster_idx:
            fail(
                "authorLoadFactionMembersPanel calls authorLoadFactionRoster before "
                "authorLoadFactionRoles — the grouped render needs declared roles in "
                "memory first"
            )

    # authorRenderFactionRoster references role_declared, role_position, and
    # authorFactionRolesLive; contains no .sort( call (server owns order).
    roster_render_body = _function_body(html, "authorRenderFactionRoster")
    if not roster_render_body:
        fail("authorRenderFactionRoster(...) function body not found in index.html")
    else:
        for token in ("role_declared", "role_position", "authorFactionRolesLive"):
            _ASSERTIONS_EVALUATED += 1
            if token not in roster_render_body:
                fail(f"authorRenderFactionRoster does not reference {token!r}")
        _ASSERTIONS_EVALUATED += 1
        if ".sort(" in roster_render_body:
            fail(
                "authorRenderFactionRoster contains a .sort( call — the server owns "
                "member order (decision A1); the client must only group"
            )

    # authorAddFactionMember posts to /memberships and sends faction_id.
    add_member_body = _function_body(html, "authorAddFactionMember")
    if not add_member_body:
        fail("authorAddFactionMember(...) function body not found in index.html")
    else:
        _ASSERTIONS_EVALUATED += 1
        if "/memberships" not in add_member_body:
            fail("authorAddFactionMember does not post to a '/memberships' path")
        _ASSERTIONS_EVALUATED += 1
        if "faction_id" not in add_member_body:
            fail("authorAddFactionMember does not send faction_id in its request body")

    # authorMemberRoleEditSubmit posts to a /role path.
    role_edit_submit_body = _function_body(html, "authorMemberRoleEditSubmit")
    if not role_edit_submit_body:
        fail("authorMemberRoleEditSubmit(...) function body not found in index.html")
    else:
        _ASSERTIONS_EVALUATED += 1
        if "/role" not in role_edit_submit_body:
            fail("authorMemberRoleEditSubmit does not post to a '/role' path")

    # The literal 'Membres (lecture seule)' no longer appears anywhere.
    _ASSERTIONS_EVALUATED += 1
    if "Membres (lecture seule)" in html:
        fail("literal 'Membres (lecture seule)' still present — the section is no longer read-only")

    _report_and_exit()


if __name__ == "__main__":
    main()
